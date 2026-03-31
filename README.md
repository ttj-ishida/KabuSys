# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。データETL、ニュースNLP、AIベースの市場レジーム判定、ファクター研究、監査ログなどのユーティリティを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を提供する Python モジュール群です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB 保存、品質チェック付き）
- RSS ベースのニュース収集と前処理（SSRF/サイズ制限等の安全対策あり）
- OpenAI を用いたニュースセンチメント分析（銘柄別 ai_score）およびマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化等）
- 取引監査ログ（signal → order_request → execution トレースのためのスキーマ定義・初期化）
- 各種設定管理（.env 自動読み込み、必須環境変数チェック）

設計上の特徴:
- ルックアヘッドバイアス低減（内部で date.today() を直接参照しない等）
- DuckDB を中心としたローカル DB ワークフロー
- API 呼び出しに対するリトライ/バックオフ、フェイルセーフ動作
- 冪等性を考慮した DB 保存（ON CONFLICT / DELETE → INSERT パターン）

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（rate limiter、トークン自動リフレッシュ、ページネーション対応）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss、前処理、安全対策（SSRF、gzip 制御、トラッキング除去）
  - データ品質チェック: missing_data / spike / duplicates / date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュース NLP（銘柄別センチメント）: score_news
  - 市場レジーム判定: score_regime（ETF 1321 の MA200 とマクロ記事センチメントを合成）
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数 / .env 自動読み込み（.env, .env.local）、必須チェック（Settings クラス）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows (PowerShell 等)
   ```

3. 依存パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - openai
     - defusedxml
   - 仮に requirements.txt を用意しているなら:
     ```bash
     pip install -r requirements.txt
     ```
   - 開発中に編集するならパッケージを editable インストール:
     ```bash
     pip install -e .
     ```

4. 環境変数 / .env を準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

   必須環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY（AI モジュールを使う場合）

   設定例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下は主要ユースケースの簡単な使用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作る（デフォルト path は Settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（株価・財務・カレンダー取得＋品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date を指定すればその日分を処理
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  wrote = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数に設定
  print("書き込んだ銘柄数:", wrote)
  ```

- 市場レジーム判定を実行（1321 の MA200 とマクロ記事で判定）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて audit_conn を監査ログ用に使う
  ```

- RSS フィードを取得する（ニュース収集の単体利用）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- 研究用：モメンタムやボラティリティを取得
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

注意:
- AI モジュールは OpenAI の API を呼び出します。API キーの設定と利用料に注意してください。
- J-Quants API 利用にはリフレッシュトークンが必要です。Settings が管理します。
- ETL・保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が前提です。必要なテーブル定義は ETL / save_* 関数の使用前に準備してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

設定は .env / .env.local に記述できます。プロジェクトルートは .git または pyproject.toml を基準に探索します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント（銘柄別）
    - regime_detector.py     -- マーケットレジーム判定（1321 + マクロ記事）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- マーケットカレンダー管理
    - news_collector.py      -- RSS 収集・前処理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（z-score 等）
    - audit.py               -- 監査ログスキーマ定義・初期化
    - etl.py                 -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ 以下にはそれぞれのユーティリティとアルゴリズム実装が含まれます。

---

## 注意事項 / 運用上のヒント

- API 呼び出しや DB 書き込みは副作用があるため、実行前に .env の設定と DB のバックアップを推奨します。
- OpenAI/API 呼び出しの失敗はフェイルセーフとして 0.0 やスキップで継続する設計ですが、結果の解釈には注意してください。
- ETL の品質チェック（quality.run_all_checks）結果は ETLResult に格納されます。重大なエラーがあれば適宜アラートや手動確認のフローを用意してください。
- DuckDB バージョン差異により executemany の振る舞いが異なる場合があるので、運用環境での動作確認を行ってください。

---

もし README に追加したい実行スクリプト例、CI ワークフロー、より詳細なテーブルスキーマやサンプル .env.example を含めたい場合はその旨を教えてください。