# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。J-Quants / JPX 等の外部データを収集・ETL し、データ品質チェック、ニュース NLP（LLM を用いたセンチメント評価）、マーケットレジーム判定、ファクター計算、監査ログ（発注/約定トレース）等の機能を提供します。

主な用途:
- 日次 ETL（株価・財務・マーケットカレンダー）の自動収集・保存
- ニュース記事の収集と銘柄単位センチメントスコア生成（OpenAI）
- マーケットレジーム判定（MA200 と マクロニュースの合成）
- 研究用ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- データ品質チェックと監査ログ（order_requests / executions 等）の管理

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証・リトライ・レート制御）
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - データ品質チェック（欠損、スパイク、重複、未来日付等）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとセンチメントを ai_scores に書き込み）
  - マーケット・レジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースの合成）
  - OpenAI 呼び出しは gpt-4o-mini を利用（JSON モード）、リトライ・フォールバック実装
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC 計算・統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み（.env / .env.local の自動読み込み / KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
  - settings オブジェクト経由で設定値にアクセス

---

## セットアップ手順

1. リポジトリをクローンして開発環境を作成します（例）:
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストールします。主要な依存例:
   - duckdb
   - openai（OpenAI Python SDK）
   - defusedxml
   - typing-extensions（必要に応じて）
   インストール例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 環境変数を設定します。プロジェクトルートの `.env` / `.env.local` を使えます。自動ロードは config モジュールがプロジェクトルート（.git または pyproject.toml）を検出して行います。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる代表的な環境変数（README 用抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必要な場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定（必要に応じて）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
   - SQLITE_PATH: SQLite（監視用など）パス（デフォルト "data/monitoring.db"）
   - KABUSYS_ENV: environment（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   .env の例（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB データベースの初期化（必要に応じて）:
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 一般的なワーク用接続:
     ```python
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（簡単な例）

以下は代表的な機能の呼び出し例です。すべて Python スクリプト内で実行します。

- settings を使う（環境変数の参照）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア（ai_score）を生成する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"Scored {count} codes")
  ```

- マーケット・レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（上でも紹介）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意点:
- AI（OpenAI）呼び出しには OPENAI_API_KEY が必要です。API エラー時はフォールバック（0.0）して継続する設計です。
- 全ての日時処理はルックアヘッドバイアス対策が施されています（target_date を明示し、date.today() を不必要に参照しない等）。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実行されます。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールと代表ファイルの一覧です（src/kabusys 配下）:

- kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（公開関数など）
  - ai/（ニュースNLP・レジーム判定）
  - その他: strategy, execution, monitoring（パッケージ公開インターフェースに含まれる可能性あり）

各ファイルの責務（要約）:
- config.py: .env 自動読み込み・環境変数管理（settings オブジェクト）
- data/jquants_client.py: J-Quants API の取得・保存ロジック（レート制御・リトライ・保存）
- data/pipeline.py: 日次 ETL のオーケストレーション
- data/news_collector.py: RSS フィード取得・前処理・raw_news への保存
- ai/news_nlp.py: 銘柄毎ニュースの集約 → OpenAI によるスコア化 → ai_scores へ保存
- ai/regime_detector.py: MA200 とマクロニュースから市場レジームを判定して market_regime へ保存
- research/*: ファクター計算・特徴量解析・IC・統計サマリー
- data/quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data/audit.py: 監査ログ用テーブルの初期化と DB 作成ユーティリティ

---

## 運用上の留意点

- 環境（KABUSYS_ENV）を適切に設定してください（development / paper_trading / live）。live 時の操作は慎重に。
- OpenAI API 呼び出しにはコストとレート制限があります。batch サイズや呼び出し頻度を運用ポリシーに合わせて調整してください。
- J-Quants API は 120 req/min のレート制限が設定されています。本クライアントは固定間隔スロットリングで対応していますが、運用実行時は注意してください。
- DuckDB の executemany に関する制約（空リスト不可など）に留意しています。スキーマ変更時は既存処理の影響確認を行ってください。
- NewsCollector は SSRF 対策（リダイレクト検査 / プライベートアドレス拒否）や受信サイズ上限を実装していますが、外部フィードを扱う際はソースの信頼性確認を行ってください。

---

## 補足

- 自動環境読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動で読み込みます。
  - 自動読み込みを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- logging: settings.log_level で制御されます。開発時は DEBUG にすると詳細ログを確認できます。
- テスト・モック: OpenAI や HTTP 呼出し部分はテストしやすいように内部呼び出し関数を差し替え可能（unittest.mock.patch を想定）です。

---

必要であれば README に以下を追記します:
- requirements.txt / pyproject.toml の例
- .env.example（推奨される全環境変数一覧）
- よくあるトラブルシューティング（OpenAI エラー・DuckDB パス権限等）
- CI / デプロイ手順（cron / systemd / Docker 等）

どの情報を追記しますか？