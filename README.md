# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL、ニュースNLP、研究用ファクター計算、監査ログ（オーディット）などを含むモジュール群を提供します。

主な特徴：
- J-Quants API と連携した日次 ETL（株価 / 財務 / カレンダー）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメントスコアリング
- マーケットレジーム判定（ETF + マクロニュースの LLM スコアを合成）
- 研究用ファクター（モメンタム、ボラティリティ、バリュー）、特徴量解析ユーティリティ
- DuckDB を用いたローカルデータ管理と監査テーブルの初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）モジュール

---

## 機能一覧（概要）

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数群、トークン自動リフレッシュ、レート制御）
  - ニュース収集（RSS → raw_news、SSRF / Gzip / トラッキング除去対策）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースのセンチメントスコアリング（score_news）
  - マーケットレジーム判定（score_regime）
  - OpenAI API 呼び出しに対するリトライ・フェイルセーフ設計
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）

---

## 前提条件 / 依存関係

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ

（実プロジェクトでは pyproject.toml / requirements.txt に依存指定があります。ここでは主要なものを列挙しています。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成と有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール
   - 開発中に editable install:
     ```
     pip install -e .
     ```
   - あるいは最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（説明）:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の既定）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 設定環境（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要 API の例）

※ ここに示すコードはライブラリ内関数を直接呼び出す例です。プロダクションではジョブスケジューラ / ワーカーから呼び出してください。

- DuckDB 接続を取得して日次 ETL を実行する
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を引数に指定することも可能
  print(result.to_dict())
  ```

- ニューススコア（対象日は date オブジェクト）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- マーケットレジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI key は環境変数から取得
  ```

- 監査ログ DB 初期化（監査用 DuckDB を新規作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / executions 等へアクセス可能
  ```

- カレンダー / 営業日判定ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API 料金・レートに注意してください。ネットワークエラーや API エラー発生時はフェイルセーフ（スコア 0.0 等）で継続する設計です。
- J-Quants API とのやり取りにはレート制御とリトライが実装されています。JQUANTS_REFRESH_TOKEN は必須です。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数 / .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py    -- 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（fetch / save）
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - etl.py                -- ETLResult 再エクスポート
    - news_collector.py     -- RSS 収集・前処理
    - calendar_management.py-- マーケットカレンダー管理
    - quality.py            -- データ品質チェック
    - stats.py              -- 統計ユーティリティ（zscore_normalize）
    - audit.py              -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py-- 将来リターン / IC / 統計サマリー

---

## 設計上の留意点（運用時のヒント）

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストなどで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは複数個所で行われます。テスト時は内部の _call_openai_api をモックする設計になっています。
- J-Quants API はページネーション・トークン・トークンリフレッシュに対応しています。id_token は内部キャッシュされます。
- DuckDB の executemany は空リストを受け付けないバージョンの制約に対応してコード側でチェックしています。
- 監査ログは削除せず蓄積する前提で設計されており、order_request_id が冪等キーとして使われます。

---

## トラブルシューティング

- 環境変数が見つからない場合: config.Settings のプロパティが ValueError を投げます。`.env.example` を参考に `.env` を作成してください。
- OpenAI 呼び出しでエラーが多発する場合: API キー・使用可能クレジット・モデル指定（gpt-4o-mini 等）を確認してください。score_news / score_regime は内部でリトライ・フォールバックを実装しています。
- J-Quants 401 エラー: refresh token に問題がある可能性があります。JQUANTS_REFRESH_TOKEN を確認してください。
- RSS 取得でパースエラーが出る場合: 対象フィードの形式やサイズ（MAX_RESPONSE_BYTES）を確認してください。SSRF 対策で private host へのアクセスは拒否されます。

---

必要があれば、README に実行例のワークフロー（cron / airflow / GitHub Actions での ETL スケジューリング例）や詳細な .env.example のテンプレートを追記します。どの部分を詳しく追記したいか教えてください。