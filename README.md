# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリ群です。  
ETL（J-Quants 経由の株価 / 財務 / カレンダー取得）、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）、研究用ユーティリティ、AI を使った市場レジーム判定等を含みます。

---

## 概要

KabuSys は日本株のデータプラットフォームと研究・自動売買層の基盤ライブラリです。主な目的は：

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- raw_news（RSS）収集と AI によるニュースセンチメント評価（OpenAI）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions の追跡用テーブル）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）

設計上、ルックアヘッドバイアス防止やフェイルセーフ（API障害時のフォールバック）、冪等性（DB書込は ON CONFLICT）を重視しています。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（rate limit / retry / token 自動リフレッシュ）
  - market calendar 管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - news_collector: RSS 収集、安全対策（SSRF、gzip制限、トラッキング除去）付き
  - quality: データ品質チェック（missing/spike/duplicates/date_consistency）
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースタイトル・本文をまとめて OpenAI に投げ、ai_scoresへ保存
  - regime_detector.score_regime: ETF 1321 MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
  - リトライ／バックオフ・JSON モードレスポンス処理等を実装
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数読み取り、自動 .env ロードをサポート

---

## セットアップ手順

1. リポジトリをクローン（パッケージルートに `pyproject.toml` や `.git` がある想定）:

   git clone <repo-url>
   cd <repo-dir>

2. Python パッケージをインストール（開発モードを推奨）:

   python -m pip install -e .

3. 依存ライブラリ（参考）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存は pyproject.toml / requirements.txt を参照してください）

4. 環境変数 / .env の設定

   プロジェクトルートの `.env` または `.env.local` ファイルに環境変数を配置できます。パッケージは起動時に自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（Settings から）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意（デフォルトを持つもの）:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - OPENAI_API_KEY        : OpenAI API キー（ai.score_news / regime_detector で使用）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite パス（デフォルト: data/monitoring.db）

   .env の例 (.env.example を参考に作成):

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（簡易例）

以下はライブラリ API を直接使うサンプルです。実運用ではログ設定や例外ハンドリングを適切に行ってください。

- DuckDB 接続（ファイル or :memory:）

  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL を実行（J-Quants トークンは settings か引数で提供）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースをスコアリングして ai_scores に書き込む（OpenAI API キー必要）

  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} codes")

- 市場レジームスコアを計算して market_regime に保存する

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB を初期化

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対して監査ログを書き込むことができます

- 設定オブジェクトの利用

  from kabusys.config import settings
  print(settings.duckdb_path)
  if settings.is_live:
      # ライブ向けのロジック
      pass

注意点:
- AI を使う関数は OpenAI の JSON mode（gpt-4o-mini 等）を想定しています。レスポンス検証・リトライが組み込まれていますが、APIキーやコスト管理には注意してください。
- J-Quants API はレート制限があるため jquants_client は内部でレート制御を行います。大量取得時は時間を要します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージ初期化。__version__ = "0.1.0"
- config.py
  - 環境変数・Settings の読み取りと .env 自動ロード機能
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースセンチメントの集約・OpenAI 呼び出し・ai_scores 書込ロジック
  - regime_detector.py
    - ETF 1321 の MA200 とマクロニュース LLM を合成して market_regime を更新
- data/
  - __init__.py
  - calendar_management.py
    - market_calendar 管理・営業日判定・カレンダー更新ジョブ
  - etl.py
    - ETLResult の再エクスポート
  - pipeline.py
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL パイプライン
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - jquants_client.py
    - J-Quants API クライアント（fetch / save 関数、トークン管理、rate limiter、retry）
  - news_collector.py
    - RSS 収集、前処理、SSRF 対策、raw_news 保存補助
- research/
  - __init__.py
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility
  - feature_exploration.py
    - calc_forward_returns / calc_ic / factor_summary / rank

（上記は主要モジュールの抜粋です。実際のリポジトリ内のファイルを参照してください）

---

## 動作・設計上の注意点

- ルックアヘッドバイアス対策
  - 日付計算は内部で明示的な target_date を受け取り、datetime.today() 等に依存しない実装が多く採用されています。バックテスト時は必ず過去データのみを使用してください。
- 冪等性
  - DB への保存は ON CONFLICT（または UPSERT）で冪等化されています。ETL 再実行が想定されています。
- フェイルセーフ
  - AI API や外部 API の失敗時は例外を上位に伝播させない設計（0.0 フォールバックやスキップ）も採用されている箇所があります。運用ポリシーに合わせログや retry を調整してください。
- テスト
  - 内部で API 呼び出しをラップしているため、テスト時はモック差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api を patch）。

---

## 追加情報

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト環境で自動読み込みを避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用します。モデルやトークンは Settings / 引数で指定できます。
- J-Quants API の認証はリフレッシュトークンから id_token を取得するフローをサポートし、401 発生時は自動でリフレッシュして再試行します。

---

もし README に追加したい内容（例: CI / テスト手順、詳細な .env.example、データベーススキーマ等）があれば教えてください。必要に応じて具体的なコマンドやサンプルスクリプトを追記します。