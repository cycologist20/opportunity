$t = "AI in preventative healthcare"
poetry run python -m ok_mvp --topic $t
$yt = Join-Path "output" (($t -replace " ", "_") + "_youtube.json")
$ax = Join-Path "output" (($t -replace " ", "_") + "_arxiv.json")
if ((Test-Path $yt) -and (Test-Path $ax)) {
  Write-Host "SMOKE PASS"
} else {
  Write-Host "SMOKE FAIL"; exit 1
}
