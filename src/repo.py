import base64
from dataclasses import dataclass
from datetime import datetime

from src.api import GithubApi
from src.generator import OpenaiModel


@dataclass
class FilePatch:
    filename: str
    patch: str


@dataclass
class Comment:
    id_: str
    author: str
    body: str
    timestamp: datetime

    def summary(self):
        return f"COMMENT by {self.author}: {self.body}"


@dataclass
class Review:
    id_: str
    author: str
    body: str
    comments: list[Comment]

    @property
    def timestamp(self):
        return self.comments[0].timestamp

    def summary(self):
        text = f"REVIEW by {self.author}: {self.body}"
        for comment in self.comments:
            text += f"\n-  REVIEW {comment.summary()}"
        return text


@dataclass
class Commit:
    id_: str
    author: str
    message: str
    timestamp: datetime
    diff: list[FilePatch]
    generated_message: str = ""

    def summary(self):
        text = f"COMMIT by {self.author}\n -HASH: {self.id_}\n -COMMIT MESSAGE: {self.generated_message}"
        for file_patch in self.diff:
            text += f"\n----CHANGED FILE: {file_patch.filename}\n  PATCH: {file_patch.patch}"
        return text

    def generate_message(self, repo):
        TASK = """\
You are a commit message generator.
You are give a list of changed files with their patches.
You need to generate a commit message for them.\
"""
        prompt = "\n".join(
            f"""\
    FILE: {file_.filename}
    PATCH: {file_.patch}
    COMMIT MESSAGE: """
            for file_ in self.diff
        )
        # maybe should add CONTENT: {repo.get_file_content(self.id_, file_.filename)}

        gpt_model = OpenaiModel("gpt-4")

        return gpt_model.ask(TASK, prompt)


@dataclass
class PullRequest:
    id_: str
    title: str
    comments: list[Comment]
    commits: list[Commit]
    reviews: list[Review]

    def get_all(self) -> list[Comment | Commit]:
        return sorted(self.comments + self.commits + self.reviews, key=lambda x: x.timestamp)

    @property
    def comments_count(self) -> int:
        return len(self.comments) + sum(len(review.comments) for review in self.reviews)

    def discussion_before_commit(self, commit: Commit):
        all_items = self.get_all()

        items_before_commit = []
        for item in all_items:
            if item.timestamp >= commit.timestamp:
                break
            if isinstance(item, Review):
                comments_to_add = [comment for comment in item.comments if comment.timestamp < commit.timestamp]
                new_review = Review(id_=item.id_, author=item.author, body=item.body, comments=comments_to_add)
                items_before_commit.append(new_review)
            else:
                items_before_commit.append(item)

        return items_before_commit


class Repo:
    def __init__(self, owner: str, name: str):
        self.owner = owner
        self.name = name
        self.pull_requests = self.init_pull_requests()

    def init_pull_requests(self) -> list[PullRequest]:
        pull_requests = GithubApi.get(
            f"/repos/{self.owner}/{self.name}/pulls",
            params={
                "sort": "popularity",
                "direction": "desc",
                "state": "all",
                "per_page": "5",
            },
        )
        pr_objects = []
        for pr in pull_requests:
            pr_id = pr["number"]
            title = pr["title"]

            # Comments
            raw_comments = GithubApi.get(f"/repos/{self.owner}/{self.name}/issues/{pr_id}/comments")
            comments = [
                Comment(
                    id_=comment["id"],
                    author=comment["user"]["login"],
                    body=comment["body"],
                    timestamp=datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                )
                for comment in raw_comments
            ]

            # Commits
            raw_commits = GithubApi.get(f"/repos/{self.owner}/{self.name}/pulls/{pr_id}/commits")
            commits = []
            for raw_commit in raw_commits:
                commit_detail = GithubApi.get(f"/repos/{self.owner}/{self.name}/commits/{raw_commit['sha']}")
                commits.append(
                    Commit(
                        id_=raw_commit["sha"],
                        author=raw_commit["commit"]["author"]["name"],
                        message=raw_commit["commit"]["message"],
                        timestamp=datetime.strptime(raw_commit["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ"),
                        diff=[
                            FilePatch(filename=file_["filename"], patch=file_.get("patch", ""))
                            for file_ in commit_detail["files"]
                            if file_["status"] in ["added", "modified", "removed"]
                        ],
                    )
                )

            # Reviews
            raw_reviews = GithubApi.get(f"/repos/{self.owner}/{self.name}/pulls/{pr_id}/reviews")
            reviews = []
            for review in raw_reviews:
                raw_review_comments = GithubApi.get(
                    f"/repos/{self.owner}/{self.name}/pulls/{pr_id}/reviews/{review['id']}/comments"
                )
                if len(raw_review_comments) == 0:
                    continue

                review_comments = [
                    Comment(
                        id_=comment["id"],
                        author=comment["user"]["login"],
                        body=comment["body"],
                        timestamp=datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    )
                    for comment in raw_review_comments
                ]
                reviews.append(
                    Review(
                        id_=review["id"],
                        author=review["user"]["login"],
                        body=review["body"],
                        comments=review_comments,
                    )
                )

            pr_objects.append(PullRequest(id_=pr_id, title=title, comments=comments, commits=commits, reviews=reviews))
        return pr_objects

    def get_file_content(self, commit_id: str, filename: str):
        file_content = GithubApi.get(f"/repos/{self.owner}/{self.name}/contents/{filename}?ref={commit_id}")
        file_content_encoding = file_content.get("encoding")
        if file_content_encoding == "base64":
            file_content = base64.b64decode(file_content["content"]).decode()

        return file_content


if __name__ == "__main__":
    repo = Repo("JetBrains", "context-plugin")

    for pr in repo.pull_requests:
        sorted_items = pr.get_all()
        for item in sorted_items:
            if isinstance(item, Comment):
                print(f"Comment by {item.author} at {item.timestamp}: {item.body}")
            elif isinstance(item, Commit):
                print(f"Commit at {item.timestamp}: {item.message}")
            elif isinstance(item, Review):
                print(f"Review by {item.author} at {item.timestamp}: {item.body}")
                for comment in item.comments:
                    print(f"  Comment by {comment.author} at {comment.timestamp}: {comment.body}")
