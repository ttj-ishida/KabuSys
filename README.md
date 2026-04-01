# KabuSys

日本株向けのデータプラットフォーム／自動売買支援ライブラリです。  
DuckDB を利用したデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ用スキーマなどのユーティリティを提供します。

主な想定用途
- J-Quants API からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と銘柄ごとの AI センチメントスコア算出
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算・特徴量探索（研究用途）
- 約定までのトレーサビリティを担保する監査（audit）スキーマの初期化

---

## 機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動で読み込み（OS 環境変数を保護）
  - 読み込み無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー、日足（prices）、財務データを差分取得・保存
  - 各種個別 ETL ヘルパー（prices / financials / calendar）

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）、ページネーション、リトライ、レート制御
  - raw_prices / raw_financials / market_calendar への保存ユーティリティ（冪等）

- ニュース関連
  - RSS 取得・前処理・保存（news_collector）
  - OpenAI を使った銘柄別センチメントスコアリング（kabusys.ai.news_nlp）
  - マクロニュース＋ETF MA200 を合成した市場レジーム判定（kabusys.ai.regime_detector）

- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー

- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化と独立 DB 作成ユーティリティ

- 汎用統計（kabusys.data.stats）
  - Zスコア正規化など

---

## 必要条件（推奨）

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨します。

4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しに利用（score_news / score_regime の引数でも指定可）

   オプション（デフォルト値あり）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は Python から直接モジュールを呼び出す例です。

- DuckDB 接続を作る（settings から既定パスを利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores テーブルに保存する
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で渡す
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime に保存する
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

注意点
- AI 呼び出し系（score_news / score_regime）は OpenAI API キーを必要とします。関数引数で `api_key` を直接渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / API 呼び出しにはネットワークアクセスと適切な認証情報が必要です。
- データベース操作は DuckDB コネクションに対して行われます。既存スキーマが前提の関数もあるため、スキーマ準備・マイグレーションは別途行ってください（スキーマ作成ユーティリティがあるモジュールも含まれます）。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level など

- ETL / Data
  - run_daily_etl(conn, target_date=None, id_token=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar

- News / AI
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)

- Research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

- Audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- Quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

---

## 自動環境変数読み込みについて

- モジュール起動時にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索し、`.env` と `.env.local` を順に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書きします（override=True）
  - ただし既に OS にある環境変数は上書きされません（保護）
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- .env のパースはシェル風（export KEY=val のサポート、引用符・コメントの取り扱い）です。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース（src/kabusys）の主要構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント＋保存処理
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - news_collector.py      — RSS 取得・前処理・保存
    - calendar_management.py — マーケットカレンダー管理ロジック
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns / IC / summary / rank
  - execution/                — （発注周りモジュール 想定／未掲載）
  - monitoring/              — （監視用モジュール 想定／未掲載）

---

## 開発・テストのヒント

- OpenAI 呼び出しは個別の内部ラッパー関数（例: _call_openai_api）を通しているため、ユニットテスト時はこれらをモックして API コールを差し替えられます（patch 可能）。
- J-Quants API 呼び出しは内部でレートリミッタやリトライ、トークン自動更新を行います。get_id_token や _request をモックしてテスト可能です。
- DuckDB は軽量 DB のためテストで ":memory:" を使うことができます（init_audit_db も対応）。

---

## 参考・注意事項

- 本ライブラリは「外部 API を使う」「実際の発注ロジックを扱う」ため、運用前に API キー管理・権限・レート制御・テスト環境（paper_trading）での十分な検証を行ってください。
- OpenAI / J-Quants の呼び出しにはコスト・レート制限があります。大量バッチを投入する際は注意してください。
- DuckDB のバージョン差異により一部の executemany 挙動等に差が出る可能性があるため、運用環境での互換性確認を推奨します。

---

ご不明点や README に追加したい使用例（CLI サンプル、Docker 化手順、CI 設定等）があれば教えてください。必要に応じて README を拡張します。