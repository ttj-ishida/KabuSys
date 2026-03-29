# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム & 自動売買リサーチ基盤です。J-Quants からのデータ取得・ETL、ニュース収集と NLP による銘柄スコアリング、OpenAI を使ったマクロセンチメント評価、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）の初期化などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date.now 等に依存しない設計）
- DuckDB をデータストアに利用（ETL / 解析用）
- 冪等（idempotent）な保存ロジック
- API 呼び出しに対する堅牢なリトライ / レート制御
- テスト容易性のため設定を環境変数／.env で管理

---

## 機能一覧

- 環境変数/設定管理（自動 .env ロード、必須チェック）
- J-Quants API クライアント（株価・財務・市場カレンダー取得、保存）
  - レート制御、トークン自動リフレッシュ、リトライ実装
- ETL パイプライン（日次 ETL: カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア生成）
- 市場レジーム判定（ETF 1321 の MA200 乖離 × マクロセンチメントの合成）
- 研究用ファクター計算（Momentum / Value / Volatility 等）と統計ユーティリティ
- 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
- DuckDB / SQLite などへのパス設定サポート

---

## 要件

- Python 3.10 以上
- 主な依存（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の細かな依存は実際の requirements.txt を参照してください）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをチェックアウトしてパッケージをインストール（編集可能インストール推奨）

   git clone <repo>
   cd <repo>
   pip install -e .

2. 必要な Python パッケージをインストール

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそちらを使用）

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

   必須環境変数（少なくとも以下は設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（使用する場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（使用する場合）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を実行する場合）

   任意 / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース用ディレクトリ作成（必要であれば）
   mkdir -p data

---

## 使い方（サンプル）

以下は Python から直接インポートして使う例です。すべての API は高水準の関数を提供します。

- DuckDB 接続を作成して日次 ETL を実行する（例）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントをスコアして ai_scores に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
  print("written:", n_written)

- 市場レジームを判定して market_regime に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要

- 監査ログ用 DB を初期化する

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

- マーケットカレンダー関数利用例

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

- 研究系: ファクター計算

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,3,20))

注意:
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。関数は api_key 引数でキーを渡すことも可能です。
- ETL 実行や保存は DuckDB に対して実行されます。適切なスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）が存在する前提です（ETL の最初に schema 初期化ユーティリティ等を用意してください）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py (パッケージ初期化、バージョン)
- config.py (環境変数 / .env 自動ロード、Settings)
- ai/
  - __init__.py
  - news_nlp.py (ニュース NLP スコアリング)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - calendar_management.py (マーケットカレンダー操作)
  - etl.py (ETL インターフェース再エクスポート)
  - pipeline.py (日次 ETL パイプライン)
  - stats.py (汎用統計ユーティリティ)
  - quality.py (データ品質チェック)
  - audit.py (監査ログスキーマ初期化)
  - jquants_client.py (J-Quants API クライアント & 保存関数)
  - news_collector.py (RSS ニュース収集)
- research/
  - __init__.py
  - factor_research.py (Momentum/Value/Volatility 等)
  - feature_exploration.py (forward_returns, IC, rank, summary)
- monitoring, strategy, execution, etc. （__all__ で将来公開される名前空間）

---

## 開発メモ / 注意点

- 設計上、多くの関数は「ルックアヘッドバイアス防止」のため date.today() 等を直接参照しません。テストやバッチ実行の際は target_date を明示して呼び出してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行います。配布後やテスト時に自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に空リストを渡すと問題が出るバージョンがあるため、コード内で空チェックが入っています。
- OpenAI 呼び出しはリトライ・バックオフ処理あり。テストでは _call_openai_api をモックして差し替えることを推奨します。
- news_collector では SSRF 防止・gzip の上限チェック・XML パースの安全化（defusedxml）などを実装しています。

---

もし README に追加したい情報（実際の requirements.txt、スキーマ初期化スクリプトの例、CI/テスト手順、CLI ツールなど）があれば教えてください。必要に応じてサンプル .env.example や DB スキーマ作成コマンドのテンプレートも作成します。