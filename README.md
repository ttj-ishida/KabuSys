# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP スコアリング（OpenAI）、リサーチ用ファクター計算、監査（オーディット）テーブルなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の要素を提供するモジュール群です。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダーを取得し DuckDB に保存）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア化（OpenAI）
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースセンチメント）
- 研究用ツール（ファクター計算・将来リターン・IC 計算・統計ユーティリティ）
- データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数 / 設定管理（.env の自動読み込み機能）

設計上の特徴:
- ルックアヘッドバイアスを避ける実装（target_date を明示、date.today() を直接参照しない箇所が多い）
- DuckDB を用いたローカルデータレイヤ
- 冪等性（ON CONFLICT / トランザクション）を考慮した保存処理
- API 呼び出しはリトライ／レート制御付きで安全に実行

---

## 主な機能一覧

- data.jquants_client: J-Quants API とのやり取り（取得・保存）、レート制限・認証リフレッシュ対応
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token
- data.pipeline: 日次 ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.news_collector: RSS 収集、安全対策（SSRF, XML bomb）を含むニュース取り込み
- ai.news_nlp: ニュースを OpenAI に投げて銘柄ごとに sentiment / ai_score を算出（score_news）
- ai.regime_detector: ETF（1321）200日 MA 乖離とマクロニュースを合成して市場レジームを判定（score_regime）
- research.factor_research: Momentum / Value / Volatility 等のファクター計算
- research.feature_exploration: 将来リターン計算、IC、統計サマリー
- data.audit: 監査ログ用テーブルの初期化（init_audit_schema / init_audit_db）
- config: .env 自動読み込み・設定プロパティ（settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型ヒントや union types を利用）
- システムに pip があること

1. リポジトリを取得（例）
   ```
   git clone <this-repo-url>
   cd <this-repo-root>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   最低限の依存（実装で使用している主要ライブラリ）:
   ```
   pip install duckdb openai defusedxml
   ```
   追加で必要となる場合があるもの:
   - linelib（LINE通知などを使う場合）
   - 他のユーティリティ（プロジェクトルートの requirements.txt があればそちらを利用）
   ```
   pip install -r requirements.txt
   ```
   あるいは開発インストール:
   ```
   pip install -e .
   ```

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、config モジュールが自動的に読み込みます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   よく使う環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - OPENAI_API_KEY=sk-...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   サンプル（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトや対話で呼び出す際の例です。DuckDB 接続は `duckdb.connect(path)` で取得してください。

1. 設定を参照する
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)
   print(settings.is_live)
   ```

2. 日次 ETL を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニューススコアリング（score_news）
   - 対象: raw_news, news_symbols, ai_scores テーブルが存在・接続されていること
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   # OPENAI_API_KEY は環境変数に設定済みであること
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")
   ```

4. 市場レジーム判定（score_regime）
   - 対象: prices_daily, raw_news, market_regime テーブルを参照/更新
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 監査ログスキーマ初期化
   ```python
   from pathlib import Path
   from kabusys.data.audit import init_audit_db

   audit_db_path = Path("data/monitoring_audit.duckdb")
   conn = init_audit_db(audit_db_path)
   # conn を使って監査テーブルへ書き込みが可能
   ```

6. 研究用ファクター計算例
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum

   conn = duckdb.connect("data/kabusys.duckdb")
   records = calc_momentum(conn, date(2026, 3, 20))
   # records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を持つ辞書のリスト
   ```

注意点:
- OpenAI を利用する機能は `OPENAI_API_KEY` が必要。引数で API キーを直接渡すこともできます。
- ETL / 保存処理は DuckDB テーブルのスキーマに依存します。スキーマ初期化は別途（スキーマ定義スクリプト）で準備してください。
- 多くの関数は target_date を明示的に受け取り、ルックアヘッドバイアスを避けるよう設計されています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants 認証用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション等の API パスワード
- KABU_API_BASE_URL: kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知関連（オプション）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite ファイルパス（data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: プロセス監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（動作モード。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動読み込みを無効化

config.Settings クラス経由でプロパティを取得できます（必要な変数が未設定だと ValueError を送出します）。

---

## ディレクトリ構成

以下は主要ファイル/モジュールの構成（抜粋）です。パッケージルートは `src/kabusys` です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL の公開インターフェース（ETLResult）
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - quality.py                 — データ品質チェック
    - news_collector.py          — RSS 収集（fetch_rss 等）
    - calendar_management.py     — マーケットカレンダー支援（is_trading_day 等）
    - audit.py                   — 監査ログ（テーブル作成・init）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum, value, volatility）
    - feature_exploration.py     — 将来リターン、IC、統計サマリー等

---

## 開発・運用上の注意

- DuckDB スキーマは本 README に含まれていないため、初期化スクリプトが必要です（テーブル作成 SQL を準備してください）。audit.init_audit_schema は監査用スキーマを初期化します。
- 外部 API（J-Quants / OpenAI）を呼ぶ処理はリトライ・レート制御・フェイルセーフを備えていますが、API キーやレート制限に注意してください。
- ニュース収集は外部 RSS に依存します。SSRF 対策や XML の安全パースを実装していますが、運用時にリストの管理を行ってください。
- 本ライブラリの関数群は主にライブラリとして呼び出す設計です。ジョブ実行（cron / systemd / Airflow 等）から Python スクリプトを呼んで使用するのが一般的です。

---

必要に応じて README の「導入手順（OS 固有の依存）」「DuckDB スキーマ初期化 SQL」「運用例（systemd / cron）」「各テーブルのスキーマ詳細」を追記できます。どの章を詳しく書いてほしいか指定してください。