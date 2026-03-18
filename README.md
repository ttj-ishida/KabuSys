# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants API からのデータ取得、ETL、品質チェック、特徴量生成、ニュース収集、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含みます。

- データ収集（J-Quants からの株価・財務・カレンダー取得）
- ETL（差分取得・冪等保存・品質チェック）
- DuckDB スキーマ定義と初期化
- ニュース（RSS）収集と銘柄紐付け
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→注文→約定のトレース）
- 研究用ユーティリティ（IC計算、Zスコア正規化など）

設計方針としては「本番口座・発注 API へ直接アクセスしない」「冪等操作」「Look-ahead バイアス対策」「外部依存は最小限」などが取られています。

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可能）
  - 必須変数取得のヘルパー
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックスや監査スキーマ初期化機能
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レートリミット管理・リトライ・トークン自動更新を備えた API 呼び出し
  - 日足・財務・マーケットカレンダーのページネーション対応取得
  - DuckDB への冪等保存（ON CONFLICT を用いる）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日をベースに差分を算出）
  - backfill による後出し修正吸収
  - 品質チェック実行（kabusys.data.quality）
- 品質チェック（kabusys.data.quality）
  - 欠損値、スパイク、重複、日付整合性などの検出
  - QualityIssue オブジェクトのリストで結果を返す
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・記事ID生成（URL正規化＋SHA256）・DB保存
  - SSRF 防御、gzip 制限、XML パース安全化（defusedxml）
  - テキストから有効銘柄コード抽出と news_symbols への紐付け
- 研究用モジュール（kabusys.research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン算出（calc_forward_returns）や IC（calc_ic）等
  - data.stats.zscore_normalize の再エクスポート

---

## 必要条件 / 依存

- Python 3.10+
- 必要なパッケージ（主に）:
  - duckdb
  - defusedxml

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトの完全な requirements.txt は別途管理してください）

---

## 環境変数

主に以下を期待します（設定が必須のものは README 内で明示）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API のパスワード（将来の発注系で使用）
- KABU_API_BASE_URL（任意）: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID（必須）: Slack チャネル ID
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意）: 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL（任意）: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

プロジェクトルートに .env / .env.local を置くと、自動で読み込まれます（不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

3. 環境変数を設定（.env を作成）
   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=yyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要ユースケース）

- 日次 ETL の実行（例: スケジューラから呼ぶ）
  ```python
  from datetime import date
  import duckdb

  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化済みであれば get_connection を使う
  conn = get_connection("data/kabusys.duckdb")

  # 今日分の ETL 実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行（既存 conn を使用）
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "6501", ...}  # 事前に取得した有効銘柄セット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存数}
  ```

- 研究用ファクター計算（DuckDB 接続と日付を渡す）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  forward = calc_forward_returns(conn, target)
  ```

- IC（Information Coefficient）計算
  ```python
  from kabusys.research import calc_ic
  ic = calc_ic(factor_records=mom, forward_records=forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

- J-Quants API を直接呼ぶ（テスト／独自取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 推奨運用フロー（例）

1. 夜間バッチで market_calendar を更新（calendar_update_job または run_calendar_etl）
2. 日次 ETL（run_daily_etl）を実行して prices/financials を取り込み
3. 品質チェック（run_all_checks）で問題を把握
4. 特徴量計算・正規化 → シグナル生成 → 発注（監査ログ記録）
5. ニュース収集は別ジョブで定期実行、news_symbols に紐付け

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得・保存）
  - news_collector.py  — RSS 取得・前処理・保存・銘柄抽出
  - schema.py  — DuckDB スキーマ定義と init_schema / get_connection
  - stats.py  — 統計ユーティリティ（zscore_normalize）
  - pipeline.py  — ETL パイプライン（run_daily_etl 等）
  - quality.py  — 品質チェック（欠損・スパイク・重複・日付整合性）
  - features.py — features モジュール公開インターフェース
  - calendar_management.py — market_calendar 管理 & 補助ユーティリティ
  - audit.py — 監査ログテーブル定義（signal_events / order_requests / executions）
  - etl.py — ETL 型の再エクスポート
- research/
  - __init__.py
  - factor_research.py  — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- strategy/
  - __init__.py (将来の戦略ロジック用)
- execution/
  - __init__.py (将来の発注ロジック用)
- monitoring/
  - __init__.py (監視・メトリクス用の拡張ポイント)

---

## 注意事項 / 実運用上のポイント

- J-Quants API のレート制限（120 req/min）や 401 リフレッシュ、429 Retry-After を考慮した実装になっていますが、運用時も API 制約に留意してください。
- ETL は差分・バックフィルを行いますが、初回は全期間の取得が行われ得ます（初回ロードの時間に注意）。
- news_collector は外部 URL を扱うため SSRF、gzip bomb、XML Bomb などに対して対策が組み込まれていますが、実行環境のネットワーク・セキュリティ設定も考慮してください。
- DuckDB ファイルはローカルファイルとして生成されるため、バックアップやパーミッションに注意してください。
- audit スキーマはトランザクション的に初期化するオプションがあります（init_audit_schema の transactional 引数）。

---

## 補足・開発メモ

- 多くの計算処理（ファクター計算・IC 等）は外部ライブラリに依存せず、標準ライブラリ＋DuckDB SQL で実装されています。これは依存軽量化とリプロデューサビリティの観点からの設計です。
- unit test や CI のためには KABUSYS_DISABLE_AUTO_ENV_LOAD を使い .env 自動ロードを無効にできます。
- Python 型注釈（| 型記法）や from __future__ annotations を使っているため Python 3.10 以上を推奨します。

---

必要があれば、README に含めるサンプルスクリプト、systemd / cron 向けのジョブ例、Dockerfile や CI 設定例を追加します。どれを優先してドキュメント化しましょうか？