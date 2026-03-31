# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ KabuSys の README です。本リポジトリはデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、データ品質チェック、特徴量計算、監査ログ（DuckDB）など、機械学習／運用バッチに必要なコンポーネント群を提供します。

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームおよび研究／自動売買基盤のコンポーネント群を提供します。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等データの差分 ETL
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリング（銘柄単位）とマクロレジーム判定
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ファクター計算・特徴量探索（Momentum / Value / Volatility 等）
- 監査ログ（signal → order → execution のトレース）用スキーマの初期化ユーティリティ
- DuckDB を利用したローカル永続化

設計上の注意点として、バックテストでのルックアヘッドバイアスを防ぐため、内部処理では date.today() / datetime.today() を直接参照しない等の配慮がされています。

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ
- データ ETL（kabusys.data.pipeline, jquants_client）
  - 差分取得・ページネーション・レート制御・リトライ
  - 保存（DuckDB）時の冪等化（ON CONFLICT）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・JPX カレンダー差分更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、トラッキングパラメータ除去、SSRF 対策、raw_news への保存想定
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとのニュース集約、OpenAI へのバッチ送信、レスポンス検証・スコア保存（ai_scores）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 研究用（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン、IC 計算、Z スコア正規化
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
- 監査ログ（kabusys.data.audit）
  - 監査テーブルの DDL / 初期化、監査 DB 初期化ユーティリティ
- 共通統計ユーティリティ（kabusys.data.stats）

## セットアップ手順

1. Python 環境（3.10+ 推奨）を用意し、仮想環境を作成・有効化します。

   - 例（Unix/macOS）
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストールします（代表的な依存を記載します）。プロジェクトに requirements.txt がない場合は下記を参考にしてください。

   pip install duckdb openai defusedxml

   開発・運用で追加が必要なパッケージ（例）
   - requests（任意）
   - slack-sdk（Slack 通知を使う場合）
   - psycopg2 / その他（必要に応じて）

3. リポジトリ内からパッケージをインストール（編集可能モード）

   pip install -e .

4. 環境変数を設定します。プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。

   必須（本番的に動かす場合）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN       : Slack Bot トークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID      : Slack チャネル ID
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注機能を使う場合）
   - OPENAI_API_KEY        : OpenAI API キー（AI モジュールを使う場合）

   省略時のデフォルト値:
   - KABUSYS_ENV (development | paper_trading | live) → default: development
   - KABUSYS のログレベル (LOG_LEVEL) → default: INFO
   - DUCKDB_PATH → data/kabusys.duckdb
   - SQLITE_PATH → data/monitoring.db

   .env の書き方（例）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...

## 使い方（代表的な呼び出し例）

ここではライブラリ関数を直接呼んで利用する例を示します。実行は Python スクリプトやバッチジョブ（systemd, cron, GitHub Actions 等）で行う想定です。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニューススコアリング（指定日）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {cnt} stocks")

- 市場レジーム判定（指定日）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DB）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成される

- カレンダージョブ（JPX カレンダー更新）

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")

注意点:
- OpenAI を使う関数は api_key 引数を受け取ります。引数を渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- J-Quants 呼び出しは settings.jquants_refresh_token を利用して id_token を取得します（自動リフレッシュあり）。
- DuckDB の接続は呼び出し側で用意して渡す設計です。

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注機能で使用）
- KABUSYS_ENV: environment ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 以下）:

- __init__.py
- config.py
  - .env 自動読み込み、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py         : ニュースを銘柄単位で集約して OpenAI に送りスコア化する
  - regime_detector.py  : ETF(1321) の MA200 乖離 + マクロセンチメントで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（取得 / 保存関数）
  - pipeline.py         : 日次 ETL パイプライン（run_daily_etl など）
  - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
  - news_collector.py   : RSS 取得・前処理・保存ロジック
  - quality.py          : データ品質チェック
  - stats.py            : z-score 正規化等統計ユーティリティ
  - audit.py            : 監査ログスキーマ初期化
  - etl.py              : ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py  : Momentum / Value / Volatility 等の計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー など

各モジュールは docstring に設計方針・処理フロー・副作用（DB 書き込み等）を明記してあり、ユニットテスト用に内部呼び出しを差し替えやすい設計になっています（例: OpenAI 呼び出しの差し替え、HTTP のモックなど）。

## 運用上の注意・ベストプラクティス

- ルックアヘッドバイアス防止: 本ライブラリはバックテストでのルックアヘッドを避ける設計を多く取り入れています。target_date を明示的に渡して処理することで意図しないデータリークを防いでください。
- API レートとトークン: J-Quants のレート制限を守るため内部に RateLimiter 実装があります。J-Quants のリフレッシュトークンは安全に管理してください。
- OpenAI への入力: ニュース送信にはバッチ化やトリミング（文字数制限）を行っています。API 呼び出しエラー時はフォールバックの挙動が定義されていますが、API 利用料に注意してください。
- DuckDB ファイルはバックアップしておくと安全です（特に監査ログは削除しない前提の運用が想定されています）。
- テスト時に .env の自動ロードを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README に含めたい追加情報（例: CI 設定、実運用の systemd / supervisor サンプル、SQL スキーマ定義の詳細、例 .env.example）を教えてください。README をそれに合わせて拡張します。