
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
        pushedAt
        defaultBranchRef {
          target {
            oid
          }
        }
      }
    }
  }
}
"""



REPO_DEP_QUERY  = """
query GetRepoDependencies($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    dockerfile: object(expression: "HEAD:Dockerfile") { id }
    dockerfile_lower: object(expression: "HEAD:dockerfile") { id }
    docker_compose: object(expression: "HEAD:docker-compose.yml") { id }
    docker_compose_yaml: object(expression: "HEAD:docker-compose.yaml") { id }
    compose_yaml: object(expression: "HEAD:compose.yaml") { id }
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



IMAGE_QUERY = """
query GetLibImage($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    homepageUrl
    usesCustomOpenGraphImage
    openGraphImageUrl

    logo_root: object(expression: "HEAD:logo.svg") {
      ... on Blob { text }
    }
    logo_assets: object(expression: "HEAD:assets/logo.svg") {
      ... on Blob { text }
    }
    logo_docs: object(expression: "HEAD:docs/logo.svg") {
      ... on Blob { text }
    }
    logo_github: object(expression: "HEAD:.github/logo.svg") {
      ... on Blob { text }
    }
    logo_png: object(expression: "HEAD:logo.png") {
      id 
    }
  }
}
"""