# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants）、DuckDBベースのデータスキーマ、ETLパイプライン、特徴量計算（ファクター）、ニュース収集、データ品質チェック、監査ログなど、戦略実行に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群を含むパッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に蓄積する ETL
- DuckDB 上のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と記事 -> 銘柄紐付け
- ファクター（モメンタム／ボラティリティ／バリュー等）および研究補助関数（IC, forward returns 等）
- 監査ログ（シグナル〜発注〜約定のトレーサビリティ）

設計方針として、可能な限り外部ランタイムへの副作用を避け、DuckDB/標準ライブラリ中心で実装されています。J-Quants へのアクセスは rate limit と再試行ロジックを備えています。

---

## 主な機能（抜粋）

- データ取得・保存
  - J-Quants クライアント（fetch/save 日足・財務・カレンダー）
  - 差分更新・バックフィル対応の ETL（pipeline.run_daily_etl）
  - DuckDB スキーマの初期化（data.schema.init_schema）
- データ品質
  - 欠損検出、主キー重複、スパイク（急騰/急落）、日付不整合検出（data.quality）
- ニュース収集
  - RSS 取得、前処理、記事ID正規化（SHA-256）、raw_news 保存、銘柄抽出と紐付け
  - SSRF や XML Bomb、レスポンスサイズ制限などの安全対策
- ファクター / 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value（research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（research.feature_exploration）
  - zscore_normalize（data.stats）
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブルと初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（kabusys.config.settings）

---

## 必要条件

- Python 3.10+
  - （型アノテーションに `|` が使われているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

例（pip）:
```
pip install duckdb defusedxml
```

プロジェクトでは他に標準ライブラリのみで実装された部分が多く、外部依存は最小限です。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置する。

2. 仮想環境を作成して依存をインストール:
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

3. 環境変数（.env）を用意する  
   プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（CWD ではなくソースファイル位置からプロジェクトルートを検出します）。例:

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードを無効化する（テストなどで）:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマの初期化  
   Python REPL やスクリプトで schema.init_schema を実行します。デフォルトの DUCKDB_PATH は settings.duckdb_path で参照できます。

   例:
   ```python
   from kabusys.config import settings
   from kabusys.data import schema
   conn = schema.init_schema(settings.duckdb_path)
   ```

   監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（市場カレンダー・日足・財務を取得して品質チェック）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data import schema, pipeline

  # スキーマ初期化（初回のみ）
  conn = schema.init_schema(settings.duckdb_path)

  # ETL 実行（target_date 省略で today）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes: 有効銘柄コードのセット（抽出に使用）
  known_codes = {"7203", "6758", ...}
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)
  ```

- カレンダー更新ジョブ（夜間バッチ）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 研究 / ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.research import calc_momentum, calc_forward_returns, zscore_normalize

  conn = get_connection("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  mom = calc_momentum(conn, t)
  fwd = calc_forward_returns(conn, t)
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- J-Quants から日足を直接フェッチ→保存:
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  ```

---

## 環境変数 / 設定一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) 既定: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) 既定: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env 読み込みを無効化

これらは kabusys.config.Settings 経由で型安全に取得できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - schema.py                       — DuckDB スキーマ定義・初期化
    - stats.py                        — 統計ユーティリティ（z-score など）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - features.py                     — 特徴量ユーティリティ（公開インターフェース）
    - calendar_management.py          — カレンダー更新・営業日判定
    - audit.py                         — 監査ログテーブル定義・初期化
    - etl.py                          — ETL 公開インターフェース（再エクスポート）
    - quality.py                      — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py          — forward returns / IC / summary
    - factor_research.py              — momentum / volatility / value 等
  - strategy/                         — 戦略層（モジュール雛形）
  - execution/                        — 発注/ブローカーや実行層（雛形）
  - monitoring/                       — 監視・メトリクス（雛形）

---

## 注意事項 / 実運用上のポイント

- J-Quants API はレート制限（120 req/min）に対応するため内部でスロットリングを行います。大量ページングを行う場合は時間がかかる点に注意してください。
- jquants_client は 401 発生時にトークン自動リフレッシュ + 1 回リトライを行います。
- news_collector は SSRF・XML Bomb・巨大レスポンス対策を組み込んでいますが、外部ソースの扱いには注意が必要です。
- DuckDB スキーマに ON DELETE CASCADE 等の一部機能は DuckDB バージョンに依存しているため、実装上コメントとして扱われている箇所があります。運用時はデータ削除手順に注意してください。
- テストや CI で .env の自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 開発・貢献

- コードはモジュール単位で再利用できるよう分割されています。研究用関数（research）とデータ処理（data）は副作用を抑え、DuckDB 接続を引数に取る設計です。
- 新しいチェックや ETL ステップを追加する際は data.quality や data.pipeline の設計方針（Fail-Fast ではなく全件収集）に従ってください。

---

この README はコードベースの主要機能をまとめたものです。実際の運用スクリプト（バッチやデプロイ方法）、詳細な API キー管理ポリシー、CI/CD、監査要件等は別途プロジェクト固有の運用ドキュメントにまとめてください。