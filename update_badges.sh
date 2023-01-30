#!/bin/sh
# Update Badges
NEW_BADGES_BRANCH_NAME="badge_updates/v$(semver bump minor $(yq e '.version' charts/agimus/Chart.yaml))"

if [ `git rev-parse --verify $NEW_BADGES_BRANCH_NAME 2>/dev/null` ]; then
  echo "fatal: New badge update branch already exists locally, check github to merge the current update branch: $NEW_BADGES_BRANCH_NAME"
elif [ ! `git ls-remote --heads git@github.com:$REPO_OWNER/$REPO_NAME.git $NEW_BADGES_BRANCH_NAME | wc -l` ]; then
  echo "fatal: New badge update branch already exists remotely, check github to merge the current update branch: $NEW_BADGES_BRANCH_NAME"
else
  echo "No current branch in progress, running script."
  git checkout -b $NEW_BADGES_BRANCH_NAME
  python3 badge_updater.py

	if [[ $(git status images/badges --porcelain) ]]; then
		make helm-bump-minor
		git add charts \
			&& git add migrations \
				&& git add images/badges \
				&& git commit -m "Committing Badge Update for v$(semver bump minor $(yq e '.version' charts/agimus/Chart.yaml)) - $(date)" \
				&& git push --set-upstream https://$GIT_TOKEN@github.com/$REPO_OWNER/$REPO_NAME.git $NEW_BADGES_BRANCH_NAME \
				&& git checkout main;
		echo "Badge Update Success"
	else
		git checkout main \
			&& git branch -D badge_updates/v$(semver bump minor $(yq e '.version' charts/agimus/Chart.yaml));
		echo "No-op"
	fi
fi