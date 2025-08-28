# create_thinker.ps1
# Build a minimal thinker/ package (controller + policy + state + reflect)

$folders = @(
  ".\thinker"
)

foreach ($f in $folders) {
  if (-not (Test-Path $f)) { New-Item -Path $f -ItemType Directory | Out-Null }
}

$files = @{
  ".\thinker\__init__.py" = @'
# thinker package
__all__ = ["controller", "policy", "state", "reflect"]
