# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
Data ETL（J-Quants連携）、ニュースNLP（OpenAIベースのセンチメント解析）、市場レジーム判定、ファクター計算、監査ログ（オーダー／約定追跡）など、運用・リサーチ・戦略実行に必要なユーティリティを含みます。

---

## 特長（概要）

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）を安全に実行
  - レートリミット、指数バックオフ、トークン自動リフレッシュを実装
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ニュース収集・前処理（RSS）、ニュースを銘柄単位で集約して LLM へ投げるニュースNLP
  - gpt-4o-mini（JSON Mode）を想定したレスポンス検証とクリッピング
  - SSRF対策・XML攻撃対策・受信サイズ制限等の安全対策
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
- ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions の追跡、UUID ベースのトレーサビリティ）
- Look-ahead bias 回避・堅牢な設計方針に基づく実装

---

## 機能一覧（モジュールハイレベル）

- kabusys.config：環境変数 / .env 自動読み込み / 必須チェック
- kabusys.data
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client：J-Quants API クライアント + DuckDB 保存ユーティリティ
  - news_collector：RSS 取得・前処理・記事ID生成
  - calendar_management：市場カレンダー管理（営業日判定）
  - quality：データ品質チェック
  - audit：監査ログテーブル初期化 / init_audit_db
  - stats：zscore_normalize 等
- kabusys.ai
  - news_nlp.score_news：銘柄別ニュースセンチメント算出 → ai_scores に保存
  - regime_detector.score_regime：市場レジーム判定（ma200 + macro sentiment）
- kabusys.research：ファクター計算・特徴量解析（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等）

---

## 必要条件・依存

- Python 3.10+
- 主な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS）

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを優先してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. パッケージをインストール（編集可能な開発モード）
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.cfg があることを想定）

5. 環境変数の準備
   - ルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector を使う際）
   - 任意・デフォルト:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite (monitoring 用)（デフォルト: data/monitoring.db）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な実行例）

以下は Python REPL / スクリプトでの簡単な利用例です。

- DuckDB 接続を作成して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを算出して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化（監査テーブルを作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS を取得して記事リストを得る（単体）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  ```

注意:
- score_news / score_regime は OpenAI API キー（env または引数）を必要とします。
- ETL / 保存先の DuckDB パスは settings.duckdb_path（環境変数 DUCKDB_PATH）で制御します。
- 多くの操作は DB スキーマ（raw_prices, raw_financials, raw_news など）が存在する前提です。初期スキーマの準備はプロジェクトの schema 初期化ルーチン（別途用意されている可能性があります）を参照してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ root）  
└─ src/kabusys/
   - __init__.py
   - config.py                — 環境変数・.env 自動読み込み / settings
   - ai/
     - __init__.py
     - news_nlp.py            — ニュースNLP（score_news）
     - regime_detector.py     — 市場レジーム判定（score_regime）
   - data/
     - __init__.py
     - jquants_client.py      — J-Quants API クライアント＋保存ロジック
     - pipeline.py            — ETL パイプライン（run_daily_etl 等）
     - etl.py                 — ETLResult 再エクスポート
     - news_collector.py      — RSS 収集・前処理
     - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
     - stats.py               — 汎用統計（zscore_normalize）
     - quality.py             — データ品質チェック
     - audit.py               — 監査ログスキーマ初期化 / init_audit_db
   - research/
     - __init__.py
     - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
     - feature_exploration.py — 将来リターン / IC / summary / rank

---

## 設計上の注意点・運用メモ

- Look-ahead bias の抑止を各所で意識した実装（datetime.today() の直接参照回避、DB クエリの排他条件等）。
- J-Quants クライアントはレートリミット制御とリトライ（指数バックオフ）、401 時のトークン自動リフレッシュを実装。
- ニュース収集は SSRF、XML 攻撃、gzip bomb、応答上限などを考慮した安全実装。
- OpenAI 呼び出しはエラー時にフェイルセーフ（センチメント 0.0 にフォールバック）にして安定した運用を重視。
- DuckDB の executemany 空リスト制約等の互換性考慮があるため、直接SQLの実行フローに注意する必要があります。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定  
  → .env を準備し、必要なキー（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。
- API RateLimit / 429 エラー  
  → J-Quants は 120 req/min を守る必要があります。jquants_client は内部で制御しますが、短時間で大量リクエストを送るバッチは避けてください。
- OpenAI のレスポンスパースエラー  
  → ランタイムでは例外を投げず 0.0 にフォールバックします。ログ（WARNING）を確認してください。

---

もし README に追加したい項目（例: デプロイ手順、CI 設定、DB スキーマ定義やサンプル .env.example の内容など）があれば教えてください。必要に応じてサンプル .env.example やコマンドの細かいテンプレートも作成します。