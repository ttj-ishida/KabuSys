# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP による銘柄スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）などを含みます。

主な設計方針：
- ルックアヘッドバイアス防止（内部処理で datetime.today()/date.today() を直接参照しない設計）
- DuckDB をメインの分析 DB として利用（冪等保存 / ON CONFLICT ロジック）
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を備えフェイルセーフに設計
- テスト容易性のため関数注入やモックによる差し替えを想定

---

## 機能一覧

- data
  - J-Quants クライアント（fetch / save）
    - 株価日足（OHLCV）取得 / 保存
    - 財務データ取得 / 保存
    - JPX マーケットカレンダー取得 / 保存
  - ETL パイプライン（差分取得、品質チェック、日次実行）
  - カレンダー管理（営業日判定、next/prev trading day、calendar 更新ジョブ）
  - ニュース収集（RSS → raw_news 保存、SSRF/サイズ制限/トラッキング除去などの保護）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（signal_events / order_requests / executions テーブル）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント scoring: score_news）
  - 市場レジーム判定（ETF1321 の MA とマクロニュースセンチメントを合成: score_regime）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリー等）
- config
  - 環境変数読み込み（.env / .env.local 自動読み込み／上書きルール）
  - settings オブジェクト経由で設定値にアクセス

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用）
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml

例（簡易）:
pip install duckdb openai defusedxml

プロジェクトをパッケージとしてインストールする場合は pyproject.toml 等があれば:
pip install -e .

---

## 環境変数 / .env

config.Settings が参照する主な環境変数：

必須
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

オプション / デフォルトあり
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で利用）

自動 .env ロード:
- パッケージ起点でプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で読み込みます。
- OS 環境変数が優先されます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡易 .env.example:
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. Python 環境を用意（推奨: venv）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクト化されている場合）
   pip install -e .

3. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定してください。
   - 必須トークン（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を用意します。

4. DuckDB スキーマ / 監査ログを初期化（必要に応じて）
   - 監査ログ専用 DB を初期化する例（Python スクリプト）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

5. ログ設定
   - 実行アプリ側で logging.basicConfig(level=settings.log_level) 等を設定してください。

---

## 使い方（主要 API の例）

- 日次 ETL 実行（J-Quants から市場カレンダー・株価・財務を差分取得 → 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP による銘柄別スコアリング（score_news）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定
  print(f"書き込み銘柄数: {n}")

- 市場レジーム判定（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または api_key 引数で渡す

- カレンダー更新ジョブ（calendar_update_job）
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"保存レコード数: {saved}")

- 監査ログ初期化（init_audit_db / init_audit_schema）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

注意点:
- OpenAI 呼び出しは API 利用料が発生します。テスト時は _call_openai_api をモックすることを推奨します（news_nlp / regime_detector 内に差し替えポイントあり）。
- ETL / ニュース収集は外部 API に依存するためネットワーク・認証情報を正しく準備してください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                         # 環境変数 / settings
- ai/
  - __init__.py
  - news_nlp.py                      # ニュース NLP（score_news）
  - regime_detector.py               # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                # J-Quants API クライアント（fetch/save）
  - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
  - etl.py                           # ETLResult re-export
  - calendar_management.py           # マーケットカレンダー管理
  - news_collector.py                # RSS ニュース収集
  - quality.py                       # データ品質チェック
  - stats.py                         # 統計ユーティリティ（zscore_normalize）
  - audit.py                         # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py               # Momentum / Value / Volatility 計算
  - feature_exploration.py           # 将来リターン / IC / サマリー
- monitoring/ (参照はあるがコードベースの一部は抜粋されている可能性があります)

各モジュールは docstring と実装コメントで設計方針・注意点を詳細に記載しています。まずは ETL とデータ保存部分（jquants_client、pipeline）、その後 AI 部分（news_nlp / regime_detector）を環境構築して順に試すことを推奨します。

---

## 開発・テスト時のヒント

- OpenAI 呼び出しをテストする際は、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えてください。
- ネットワークアクセスや外部 API を切りたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して .env 自動ロードを無効化できます（テスト内で環境を手動構成する際に便利）。
- DuckDB はファイルベースでもインメモリ（":memory:"）でも利用可能です。テストでは ":memory:" を指定してスピード優先で実行できます。

---

この README はコードベースの主要機能と利用手順を概説したものです。具体的なユースケース（実運用での発注フローや Slack 通知の実装、バックテスト統合など）は別途アプリケーション層の実装により提供してください。必要であれば、README にサンプルスクリプトやより詳細な設定例を追記します。