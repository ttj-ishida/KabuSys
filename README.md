# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買（調査・シグナル生成・監査）を支援するライブラリ群です。  
DuckDB をデータストアとして用い、J-Quants API や RSS / OpenAI（LLM）を組み合わせてデータ収集・品質チェック・AI スコアリング・ファクター計算・監査ログ初期化などを行います。

---

## 主な特徴（機能一覧）

- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得 & 保存（冪等）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分更新・バックフィル・品質チェックを組み合わせた日次 ETL（run_daily_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 & NLP（news_collector, news_nlp）
  - RSS からの安全なニュース取得（SSRF 対策、XML の安全パース）
  - ニュースを銘柄ごとに集約して LLM でセンチメント評価（JSON mode）
- 市場レジーム判定（regime_detector）
  - ETF（1321）の200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - シグナル → 発注 → 約定までのトレーサビリティを保証する監査スキーマの初期化・管理
- コンフィグ管理
  - .env / .env.local または環境変数ベースで設定管理（自動ロード機能あり。無効化可能）

---

## 必要な依存パッケージ（代表例）

本リポジトリは下記のライブラリに依存します（抜粋）:

- duckdb
- openai（OpenAI Python SDK v1 系想定）
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

インストール例（仮）:

pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをチェックアウト / clone してパッケージをインストール（任意）

   git clone <repo-url>
   cd <repo>
   pip install -e .

2. 環境変数 / .env の準備

   必須な環境変数（Settings で参照されるもの）:
   - JQUANTS_REFRESH_TOKEN      （必須） — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD          （必須） — kabuステーション等の API パスワード
   - SLACK_BOT_TOKEN           （必須） — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID          （必須） — Slack チャンネル ID
   - OPENAI_API_KEY            （LLM を使う機能を使う場合に必要）
   - DUCKDB_PATH               （任意、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH               （任意、監視用 sqlite パスのデフォルト: data/monitoring.db）
   - KABUSYS_ENV               （任意、development / paper_trading / live。デフォルト development）
   - LOG_LEVEL                 （任意、DEBUG/INFO/...。デフォルト INFO）

   例: .env（プロジェクトルートに置く）

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   自動読み込みについて:
   - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local をプロセス起動時に自動読み込みします。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利です）。

3. データベース用ディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 使い方（例）

以下は主要機能の簡単な実行例です。実環境ではログ設定や例外処理を適切に行ってください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントスコアを生成して ai_scores に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)

  ※ OpenAI API キーは環境変数 OPENAI_API_KEY、または score_news の api_key 引数で渡します。

- 市場レジームの判定（regime score）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB の初期化:

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

- 研究用ファクター計算の実行:

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, target_date=date(2026,3,20))
  v = calc_value(conn, target_date=date(2026,3,20))

- データ品質チェック:

  from datetime import date
  import duckdb
  from kabusys.data.quality import run_all_checks

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点:
- 多くの関数は look-ahead bias を避けるため内部で datetime.today() を参照しない設計です。target_date を明示して呼び出してください。
- OpenAI 呼び出しはリトライ・フォールバックロジックを持ちますが、API キー未設定時は ValueError を送出します。
- J-Quants 関連の API 呼び出しは rate limit を守るために内部でスロットリングします。

---

## 設定（主要な環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring) のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — execution 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- OPENAI_API_KEY — OpenAI API キー（LLM を使う機能で使用）

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / .env の読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py           — ニュース NLP（LLM 呼び出し・バッチ処理）
  - regime_detector.py    — 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py           — ETL パイプライン（run_daily_etl など）
  - etl.py                — ETLResult のエクスポート
  - news_collector.py     — RSS 取得と前処理
  - calendar_management.py— カレンダー（market_calendar）管理・営業日ロジック
  - quality.py            — データ品質チェック
  - stats.py              — 共通統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログ（schema 初期化 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py    — モメンタム / ボラティリティ / バリュー 等
  - feature_exploration.py— 将来リターン / IC / 統計サマリー 等
- research/*, data/*, ai/*  はそれぞれの機能群

---

## 開発・テスト時の便利な点

- 自動 .env 読み込みを無効にする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI / J-Quants の外部呼び出しは、テスト時に各モジュール内の _call_openai_api や jquants_client._request 等を mock して差し替える設計になっています。

- DuckDB の executemany の制約（空リスト不可）や JSON パース時の余分なテキストへの寛容性など、実運用で遭遇するケースに対する保護ロジックが組み込まれています。

---

この README はコードの主要な使い方と構造をまとめたものです。各モジュール内の docstring に細かい仕様・設計思想・戻り値（型）が記載されていますので、詳細はソースコードを参照してください。必要であれば、実行例スクリプトや運用手順（cron / Airflow など）向けのサンプルも作成できます。