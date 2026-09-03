# D3-tools — real structured-merge tools, tested

Transcripts of the actual runs are in `TRANSCRIPT-daff.txt` and
`TRANSCRIPT-mergiraf.txt`. The build artifacts are deleted (72 MB); rebuild with:

    npm install daff                        # daff 1.4.2 -> node_modules/.bin/daff
    cargo install --root ./mergiraf-install --locked mergiraf   # 0.19.0

then `bash run-daff.sh` and `bash run-mergiraf.sh`.

Findings are written up in `../../design-findings/D3-diff-merge.md` §2.
