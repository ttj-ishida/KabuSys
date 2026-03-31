# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。ETL（J-Quants）、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

主な用途:
- J-Quants からの株価・財務・カレンダーの差分 ETL
- raw_news の収集と LLM による銘柄別センチメント算出
- ETF（1321）とマクロニュースを組み合わせた市場レジーム判定
- 研究用ファクター / 将来リターン / IC 計算
- DuckDB を用いた監査ログ（トレース可能な発注・約定履歴）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch / save: prices, financials, market calendar, listed info）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質管理
  - 欠損データ・スパイク・重複・日付不整合のチェック（quality.run_all_checks）
- ニュース収集・NLP
  - RSS 取得と前処理（news_collector.fetch_rss / preprocess_text）
  - OpenAI を使った銘柄別センチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
- リサーチユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算（research.calc_*）
  - 将来リターン・IC・統計サマリー（feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化（data.audit.init_audit_schema, init_audit_db）
- 設定 / 環境変数管理
  - .env 自動読み込み（config.py。プロジェクトルートは .git / pyproject.toml で検出）

---

## 必要条件 / 依存ライブラリ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。最低限、次のパッケージは必要です:

pip install duckdb openai defusedxml

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 開発中であれば editable install:
     ```
     pip install -e .
     ```
   - 依存パッケージを個別に:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（config.py の自動ロード。CWD に依存しない）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション接続用パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime 呼び出し時に渡すか環境変数で）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要なユースケース例）

注意: すべての関数は外部副作用（DB・API）を伴うため、本番運用前にテスト環境で動作確認してください。

- DuckDB 接続を作成して ETL を実行する（例）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメント（LLM）を実行して ai_scores に書き込む:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written {written} ai scores")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化:
  ```python
  from kabusys.config import settings
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db(settings.duckdb_path)  # ディレクトリがなければ自動作成
  ```

- 設定アクセス例:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

テスト時の注意:
- OpenAI 呼び出しはユニットテストでモック（news_nlp._call_openai_api / regime_detector._call_openai_api）することを想定して設計されています。
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 設計上の注意点 / 実運用向けメモ

- Look-ahead bias 回避: 多くの関数は datetime.today() を直接参照せず、target_date 引数で明示的に日付を指定します。バックテストの際は注意して使用してください。
- 冪等性: J-Quants / News / Audit の保存処理は冪等（ON CONFLICT）を考慮しています。
- API エラー処理: OpenAI や J-Quants 呼び出しはリトライ・フォールバック（失敗時はゼロスコア等）を実装していますが、本番では監視とアラート設定を行ってください。
- カレンダー: market_calendar がない場合は曜日ベースのフォールバックを行いますが、正確な営業日判定には必ず calendar ETL を定期実行してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys` 下を抜粋）

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
    - audit.py (監査DB初期化等)
    - etl.py (ETL エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/ (その他 research ユーティリティ)
  - ai/ (LLM 関連)
  - data/ (ETL・DB関連)

各モジュールの詳細関数（例）:
- data.pipeline: run_daily_etl, run_prices_etl, run_financials_etl, ETLResult
- data.jquants_client: fetch_daily_quotes, fetch_financial_statements, save_daily_quotes, save_financial_statements
- data.news_collector: fetch_rss, preprocess_text
- ai.news_nlp: score_news
- ai.regime_detector: score_regime
- data.audit: init_audit_db, init_audit_schema
- research: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- data.stats: zscore_normalize
- data.quality: run_all_checks, QualityIssue

---

## ライセンス / 貢献

本 README 内ではライセンス情報は省略しています。実運用／公開時は LICENSE ファイルを追加してください。バグ報告・機能追加は PR を受け付ける運用にしてください。

---

もし README に追加で欲しい情報（例: CI の設定例、具体的な SQL スキーマ定義、デプロイ手順、Dockerfile、サンプル .env.example）等があれば教えてください。必要に応じて追記・具体化します。