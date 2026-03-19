# KabuSys

日本株向けの自動売買 / データプラットフォーム向けライブラリです。  
DuckDB をデータレイクとして用い、J-Quants などから市場データを取得して ETL → 品質チェック → 特徴量生成 → 戦略評価 / 発注監査までのワークフローをサポートします。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants API からの日足・財務・カレンダー取得（差分取得・ページネーション対応）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS → 正規化 → DuckDB 保存、銘柄紐付け）
- 研究用ユーティリティ（ファクター計算、将来リターン・IC 計算、Zスコア正規化）
- 監査ログ（signal → order_request → execution のトレース用スキーマ）
- 環境変数ベースの設定管理（.env 自動読み込み機能）

設計方針として、本番の発注 API や外部ライブラリに過度に依存せず、DuckDB と標準ライブラリ／最小限の依存で完結するようにしています。ETL・データ処理は冪等（idempotent）に実装されています。

---

## 機能一覧

主な機能（モジュール）:

- kabusys.config
  - 環境変数管理、.env/.env.local の自動読み込み、必須設定チェック
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義・初期化
  - pipeline: 日次差分 ETL（prices / financials / market_calendar）と品質チェック
  - news_collector: RSS 取得・前処理・DB保存・銘柄抽出
  - calendar_management: JPX カレンダー管理、営業日の判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 発注・約定の監査テーブル初期化
  - stats: Zスコア正規化などの統計ユーティリティ
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクターサマリー
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - （パッケージプレースホルダ。戦略ロジックや発注実行、監視周りを配置）

主な特徴:
- DuckDB を用いた軽量かつ高速な分析/保存
- J-Quants 用の堅牢な HTTP 層（固定間隔スロットリング、リトライ、トークン管理）
- RSS 収集に対する SSRF / XML Bomb 対策（URL検証、defusedxml、受信サイズ制限）
- 品質チェックを ETL の一部として標準実行可能

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒントで union 型表記を使用）
- ネットワーク接続（J-Quants API などへアクセスする場合）

1. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. インストール（最低必要パッケージ）
   - pip install duckdb defusedxml

   （プロジェクトをパッケージとしてインストールする場合）
   - pip install -e .

   ※ requirements.txt / pyproject.toml がある場合はそちらを使ってください。

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（Settings により参照）:
   - JQUANTS_REFRESH_TOKEN (J-Quants リフレッシュトークン)
   - KABU_API_PASSWORD (kabuステーション API パスワード) — 発注を使う場合
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知に使用する場合)

   任意:
   - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
   - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH (データベースファイルパス, デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (監視用 SQLite 等)

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 初期スキーマ作成
   - Python REPL またはスクリプトで DuckDB 接続を作成し、スキーマを初期化します（init_schema を使うと Raw/Processed/Feature/Execution 層が作成されます）。
   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

5. 監査ログ用スキーマ（任意: audit 専用テーブル）
   ```python
   from kabusys.data import audit
   # 既存の conn に監査スキーマを追加
   audit.init_audit_schema(conn, transactional=True)
   # または専用 DB に初期化
   # audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主なユースケース例）

以下は代表的な使い方の一部。実運用用の CLI / orchestration は別途実装してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ today（自動で営業日に調整）
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出用に有効な銘柄コードの集合を渡す（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

4) ファクター計算 / 研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
momentum = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
value = calc_value(conn, target)

# 将来リターンの取得
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# IC の計算（例: mom_1m と fwd_1d のランク相関）
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

5) J-Quants からのデータ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

# id_token を省略すると内部キャッシュから自動で取得・リフレッシュされます
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存は save_daily_quotes を利用
from kabusys.data.jquants_client import save_daily_quotes
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
save_daily_quotes(conn, records)
```

注意:
- J-Quants API はレート制限（120 req/min）やエラーハンドリングを組み込んでいます。長時間の大量取得はレートに配慮してください。
- ニュース収集は外部 URL を取得するため、ネットワークセキュリティ周り（プロキシ・接続先検査）に注意してください。fetch_rss は SSRF 対策や受信サイズ制限を実装しています。

---

## ディレクトリ構成

主要ファイル / パッケージ構成（src/kabusys 以下）:

- __init__.py
- config.py
  - 環境変数・.env 自動ロード、Settings クラス
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - news_collector.py     — RSS 収集・正規化・保存・銘柄抽出
  - schema.py             — DuckDB スキーマ定義と init_schema / get_connection
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - features.py           — features 公開インターフェース（zscore_normalize 再エクスポート）
  - calendar_management.py— 市場カレンダー更新・営業日判定ユーティリティ
  - audit.py              — 監査ログ（signal / order_request / executions）スキーマ
  - etl.py                — ETL 公開インターフェース（ETLResult 再エクスポート）
  - quality.py            — データ品質チェック
- research/
  - __init__.py           — 研究用ユーティリティ再エクスポート
  - factor_research.py    — ファクター計算（momentum / value / volatility）
  - feature_exploration.py— 将来リターン・IC・サマリー等
- strategy/
  - __init__.py           — 戦略層（プレースホルダ）
- execution/
  - __init__.py           — 発注層（プレースホルダ）
- monitoring/
  - __init__.py           — 監視系（プレースホルダ）

README の情報はコード内の docstring を元にまとめています。各モジュールの詳細は該当ファイルの docstring / 関数ドキュメントを参照してください。

---

## 注意事項 / ベストプラクティス

- 本ライブラリはデータ取得・特徴量生成・監査ログの土台を提供しますが、実際の自動売買運用ではリスク管理・取引回路の確実性・法令順守が重要です。必ずペーパートレーディングで検証してください。
- 環境依存の設定（API トークン等）は .env に保存する際、十分にアクセス制御された場所に置いてください。
- DuckDB ファイルは破損リスクを軽減するため定期的なバックアップを推奨します。
- 自動ロードされる .env の挙動をテストで制御したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

必要であれば、この README をベースに CLI 例（cron / airflow / systemd 単位での実行例）、運用フロー図、サンプル .env.example ファイルやユニットテスト用モックの例も作成できます。どの情報を追加したいかお知らせください。