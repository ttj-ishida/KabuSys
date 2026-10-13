# 手動約定の同日・同銘柄・同売買の複数登録 設計

- Issue: #411
- ブランチ: `feature/issue-411-multi-manual-trades`
- 関連: #410（手動約定入力・助言モード）

ユーザーから「自動で進められる部分は自動で進める」と指示を受けている。以下の判断はユーザー確認を経ずに決めたもので、PR で確認してもらう。

## 1. 現状の問題

- `build_manual_trade_id` が `MANUAL_{date}_{code}_{side}` を返すため、同日・同銘柄・同売買の約定は 1 件しか登録できない。
- `force=True`（CLI `--force`、GUI チェックボックス）を使うと、既存の約定を削除してから登録する。分割約定の 2 件目を登録しようとすると、1 件目が消える。
- `calculate_manual_positions` は約定を `trade_date, created_at, trade_id` の順に処理する。同日に SELL を BUY より先に入力すると、SELL の時点で保有が 0 株のため数量が 0 に切り詰められ、SELL が実質的に無視される。
- 保有を超える SELL（売り過ぎ）は黙って 0 に切り詰められる。

## 2. 決定事項

### 2.1 約定 ID

- 1 件目は従来どおり `MANUAL_{date}_{code}_{side}` とする。既存データとの互換を保つため、既存データの移行は不要。
- 2 件目以降は `MANUAL_{date}_{code}_{side}_{n}` とする。n は 2 から始まり、まだ使われていない最小の番号を割り当てる。
- `build_manual_trade_id(trade_date, code, side)` は 1 件目の ID を返す関数として残す。ID の採番は新しい内部関数で行う。

### 2.2 同一内容の二重入力の検知

- 約定日・銘柄・売買・数量・単価・手数料がすべて一致する約定が既にある場合は、`DuplicateManualTradeError` を送出する。
- 本当に同じ内容の約定が 2 件ある場合は、`allow_duplicate=True` を指定すれば登録できる。
- 内容が異なる約定（数量や単価が違う分割約定など）は、確認なしで追加の番号付き ID で登録する。

### 2.3 `force`（上書き）の廃止

- `add_manual_trade` の `force` 引数は `allow_duplicate` に置き換える。既存の約定を削除する経路はなくす。修正したい場合は、`delete` で削除してから登録し直す。
- CLI: `--allow-duplicate` を追加する。`--force` は互換のため残すが、意味は `--allow-duplicate` と同じとし、help に「非推奨」と書く。既存の約定は消さない。
- GUI: チェックボックスを「同じ内容の約定をもう 1 件登録する」に変更し、`allow_duplicate` に渡す。

### 2.4 同日内の処理順

- `calculate_manual_positions` の並び順を `trade_date, BUY を先・SELL を後, created_at, trade_id` にする。
- 同日内のデイトレード（売ってから買い直す）は想定しない。このため、同日の SELL は同日の BUY を含めた保有に対して処理される。

### 2.5 売り過ぎ

- `add_manual_trade` は、SELL の数量がその約定日時点の保有（同日の BUY を含む）を超える場合、`OversellError`（`ValueError` のサブクラス）を送出する。
- 手動記録を始める前から持っていた株を売る場合など、正当な理由がある場合に備えて `allow_oversell=True` で登録できるようにする。CLI は `--allow-oversell`、GUI はチェックボックス「保有を超える売却を許可する」で指定する。
- `calculate_manual_positions` は、売り過ぎた分を従来どおり 0 に切り詰めたうえで、`logger.warning` を出す。
- `calc_manual_portfolio_value` の現金計算は、実際に受け取った売却代金を全額計上する（現状維持）。保有の切り詰めと食い違う場合があることを docstring に明記する。

## 3. テスト

- 同日・同銘柄・同売買で内容の異なる 2 件を登録すると、ID が `…_buy` と `…_buy_2` になり、保有数量・平均単価に両方が反映される。
- 3 件目は `_3` になる。`_2` を削除した後に登録すると `_2` を再利用する。
- 同一内容の 2 件目は `DuplicateManualTradeError` になる。`allow_duplicate=True` なら `_2` で登録できる。
- `force` 引数は存在しない（既存のテスト `test_add_manual_trade_force_replaces_existing` は、新しい仕様のテストに置き換える）。
- 同日に SELL を BUY より先に入力しても、保有が正しく計算される。
- 保有を超える SELL は `OversellError` になる。`allow_oversell=True` なら登録でき、保有計算では警告が出る（caplog で確認）。
- CLI: `--allow-duplicate`、`--allow-oversell`、非推奨の `--force` の動作（`main([...])` で検証）。
- 2 件目以降の約定も、`calc_manual_portfolio_value` の現金計算に反映される。

## 4. 対象外

- 約定の編集機能（削除して登録し直す運用とする）
- CSV 一括投入（ユーザー判断で不要）
