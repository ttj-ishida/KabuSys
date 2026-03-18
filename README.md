# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants / DuckDB を中心としたデータ収集・ETL、品質チェック、特徴量生成、ニュース収集、監査ログ管理などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を含みます。

- J-Quants API からの株価・財務・カレンダーの取得（レート制御／リトライ／トークン自動更新対応）
- DuckDB を用いたデータベーススキーマ（Raw / Processed / Feature / Execution 層）の初期化・保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、トラッキングパラメータ除去）
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）および統計ユーティリティ（Zスコア正規化、IC 計算）
- 監査ログ（シグナル → 発注 → 約定までのトレースを保持する監査スキーマ）

設計方針として、本番口座や発注 API には直接アクセスしないデータ処理・研究系処理を安全に行えるようになっています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API からのページネーション対応取得（株価、財務、カレンダー）
  - トークン自動リフレッシュ、レートリミット、リトライ（指数バックオフ）
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- data/schema
  - DuckDB 上のスキーマ定義（raw_prices / prices_daily / features / signals / orders / executions / audit 等）
  - init_schema() による一括初期化

- data/pipeline
  - 差分更新 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を表す ETLResult（品質チェック結果・エラー情報を含む）

- data/news_collector
  - RSS フィード取得 / 正規化 / raw_news への保存
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）
  - SSRF 対策・gzip 制限・XML パース安全化（defusedxml）

- data/quality
  - 欠損、スパイク（前日比）、重複、日付不整合などの品質チェック
  - run_all_checks による一括チェック

- research/factor_research, feature_exploration
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、統計サマリ（factor_summary）
  - zscore_normalize 再利用可能

- data/audit
  - シグナル／発注要求／約定の監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提:
- Python 3.9+（typing の | 型注釈が用いられているため）
- インターネット接続（J-Quants / RSS 取得）
- DuckDB を利用するためのディスク容量

1. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール（最低限）
   ※ プロジェクトの requirements.txt がある場合はそれを使用してください。ここでは主要パッケージ例を示します。
   ```
   pip install duckdb defusedxml
   ```

3. パッケージをインストール（開発モード）
   プロジェクトに pyproject.toml / setup.py がある場合:
   ```
   pip install -e .
   ```

4. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）。
   必須の環境変数（Settings クラスで _require されるもの）:

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注関連を使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合
   - SLACK_CHANNEL_ID      : Slack 通知を使う場合

   その他オプション:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO
   - DUCKDB_PATH, SQLITE_PATH — DB パス（デフォルトは data/ 以下）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要なサンプル）

以下はライブラリをプログラムから利用する例です。Python REPL やスクリプトで実行します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes に有効な銘柄コードの集合を渡すと、記事から銘柄抽出して紐付けします
  known_codes = {"7203", "6758", "9433"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- ファクター計算（モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # records: [{"date": ..., "code": "7203", "mom_1m": ..., "ma200_dev": ...}, ...]
  ```

- 将来リターンと IC（Information Coefficient）
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  # factor_records: calc_momentum 等の結果
  # forward_records: calc_forward_returns(conn, target_date)
  ic = calc_ic(factor_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
  ```

- 監査ログスキーマ初期化（監査専用 DB を分けたい場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

---

## よく使う設定・環境変数一覧

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu ステーション API パスワード
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（テスト時に利用）

自動で .env/.env.local を読み込む機能は、プロジェクトルート（.git または pyproject.toml を基準）から行われます。CWD に依存しない探索を行います。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring）
- config.py
  - 環境変数/設定管理（Settings クラス）

src/kabusys/data/
- __init__.py
- jquants_client.py
  - J-Quants API クライアント（取得 + 保存ユーティリティ）
- news_collector.py
  - RSS 収集、前処理、DB 保存、銘柄抽出
- schema.py
  - DuckDB スキーマ定義・初期化（init_schema / get_connection）
- pipeline.py
  - ETL パイプライン（差分取得・backfill・品質チェック）
- etl.py
  - ETLResult 再エクスポート
- features.py / stats.py
  - 統計ユーティリティ（zscore_normalize 等）
- calendar_management.py
  - market_calendar 管理・営業日判定
- quality.py
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- audit.py
  - 監査ログ（signal_events / order_requests / executions）定義と初期化

src/kabusys/research/
- __init__.py
  - 研究用関数をエクスポート
- feature_exploration.py
  - 将来リターン計算 / IC / factor_summary / rank
- factor_research.py
  - Momentum / Volatility / Value 等のファクター計算

src/kabusys/strategy/
- __init__.py
  - 戦略関連（将来的な拡張ポイント）

src/kabusys/execution/
- __init__.py
  - 発注ロジック用（将来的に追加）

src/kabusys/monitoring/
- __init__.py
  - 監視・メトリクス収集（将来的に追加）

---

## トラブルシューティング / 注意点

- 環境変数が未設定の場合、Settings のプロパティで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）。
- DuckDB の初期化時に親ディレクトリが存在しない場合、自動で作成します。
- J-Quants API はレート制限（120 req/min）を遵守するため遅延が入ります。大量のバックフィルは時間がかかります。
- news_collector: RSS の XML は外部入力のためパースエラー等が起きうる点に注意。defusedxml を利用してある程度の防護はされています。
- ETL 中の品質チェックはデフォルトで警告を蓄積し、呼び出し元が致命度に応じて対処する設計です（Fail-Fast ではない）。

---

## 今後の拡張候補

- strategy / execution の具体的な発注ラッパー実装（kabu ステーション連携）
- モニタリング / アラート（Slack 連携の実装例）
- CLI / cron 用のラッパースクリプト
- 単体テスト・統合テストの充実（モック注入を前提に設計済みの箇所あり）

---

この README はコードベースの現状（各モジュールの docstring と実装）を基に作成しています。実際に運用する際は .env.example の作成、必要な権限情報（J-Quants トークン、Slack トークンなど）の安全管理を必ず行ってください。