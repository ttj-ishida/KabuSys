KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株向けのデータパイプライン、リサーチ、AI（ニュースNLP／市場レジーム判定）、監査（オーディット）機能、および ETL を中心としたユーティリティ群を備えたライブラリです。J-Quants や RSS、OpenAI（gpt-4o-mini）など外部サービスと連携してデータを取得・加工し、DuckDB に保存して下流のストラテジーや実行ロジックに供給します。

主な特徴
- データ取得（J-Quants API）: 日次株価（OHLCV）、財務データ、JPX カレンダー取得（ページネーション、トークン自動リフレッシュ、レート制御、リトライ）。
- ETL パイプライン: 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）を統合した日次 ETL run_daily_etl。
- ニュース収集: RSS 収集、URL 正規化、SSRF 対策、記事の前処理、raw_news への冪等保存設計（ハッシュID）。
- AI ベース解析:
  - news_nlp.score_news: 銘柄別にニュースを集約し LLM でセンチメント（ai_scores テーブルへ書き込み）。
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）判定。
- 監査ログ（audit）: シグナル→発注→約定までトレース可能なテーブル設計と初期化ユーティリティ（DuckDB）。
- リサーチツール: モメンタム / バリュー / ボラティリティ等のファクター算出、将来リターン計算、IC（スピアマン）などの統計解析ユーティリティ。
- 設定管理: .env 自動読み込み（.env/.env.local、OS 環境変数優先）と型付 Settings（環境変数の必須チェック・デフォルト値）。

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境の作成（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell)

3. 依存ライブラリのインストール（最小例）
   pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。
   ※ 他に標準ライブラリ外の依存がある場合は適宜追加してください。

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml がある場所）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（Settings で _require を使っているもの）:
   - JQUANTS_REFRESH_TOKEN  (J-Quants リフレッシュトークン)
   - KABU_API_PASSWORD      (kabuステーション API パスワード)
   - SLACK_BOT_TOKEN        (Slack 通知用 Bot トークン)
   - SLACK_CHANNEL_ID       (Slack チャンネル ID)

   推奨 / 任意:
   - OPENAI_API_KEY         (OpenAI API キー。score_news / score_regime が利用)
   - KABU_API_BASE_URL      (デフォルト http://localhost:18080/kabusapi)
   - DUCKDB_PATH            (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH            (デフォルト data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV            (development | paper_trading | live) デフォルト development
   - LOG_LEVEL              (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト INFO

   .env の例:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXX

使い方（コード例）
- DuckDB 接続を作り ETL を実行する（短縮例）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを生成（score_news）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {n_written}")

- 市場レジーム判定（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査 DB 初期化（audit）
  import duckdb
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成し、スキーマ初期化する

- J-Quants クライアントを直接使う例
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token から取得される
  records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,1,31))

注意点 / 運用上の説明
- OpenAI 呼び出しは外部 API を伴うためコストやレイテンシ、レート制限に注意してください。環境変数 OPENAI_API_KEY を設定することで score_news / score_regime が動作します。API 失敗時は安全側のフォールバック（スコア 0 等）を行う設計です。
- J-Quants API 呼び出しはレート制御とリトライを行います。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- DuckDB への書き込みは多くの箇所で冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して実装されています。
- ルックアヘッドバイアス防止のため、内部ロジックは target_date 引数を受け取り datetime.today() を直接参照しない設計です。バッチやテストでは明示的に日付を渡すことを推奨します。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py                パッケージ初期化（version 等）
  - config.py                  環境変数読み込み・Settings（.env 自動ロード、必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py              ニュースを銘柄ごとに集約して LLM でセンチメント評価、ai_scores 書込
    - regime_detector.py       ETF の MA200 とマクロニュース LLM を合成して市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py   JPX カレンダー管理、営業日判定、next/prev/get_trading_days
    - pipeline.py              ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
    - etl.py                   ETLResult の再エクスポート
    - stats.py                 zscore_normalize 等の統計ユーティリティ
    - quality.py               データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                 監査ログテーブルの DDL / 初期化ユーティリティ
    - jquants_client.py        J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
    - news_collector.py        RSS 収集 / 前処理 / SSRF 対策 / raw_news 保存ロジック
  - research/
    - __init__.py
    - factor_research.py       Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py   将来リターン計算、IC、統計サマリー
  - その他（strategy, execution, monitoring 等は __all__ に含まれるが本コード一覧では省略されています）

開発・テスト
- モジュール中には外部 API 呼び出しのラッパー関数があり、テスト時は該当関数（例: kabusys.ai.news_nlp._call_openai_api、kabusys.data.news_collector._urlopen、jquants_client._request 等）をモックすることを想定しています。
- settings は自動で .env をロードしますが、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化して環境制御ができます。

補足
- README に含まれていない細かいパラメータや仕様は各モジュールの docstring を参照してください。モジュール内に設計方針・フェイルセーフ挙動・ルックアヘッドバイアス対策が詳細に記載されています。

ご不明点・追加で記載したい内容（例: CLI、Docker、具体的なスキーマ定義、運用フロー図等）があれば教えてください。README を拡張して運用ガイドやサンプル .env.example、起動スクリプトの例も追加します。