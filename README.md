# KabuSys

日本株向け自動売買プラットフォームのライブラリ群。データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量計算（リサーチ）、ニュースセンチメント（LLM）、市場レジーム判定、監査ログ（発注〜約定トレーサビリティ）などを提供します。

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要APIの例）
- 環境変数一覧（必須・任意）
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要
KabuSys は日本株の自動売買システム構築を支援する内部ライブラリセットです。  
主に以下の役割を担います。
- J-Quants API を用いた株価・財務・上場情報・カレンダーの差分取得（ETL）
- RSS からのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別・マクロ）
- 市場レジーム判定（ETF の MA200 とマクロセンチメントの融合）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal / order_request / executions）用スキーマと初期化ユーティリティ
- 簡易的な kabuステーション API 設定（設定管理モジュール）

設計上の方針として、バックテスト時のルックアヘッドバイアスを避ける実装、外部呼び出しに対する堅牢なリトライ・フェイルセーフが重視されています。

---

## 主な機能一覧
- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（レート制限・リトライ・トークン自動更新）
  - NewsCollector: RSS 取得、SSRF対策、前処理、raw_news への保存補助
  - calendar_management: 営業日判定・カレンダー更新バッチ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ作成・監査DB初期化
  - stats: zscore 正規化等汎用統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: 市場レジーム（bull / neutral / bear）を判定して market_regime に保存
  - OpenAI 呼び出しは安全にリトライを行い、失敗時はフェイルセーフ（スコア 0）で継続
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得（settings オブジェクト）

---

## セットアップ手順（開発用）
推奨 Python バージョン: 3.10+

1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 依存ライブラリをインストール
   pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt がある場合はそれを利用してください）
4. 開発インストール（任意）
   pip install -e .
5. 環境変数設定
   プロジェクトルートの .env またはシステム環境変数に必要なキーを設定します（下記参照）。
   自動読み込みはデフォルトで有効です。テスト等で無効化する場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

デフォルトの DB パス:
- DuckDB（データ）: data/kabusys.duckdb
- SQLite（モニタリング）: data/monitoring.db

---

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で使用）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot Token（通知実装がある場合）
- SLACK_CHANNEL_ID: Slack チャネル ID
- KABU_API_PASSWORD: kabuステーション API のパスワード

OpenAI 関連:
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

.env の基本例:
JQUANTS_REFRESH_TOKEN="xxxx"
OPENAI_API_KEY="sk-xxxx"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABU_API_PASSWORD="your_password"
KABUSYS_ENV=development

---

## 使い方（主要 API の例）
以下はライブラリを直接インポートして利用する基本例です。DuckDB の接続オブジェクト（duckdb.connect(...)）を渡して利用します。

- ETL を日次で走らせる（例）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）を算出して DB に保存:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {written} codes")

- 市場レジーム判定:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算:
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))

- 監査ログ DB 初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions が作成されます

- データ品質チェック:
  from datetime import date
  import duckdb
  from kabusys.data.quality import run_all_checks
  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)

注意点:
- OpenAI 呼び出しを伴う処理（score_news / score_regime）は OPENAI_API_KEY が必要です。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN を使って id_token を取得します。
- 実行は DuckDB に想定テーブルが存在することが前提です（ETL で自動作成される場合があります）。

---

## ディレクトリ構成（主要ファイルの説明）
src/kabusys/
- __init__.py
  - パッケージのバージョンとサブモジュール露出設定
- config.py
  - .env 自動読み込み、Settings オブジェクト（環境変数管理）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースを LLM でセンチメント化し ai_scores テーブルに保存。バッチ処理・リトライ・レスポンス検証を実装。
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成し market_regime テーブルへ保存。
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（認証・リトライ・レート制御・保存関数）
  - pipeline.py
    - ETL 実行ロジック（run_daily_etl, run_prices_etl, ...）と ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS 収集、SSRF 対策、正規化、raw_news への永続化補助
  - calendar_management.py
    - market_calendar テーブル管理、営業日判定、カレンダー更新ジョブ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py
    - 監査ログテーブル DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py
    - Momentum / Value / Volatility / Liquidity の計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー等

その他:
- src/kabusys/ai/__init__.py、src/kabusys/research/__init__.py 等は公開 API を整理

---

## 注意点・運用上のヒント
- ルックアヘッドバイアス対策: 多くの関数は date 引数を受け取り、内部で date.today() を直接参照しない実装になっています。バックテスト時は適切な target_date を指定してください。
- OpenAI 呼び出し失敗時はフェイルセーフ（スコア 0）にフォールバックする設計ですが、API 使用量やレスポンス検証は必ず運用側でモニタリングしてください。
- J-Quants API はレート制限が厳しいため、jquants_client モジュールのレートリミッタとページネーション挙動を尊重して活用してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml で判定）を基準に行われます。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてテスト用設定を注入してください。

---

README は以上です。追加で以下を提供できます:
- requirements.txt の雛形
- Dockerfile / docker-compose による実行例
- 各モジュールの API サンプルスクリプト（バッチ/cron 用）