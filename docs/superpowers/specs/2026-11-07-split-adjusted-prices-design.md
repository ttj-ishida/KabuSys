# 株式分割・併合の補正（prices_daily の分割補正）設計

- Issue: #424（関連: #425 PER の TTM 化、#430 修正後の研究結果の再検証）
- ブランチ: `fix/issue-424-split-adjusted-prices`
- 方針はユーザーが承認済み（案 A：`prices_daily` を補正済みの株価にする）。

## 1. 現状（調査結果）

- `raw_prices.adj_factor`（J-Quants の `AdjFactor`。権利落ち日に分割比率の逆数。例 1:5 分割 → 0.2）は、初期データの取り込み（`data/bootstrap/loaders.py`）でのみ保存されている。2016-05-02〜2026-06-01 の期間に、1 以外の値が 2,574 件ある。
- 日次のデータ更新（`jquants_client.save_daily_quotes`）は `AdjFactor` を保存していない。2026-06 以降は NULL。
- `pipeline.py` の raw → prices_daily 同期（約 L340-380）は、補正前の値をそのままコピーしている。そのため **`prices_daily` は全期間で分割の補正がされていない**。
- 実例：485A0 は 2026-05-28 に 1:3 の分割（13,590 → 4,340）。阿波銀行（83880）は 2026-09-29 に 1:5 の分割（11,130 → 2,185。adj_factor は NULL）。

## 2. 決定事項

### 2.1 日次のデータ更新で調整係数を保存する
- `save_daily_quotes` で `AdjFactor`（v2 `/equities/bars/daily` のフィールド）を `raw_prices.adj_factor` に保存する。キーがない、または数値に変換できない場合は NULL。ON CONFLICT の UPDATE にも含める。

### 2.2 `prices_daily` を補正済みにする（後方補正）
- 銘柄ごとに、日付 d の補正倍率を **M(d) = Π_{t > d} f(t)**（d より後の全営業日の adj_factor の積。NULL は 1 とみなす）とする。
- `prices_daily` の open / high / low / close = raw × M(d)、volume = raw / M(d)（四捨五入して整数）、turnover = raw（売買代金は補正しない）。
- 最新日は M = 1 なので、**直近の株価は実際の株価と一致する**（手動注文の参照価格・保有の評価額は従来どおり）。
- **Look-ahead の扱い：** 補正に使う係数は、その時点の DB にあるデータだけである。バックテストは、実行時点の補正済み系列を使う。比率（リターン・モメンタム・ATR 比など）は分割の影響を受けなくなる。ただし過去の株価の絶対水準は、後の分割で変わる。そのため「株価 300 円以上」の足切りや 100 株単位の株数計算は、過去分がわずかにずれる。これは案 A の既知のトレードオフとして受け入れ、ドキュメントに明記する。
- **冪等な再構築関数：** `rebuild_adjusted_prices(conn, codes: list[str] | None = None) -> int` を `data/` 配下（例 `data/price_adjustment.py`）に置く。指定した銘柄（None なら adj_factor ≠ 1 を持つ全銘柄）について、raw_prices の全期間から prices_daily を作り直す。同期と同じ品質フィルタを適用し、何度実行しても同じ結果になる。
- **日次の同期：** 従来の範囲同期（raw → prices_daily）は、そのまま M(d) を掛けて書き込む。同期した範囲に adj_factor ≠ 1 の行が新たに現れた銘柄は、`rebuild_adjusted_prices(codes)` でその銘柄の全期間を作り直す（過去の行に新しい係数を反映するため）。
- **初回の移行：** `scripts/rebuild_adjusted_prices.py [--codes ...] [--dry-run]` を追加する。運用 DB で一度実行すると、既存の 2,574 件の分割・併合が反映される。DuckDB への書き込みが必要なので、スケジューラーと Execution が止まっていること（現在は停止中）を前提とする。

### 2.3 手動保有の分割補正
- `operations/manual_trades.py` の `_fold_manual_trades`（保有計算・売り過ぎチェックで共有）で、各約定の数量と単価を、評価日（as_of）の株数ベースに換算する。約定日より後で as_of 以前の adj_factor の積を F として、数量 = qty / F、単価 = price × F（手数料はそのまま）。
  - これをしないと、分割の翌日に、補正済みの終値と分割前の平均単価を比べて「−80% で損切り」と誤判定される。
- 換算後の数量は分割比率が整数なら整数になるが、念のため丸める（`round`）。
- 売り過ぎの判定・ID の採番・DB に保存する値（約定の生データ）は変更しない。換算は計算時だけ行う。
- 自動執行の保有（`positions` / SQLite）はブローカーが分割後の数量を返すため対象外。バックテストは補正済みの系列で一貫しているため変更不要。

### 2.4 2026-06 以降の欠けた調整係数
- `scripts/backfill_adj_factor.py --from YYYY-MM-DD --to YYYY-MM-DD`：日付ごとに `fetch_daily_quotes(date=...)` で再取得して `adj_factor` を保存し、影響のあった銘柄を `rebuild_adjusted_prices` で作り直す。J-Quants のプランで取得できない日付は、警告を出してスキップする。
- `scripts/detect_split_candidates.py [--from] [--to]`：adj_factor が NULL の期間で、前日比が約 1/2・1/3・1/4・1/5・1/10（または逆数）の日を「分割の候補」として一覧表示する（**表示のみで、DB には書き込まない**）。

## 3. テスト

- `save_daily_quotes` が AdjFactor を保存する（あり／なし／不正値）。
- `rebuild_adjusted_prices`：1:5 分割を含む系列で、分割前の終値が × 0.2、出来高が × 5 になり、最新日は不変。2 回目の実行で結果が変わらない。複数の分割があっても積で補正される。adj_factor が NULL の行は 1 とみなす。
- 日次の同期：新たに係数が出た銘柄の過去の行が作り直され、係数のない銘柄は従来どおり同期される。
- `_fold_manual_trades`：分割前に 100 株を 10,000 円で買い、1:5 分割後に評価すると 500 株・2,000 円になる。分割後に売った分も正しく相殺される。分割がなければ従来と同じ。
- `detect_split_candidates`：候補を検出し、DB には書き込まない。
- 既存テストが通ること（特に pipeline・bootstrap・manual_trades・backtest）。

## 4. 対象外

- `features` の過去分の再計算と、研究結果の再検証（#430）。
- 自動執行の保有の分割補正（ブローカー側の値を使う）。
