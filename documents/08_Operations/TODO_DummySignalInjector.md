# TODO: テスト用ダミーシグナル注入CLIの作成

## 1. 背景と目的
現在のKabuSysでは、ペーパートレード（仮想売買）環境で「特定の銘柄だけを発注テストしたい」場合、夜間バッチが生成した実際の `signal_queue` をそのまま読み込む仕様になっており、手軽に任意の銘柄をテストすることが難しい。
この課題を解決するため、任意の銘柄のダミーシグナル（買い/売り）を `signal_queue` テーブルに直接注入するCLIツールを作成する。

これにより、新しい戦略の実装後や、発注ロジックのデバッグ時に、意図した銘柄・数量でのペーパートレード検証が迅速に行えるようになる。

---

## 2. 実装要件 (TODO)

- [ ] **スクリプトの作成**
  - ファイルパス: `src/kabusys/tools/inject_dummy_signal.py`
  - `argparse` を用いて、CLIから必要なパラメータを受け取るようにする。

- [ ] **CLI引数の定義**
  - `--code` (必須): 銘柄コード（例: 7203）
  - `--side` (必須): 売買区分（`BUY` または `SELL`）
  - `--qty` (オプション): 注文数量（デフォルト: 100株など）
  - `--date` (オプション): 対象日（`YYYY-MM-DD` 形式。省略時は翌営業日または当日とする）

- [ ] **DuckDBへのデータ投入処理**
  - `config.Settings` から `DUCKDB_PATH` を読み込み、DBに接続する。
  - `signal_queue` テーブルに対し、指定された条件でレコードを `INSERT` する。
  - 投入するレコードは、本番の夜間バッチが生成するシグナルと同じスキーマ形式を満たすこと（`id`, `date`, `code`, `side`, `qty`, `created_at` 等）。

- [ ] **既存データとの競合ハンドリング**
  - 既に同じ日付・銘柄コードでシグナルが存在する場合の挙動を定義する（上書きする、あるいはエラーにする）。

- [ ] **README への追記**
  - ツールが完成したら、`README.md` の「使い方（よく使うコマンド例）」セクションにツールの使用方法を追記する。

---

## 3. 想定される利用フロー

1. テストしたい銘柄のダミーシグナルを注入する
   ```bash
   python -m kabusys.tools.inject_dummy_signal --code 7203 --side BUY --qty 100
   ```
2. Signal Queueレポートで注入されたことを確認する
   ```bash
   python -m kabusys.run_signal_queue_report
   ```
3. ペーパートレード環境で Execution Engine を起動し、指定銘柄が正しく発注・約定シミュレーションされるか確認する
   ```bash
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
