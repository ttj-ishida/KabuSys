# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買パイプライン群を提供する Python パッケージです。J-Quants API からのデータ取得（株価 / 財務 / カレンダー）、DuckDB ベースの ETL、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注→約定のトレース）などを含みます。

主な設計方針：
- ルックアヘッドバイアス対策（内部で datetime.today() を安易に参照しない）
- DuckDB を中心としたローカルデータ管理（ETL は冪等・差分更新）
- 外部 API 呼び出しはリトライ／バックオフ・レートリミッティングを備える
- モジュール単位でテスト差し替え（_call_openai_api 等をモック可能）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save /認証の自動リフレッシュ、レート制御、リトライ）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF や XML の安全対策、URL 正規化）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのセンチメントを OpenAI で評価して ai_scores に格納）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime に記録）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理（kabusys.config.Settings）
  - .env 自動読み込み（プロジェクトルートを .git や pyproject.toml から検出）
  - 必要な環境変数の定義とバリデーション

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   必須例（プロジェクトに requirements.txt があればそれを使用してください）。本コードベースで明示的に使われているパッケージ例：
   - duckdb
   - openai
   - defusedxml
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定（.env を推奨）
   プロジェクトルート（.git または pyproject.toml のある階層）に `.env` と `.env.local` を置くと自動で読み込まれます（読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   OPENAI_API_KEY=sk-...
   KABUYS_ENV=development          # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_FILL_MODE=instant        # paper trading のモック埋め合わせ
   ```

   注意:
   - J-Quants の認証には JQUANTS_REFRESH_TOKEN が必要です（get_id_token がそれを使って idToken を取得します）。
   - AI 機能を使う場合は OPENAI_API_KEY を設定してください。関数に直接 api_key を渡すことも可能です。

5. データディレクトリ（必要なら）を作成
   ```bash
   mkdir -p data
   ```

---

## 使い方（短いコード例）

以下はパッケージを Python から使う際の代表的な例です。すべて duckdb 接続を渡して操作します。

- DuckDB 接続を作る（デフォルトファイル: settings.duckdb_path）
  ```python
  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # デフォルト data/kabusys.duckdb
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai.score_news）を実行する
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されているか、api_key を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- 市場レジーム判定（ai.score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化（監査用 DuckDB を分離する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 監視・設定の読み方
  ```python
  from kabusys.config import settings
  print(settings.kabu_api_base_url)
  print(settings.is_paper)
  ```

注意点：
- AI 呼び出しや外部 API 呼び出しは課金やレート制限の対象となるため、本番稼働前に設定を確認してください。
- ETL 系は冪等性を考慮して実装されていますが、スキーマが揃っていることを前提に動作します（必要なテーブルがない場合はエラーや空挙動となることがあります）。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: paper trading のフィルモード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用フラグ
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

.env の自動読み込み：
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` → `.env.local` の順で読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイル・モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult 再エクスポート
    - calendar_management.py        -- 市場カレンダー管理
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - quality.py                    -- データ品質チェック
    - news_collector.py             -- RSS ニュース収集（SSRF 対策等）
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py        -- 将来リターン / IC / summary / ranking

---

## 運用上の注意 / ヒント

- OpenAI API を使用する機能（news_nlp, regime_detector）は API キーの管理とコストに注意してください。API 呼び出しは JSON モードで行い、レスポンスのバリデーション・リトライを実施しますが、外部サービス依存部分はフェイルセーフにより 0 や空で継続する実装です。
- J-Quants API はレート制限が厳しく（120 req/min）RateLimiter と指数バックオフを内蔵しています。大量取得時は ETL の実行頻度を調整してください。
- DB スキーマ初期化（監査ログなど）は init_audit_schema / init_audit_db を利用してください。監査テーブルは UTC タイムスタンプを前提とします。
- コード内で外部 API 呼び出しや時間に関わる処理は、テスト時に差し替え可能（関数ごとにモックしやすい設計）です。

---

必要であれば README に
- インストール用 requirements.txt の例
- より細かい API 使用例（SQL スキーマ説明やテーブル名一覧）
- デバッグ / ログ設定方法
などの追記を行えます。どの情報を優先して追加しますか？