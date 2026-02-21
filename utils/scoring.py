def score_repo(repo: dict, weights: dict) -> float:
    """Score a repository based on weighted signals."""
    score = 0.0

    # Star score — normalized, capped at 10k
    star_score = min(repo.get("stars", 0) / 10000, 1.0)
    score += star_score * weights.get("stars", 0.3)

    # Commit recency score
    days = repo.get("last_commit_days")
    if days is not None:
        if days <= 7:
            recency_score = 1.0
        elif days <= 30:
            recency_score = 0.8
        elif days <= 90:
            recency_score = 0.5
        elif days <= 365:
            recency_score = 0.2
        else:
            recency_score = 0.0
    else:
        recency_score = 0.3  # unknown, neutral
    score += recency_score * weights.get("commit_recency", 0.3)

    # Fork score — sign of adoption
    fork_score = min(repo.get("forks", 0) / 1000, 1.0)
    score += fork_score * weights.get("forks", 0.2)

    # Issue health — lower open issues relative to stars is better
    stars = repo.get("stars", 1)
    issues = repo.get("open_issues", 0)
    issue_ratio = issues / max(stars, 1)
    issue_score = max(0.0, 1.0 - issue_ratio * 10)
    score += issue_score * weights.get("issue_health", 0.2)

    return round(score, 4)


def score_package(package: dict, weights: dict) -> float:
    """Score a PyPI package based on weighted signals."""
    score = 0.0

    # Star score
    star_score = min(package.get("stars", 0) / 10000, 1.0)
    score += star_score * weights.get("stars", 0.3)

    # Release freshness
    days = package.get("release_days")
    if days is not None:
        if days <= 30:
            freshness_score = 1.0
        elif days <= 90:
            freshness_score = 0.7
        elif days <= 365:
            freshness_score = 0.4
        else:
            freshness_score = 0.1
    else:
        freshness_score = 0.3
    score += freshness_score * weights.get("release_freshness", 0.3)

    # Dependent repos — sign of real-world adoption
    dep_score = min(package.get("dependent_repos", 0) / 1000, 1.0)
    score += dep_score * weights.get("dependent_repos", 0.4)

    return round(score, 4)


def get_weights_from_context(intent: dict) -> dict:
    """Adjust scoring weights based on coordinator intent."""
    weights = {
        "stars": 0.3,
        "commit_recency": 0.3,
        "forks": 0.2,
        "issue_health": 0.2,
        "release_freshness": 0.3,
        "dependent_repos": 0.4
    }

    prioritize = intent.get("prioritize", "balanced")

    if prioritize == "recency":
        weights["commit_recency"] = 0.5
        weights["stars"] = 0.2
        weights["release_freshness"] = 0.5

    elif prioritize == "popularity":
        weights["stars"] = 0.5
        weights["commit_recency"] = 0.2
        weights["dependent_repos"] = 0.5

    elif prioritize == "stability":
        weights["stars"] = 0.4
        weights["issue_health"] = 0.4
        weights["commit_recency"] = 0.2

    return weights