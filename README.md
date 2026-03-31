# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
J-Quants からのデータ ETL、ニュース収集・NLP（OpenAI）によるセンチメントスコアリング、リサーチ用ファクター計算、監査ログスキーマ、マーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得から前処理、AI によるニュース解析、ファクター計算、取引監査ログ管理までを一貫して扱えるライブラリです。以下を主にサポートします。

- J-Quants API による株価・財務・カレンダーの差分 ETL（レートリミット・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集（SSRF 防御・トラッキングパラメータ除去・冪等保存）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析 / 市場レジーム判定（JSON Mode 対応、リトライ／フォールバックあり）
- DuckDB をバックエンドにした ETL / 品質チェック / 監査ログの初期化・保存
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ

設計上の重要点:
- ルックアヘッドバイアス回避（多くの処理は内部で date を引数として受け、datetime.today() 参照を避ける）
- 冪等性（DB 保存は可能な限り ON CONFLICT / ユニークキー等で上書き対応）
- フェイルセーフ（外部 API 失敗時は例外を投げずフォールバックする箇所がある）
- 外部依存の抽象化（OpenAI 呼び出し等はテスト差し替えを想定）

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、環境変数管理
  - 必須環境変数の取得ユーティリティ

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数、ページネーション、トークン管理、レート制御、リトライ）
  - pipeline / etl: 日次 ETL パイプライン（市場カレンダー、株価、財務）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日判定・バッチ更新ジョブ
  - quality: データ品質チェック（欠損・重複・未来日付・スパイク）
  - audit: 監査（signal / order_request / executions）テーブルの初期化ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI へ送り ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を算出して保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats から zscore_normalize を再利用可能

---

## セットアップ手順

前提
- Python 3.9+（typing アノテーションや一部の標準機能を想定）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）

1. リポジトリをクローンしてインストール
   - 開発インストール例:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - または最低限の依存をインストール:
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置できます。
   - 自動読み込み順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   主要な環境変数（config.Settings 参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite3 DB（デフォルト: data/monitoring.db）
   - PID_FILE_PATH: 実行 PID ファイル（デフォルト: data/execution.pid）
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（デフォルト 90/85/90）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...

   - OpenAI API キーは OPENAI_API_KEY 環境変数または各関数の api_key 引数で渡します。

3. データベース初期化（監査ログなど）
   - 監査ログ用 DuckDB を初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
     ```
   - ETL・分析用の DuckDB は settings.duckdb_path を使うと便利:
     ```python
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（簡易例）

以下は代表的な利用フローの例です。

- 日次 ETL（株価・財務・カレンダー & 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（ai_scores へ保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数か、第3引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジーム判定（market_regime テーブルへ保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマの初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect(str("data/kabusys.duckdb"))
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出しは json_object(JSON Mode) を期待するため、返り値の検証やリトライロジックが組み込まれています。テストでは _call_openai_api をモックできます。
- 多くの関数は target_date 引数を必須（または明示的に渡すこと推奨）し、ルックアヘッドを防ぐ設計です。

---

## ディレクトリ構成

主要なファイル／モジュール構成（src/kabusys 以下）:

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
  - etl.py (ETLResult 再公開)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py

- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は主要モジュール。実装は src/kabusys 配下の各 .py を参照してください）

---

## 運用メモ / 注意事項

- .env 自動読み込み:
  - パッケージインポート時にプロジェクトルートを探索して .env を自動読み込みします。
  - 無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時便利）。

- OpenAI:
  - API 呼び出しはモデル gpt-4o-mini を想定しています。API キーは OPENAI_API_KEY に設定するか、各関数の api_key 引数で渡してください。
  - レスポンスの JSON パース失敗や API エラー時にはフォールバック（0.0 スコア等）する箇所があります。重大な停止を避けるための挙動です。

- J-Quants:
  - J-Quants 用のリフレッシュトークンは JQUANTS_REFRESH_TOKEN に設定してください。クライアントは自動で id_token を取得・キャッシュ・更新します。
  - API レート制限（120 req/min）を厳守するため内部に RateLimiter を実装しています。

- セキュリティ:
  - RSS 収集では SSRF 対策・受信サイズチェック・XML パースの安全化（defusedxml）を行っています。
  - DB 保存でのインジェクションはパラメータバインド（?）を利用して回避しています。

---

## テスト & 開発

- OpenAI、J-Quants、ネットワークリソース呼び出しはモック可能な箇所が設計されています（例: _call_openai_api の差し替え、news_collector._urlopen のモックなど）。
- config.py の自動 .env ロードを無効にすることで環境依存を切り離して単体テストが容易になります。

---

ご不明点があれば、用途（ETL の稼働スケジュール、バックテストとの連携、実運用での注意点など）を教えてください。README の追補（API リファレンス、例 .env.example、運用スクリプト例）を追加できます。