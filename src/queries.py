
REPOS_QUERY = """
query GetUserRepositories($owner: String!, $cursor: String) {
  user(login: $owner) {
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: [OWNER]
      orderBy: { field: PUSHED_AT, direction: DESC }
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        nameWithOwner
        isFork
        isPrivate
        url
      }
    }
  }
}
"""



REPO_DEP_QUERY  = """
query GetRepoDependencies($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    dependencyGraphManifests(first: 20) {
      nodes {
        filename
        dependencies(first: 100) {
          nodes {
            packageName
            requirements
            packageManager
          }
        }
      }
    }
  }
}
"""

