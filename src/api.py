from random import sample
import requests

GITHUB_API_TOKEN = "your-api-key"


class GithubApi:
    @staticmethod
    def get(endpoint: str, params: dict = {}):
        url = f"https://api.github.com{endpoint}"
        headers = {"Authorization": f"token {GITHUB_API_TOKEN}"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_open_source_projects(n=5) -> list[tuple[str, str]]:
        raw_projects = GithubApi.get(
            "/search/repositories",
            {
                "q": "size:<1000000 is:public template:false",
                "sort": "stars",
                "order": "desc",
                "per_page": n * 4,
            },
        )["items"]

        # choose n random projects
        raw_projects = sample(raw_projects, n)

        return [project["full_name"] for project in raw_projects]


if __name__ == "__main__":
    repos = GithubApi.get_open_source_projects()
    for repo in repos:
        print(repo)
