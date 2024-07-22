from random import choice

from src.api import GithubApi
from src.generator import OpenaiModel
from src.repo import Comment, Commit, Repo, Review

COMMENTS_THRESHOLD = 5


def ask_gpt_to_find_good_example(items: list[Comment, Review, Commit]):
    print("\n================================\n")
    TASK = """\
You are given a list of comments, commits and reviews taken from a pull request.
Find the best commit whose message can be improved by knowing the comments and reviews before it.
That means the current commit message could miss infos from the chat before.
Return current commit message then provide with a better commit message and explain why it relates to the comments before."""

    PROMPT = ""

    for item in items:
        PROMPT += f"* {item.summary()}\n\n\n"

    PROMPT += "Commit hash: "

    gpt_model = OpenaiModel("gpt-4")
    result = gpt_model.ask(TASK, PROMPT)
    print(result)


def find_good_example(owner, repo_name):
    print("\033[94m" + f"Searching for good example in {owner}/{repo_name}..." + "\033[0m")
    repo = Repo(owner, repo_name)
    pull_requests = list(filter(lambda pr: pr.comments_count > COMMENTS_THRESHOLD, repo.pull_requests))
    print(
        f"Found {len(pull_requests)}/{len(repo.pull_requests)} pull requests with more than {COMMENTS_THRESHOLD} comments."
    )

    for pr in pull_requests:
        print("\033[92m" + f"Processing pull request {pr.id_}..." + "\033[0m")
        try:
            all_items = pr.get_all()
            # find index of the first comment or review
            first_comment_or_review_index = next(
                i for i, item in enumerate(all_items) if isinstance(item, Comment) or isinstance(item, Review)
            )
            # find the last index of a commit
            last_commit_index = next(i for i, item in reversed(list(enumerate(all_items))) if isinstance(item, Commit))
            relevant_items = all_items[first_comment_or_review_index : last_commit_index + 1]

            if len(relevant_items) < 2:
                print("\033[93m" + "Not enough comments and reviews to find a good example." + "\033[0m")
                continue

            for item in relevant_items:
                if isinstance(item, Commit):
                    item.generated_message = item.generate_message(repo)

            ask_gpt_to_find_good_example(relevant_items)
        except:
            print("\033[91m" + "Error while processing pull request." + "\033[0m")


if __name__ == "__main__":
    # test_on_random_commit()
    open_source_repos = GithubApi.get_open_source_projects(30)
    for repo in open_source_repos:
        find_good_example(repo.split("/")[0], repo.split("/")[1])
