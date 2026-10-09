## sample workflow

```text
main
  ↓
create feature branch
  ↓
develop
  ↓
commit
  ↓
push branch
  ↓
create pr
  ↓
another teammate reviews & approves
  ↓
merge into main
```

## 1. clone the repo

```bash
git clone https://github.com/strob3/panataanph-hackathon-2026.git
```

go to `main` and pull the latest version:

```bash
git checkout main
git pull origin main
```

## 2. create feature branch

create a new branch for the feature

```bash
git checkout -b feat/my-feature
```

### Branch naming

```text
feat/<feature>     New feature
fix/<bug>          Bug fix
docs/<topic>       Documentation
refactor/<topic>   Code refactoring
```

## 3. develop

the feature branch is separate from `main`, so the changes won't affect the main project until your PR is merged.

## 4. push your branch

```bash
git push -u origin feat/my-feature
```

—after the first push:

```bash
git push
```

## 5. create PR

select:

```text
base: main
compare: feat/my-feature
```

the PR should merge:

```text
feat/my-feature → main
```

## 6. review then merge the PR

## 7. update your local repo

after the PR is merged, update your local `main` before starting another task:

```bash
git checkout main
git pull origin main
```

then create next feature branch:

```bash
git checkout -b feat/next-feature
```

# reference

### start

```bash
git checkout main
git pull origin main
git checkout -b feat/my-feature
```

### save

```bash
git add .
git commit -m "feat:"
```

### push your branch

```bash
git push -u origin feat/my-feature
```

### on github

```text
create PR
        ↓
base: main
compare: your branch
        ↓
review
        ↓
approve
        ↓
merge
```

