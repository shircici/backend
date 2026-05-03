param(
  [ValidateSet("pytest", "django")]
  [string]$Runner = "pytest",
  [string]$Tag = "backend-test",
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"

Write-Host "Building image: $Tag"
docker build -t $Tag .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$commonEnv = @(
  "-e", "DJANGO_SECRET_KEY=dev",
  "-e", "DEBUG=False",
  "-e", "DJANGO_SETTINGS_MODULE=myproject.settings_test"
)

if ($Runner -eq "django") {
  Write-Host "Running Django tests in container (settings_test)"
  docker run --rm @commonEnv $Tag python manage.py test --settings=myproject.settings_test @Args
  exit $LASTEXITCODE
}

Write-Host "Running pytest in container (settings_test)"
docker run --rm @commonEnv $Tag pytest @Args
exit $LASTEXITCODE
