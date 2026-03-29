# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API や RSS から市場データ・ニュースを取得して DuckDB に保存し、AI（OpenAI）を用いたニュースセンチメントや市場レジーム判定、ファクター計算、ETL パイプライン、監査ログ機能などを提供します。

主な設計方針としては「ルックアヘッドバイアスを避ける」「ETL と保存は冪等（idempotent）」「外部 API 呼び出しはリトライとレート制御を備える」「DuckDB を中心とした軽量なデータレイヤ」を採用しています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・JPX カレンダーを差分取得（ページネーション対応、リトライ・レート制御）
  - ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックを順に実行
  - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）

- ニュース収集 / NLP
  - RSS フィード取得と安全対策（SSRF 対策、gzip 上限、XML 攻撃防御）
  - ニュースを銘柄に紐付け raw_news / news_symbols テーブルへ保存
  - OpenAI を用いた銘柄別ニュースセンチメント算出（ai.score_news）
  - マクロ記事を使った市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理
  - 発注フローの UUID 連鎖による完全トレース化、冪等 key（order_request_id）対応

- 設定管理
  - .env ファイル / 環境変数読み込み（自動ロード、優先順位: OS 環境変数 > .env.local > .env）
  - 環境変数の必須チェックとユーティリティ（kabusys.config.settings）

---

## 動作要件（推奨）

- Python 3.10+
- 必須パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging 等）

requirements.txt が無い場合は上記パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）し仮想環境を作成・有効化:

   bash:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール:

   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. 環境変数を準備:
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。自動読み込みはデフォルトで有効です。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（オプション、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack bot token（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - OPENAI_API_KEY: OpenAI API キー（ai 関連関数で使用）
   - 自動 env 読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

4. DuckDB の初期スキーマや監査 DB を作成（必要に応じて）:
   - 監査 DB を別ファイルに作る場合の例:

     python:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（基本例）

以下は主要な操作を行う際の簡単な Python スニペット例です。

- DuckDB 接続の作成:

  python:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）:

  python:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(res.to_dict())

- ニュースセンチメント算出（OpenAI を使用）:

  python:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - # api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  - print(f"written scores: {n_written}")

- 市場レジーム判定（ETF 1321 の MA + マクロ記事の LLM 評価）:

  python:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - result = score_regime(conn, target_date=date(2026,3,20))
  - print("score_regime done:", result)

- 監査ログ用 DB を初期化（監査スキーマの作成）:

  python:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- J-Quants の生データ取得（必要に応じて直接利用可能）:

  python:
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  - quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))

注意:
- AI 呼び出しは OpenAI の API キー（OPENAI_API_KEY）を必要とします。関数引数で api_key を渡すこともできます。
- 多くの操作は外部 API を呼ぶためネットワーク環境および API 制限（レート・料金）に注意してください。

---

## 主なモジュール / 主要機能の概要

- kabusys.config
  - 環境変数管理、.env 自動ロード、settings（必須 env のチェック、パス設定、環境判定ユーティリティ）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: ETL のメインロジック（run_daily_etl 他）
  - quality: データ品質チェック
  - news_collector: RSS 収集と前処理（SSRF 対策・XML 防御）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査テーブルの初期化 / 監査ログ管理
  - stats: 汎用統計ユーティリティ（Zスコア正規化など）
  - etl: ETLResult 型の再エクスポート

- kabusys.ai
  - news_nlp: ニュースセンチメント算出（batch を使った OpenAI への問い合わせ、レスポンス検証、スコア書き込み）
  - regime_detector: ETF（1321）の MA とマクロ記事 LLM を合成して市場レジーム判定

- kabusys.research
  - factor_research: Momentum, Value, Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリー 等
  - zscore_normalize は data.stats から提供

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - quality.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - audit.py
  - (その他: schema 初期化等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ファクター・リサーチ関連）
- (package version: kabusys.__version__ = "0.1.0")

（上記はコードベースに含まれる主なモジュール・ファイル一覧です）

---

## 実運用時の注意点と設計上のポイント

- Look-ahead バイアスの回避: 多くのモジュールは内部で date.today()/datetime.today() を直接参照せず、target_date を明示的に渡して処理します。バックテスト時は取得済みデータと処理日付を明確にすること。
- 冪等性: ETL / 保存処理は ON CONFLICT DO UPDATE などで冪等設計になっています。部分失敗時でも既存データを不必要に消さないよう配慮されています。
- 外部 API 呼び出し:
  - J-Quants クライアントは固定間隔レートリミッタと再取得ロジックを備えています。
  - OpenAI 呼び出しは JSON Mode を使いレスポンス検証・リトライを行います。API キーの管理とコストに注意してください。
- セキュリティ: news_collector は SSRF 対策・XML injection 対策・レスポンスサイズ上限などを実装しています。RSS ソース追加時も安全性を意識してください。

---

## トラブルシューティング

- 環境変数が読み込まれない場合:
  - デフォルトでプロジェクトルート（.git または pyproject.toml がある）を起点に `.env` / `.env.local` を自動ロードします。テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
  - 必須の環境変数が未設定の場合、kabusys.config.settings のプロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

- DuckDB 関連:
  - executemany に空のリストを渡すとインターフェース制約によりエラーとなる箇所があるため、実行前に空チェックが行われています。スキーマ初期化やテーブル名に注意してください。

---

必要であれば README の補足（例: .env.example のテンプレート、より具体的な ETL 実行スクリプト、Docker / systemd 用の起動例、CI テスト方法など）を追加できます。どの情報を追加したいか教えてください。