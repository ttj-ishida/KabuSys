KabuSys — 日本株自動売買プラットフォーム (README)
概要
- KabuSys は日本株向けのデータパイプライン、研究（ファクター計算）、ニュース NLP（LLM を使ったセンチメント算出）、市場レジーム判定、監査ログ（発注・約定のトレーサビリティ）などを含む自動売買システムのライブラリ群です。
- 主に DuckDB をデータストアに用い、J-Quants API から市場データを取得、OpenAI（gpt-4o-mini）をニュース解析やマクロセンチメント推定に利用します。
- コア設計方針として「ルックアヘッドバイアスの排除」「冪等な DB 書き込み」「堅牢なリトライ／フォールバック」を重視しています。

主な機能一覧
- ETL（data.pipeline）
  - J-Quants から株価（daily quotes）、財務（financial statements）、市場カレンダーを差分取得・保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次パイプライン run_daily_etl による一括実行と結果集約（ETLResult）
- ニュース収集（data.news_collector）
  - RSS 取得、前処理（URL 正規化・除去）、raw_news への冪等保存
  - SSRF 対策・受信サイズ制限・XML の安全パース
- ニュース NLP（ai.news_nlp）
  - 指定ウィンドウのニュースを銘柄ごとに集約し OpenAI に送信して ai_scores を生成
  - バッチ処理・リトライ・レスポンスバリデーションあり
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を算出・保存
  - API エラー時のフェイルセーフ（macro_sentiment=0.0）
- 研究ユーティリティ（research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン・IC 計算・統計サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions など監査テーブルの初期化・インデックス作成（DuckDB）
  - init_audit_schema / init_audit_db により冪等に初期化可能
- J-Quants クライアント（data.jquants_client）
  - レートリミット制御、401 自動リフレッシュ、ページネーション対応、DuckDB への冪等保存関数

前提（Prerequisites）
- Python 3.10 以上（typing の | 演算子を使用）
- DuckDB
- OpenAI SDK（openai）
- defusedxml（RSS の安全パース）
- 標準ライブラリ以外の主要依存例:
  - duckdb
  - openai
  - defusedxml

セットアップ手順
1. リポジトリをクローン
   git clone <repository-url>
   cd <repository-root>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージのインストール（開発編集可能モード）
   pip install -e ".[all]"  または最低限:
   pip install -e .
   pip install duckdb openai defusedxml

   （プロジェクトに extras_require がある場合は ".[all]" を使う想定）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env/.env.local を置くと自動読み込みされます（自動読み込みは既定で有効）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=xxxxx         # 必須: J-Quants リフレッシュトークン
- OPENAI_API_KEY=sk-xxxx               # 必須 for AI モジュール（score_news / score_regime）
- KABU_API_PASSWORD=xxxx               # 必須: kabu ステーション API パスワード
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=xoxb-xxx             # 必須（Slack 通知を使う場合）
- SLACK_CHANNEL_ID=C0123456789         # 必須（Slack 通知を使う場合）
- DUCKDB_PATH=data/kabusys.duckdb      # DuckDB DB ファイルパス（デフォルト）
- SQLITE_PATH=data/monitoring.db       # 監視用 SQLite（デフォルト）
- PID_FILE_PATH=data/execution.pid     # 実行監視用 PID ファイル
- CPU_THRESHOLD_PCT=90.0               # 監視閾値例
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development              # development | paper_trading | live
- LOG_LEVEL=INFO

使い方（簡単な例）
- DuckDB 接続と ETL 実行（日次 ETL）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア（AI）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn をアプリ用の接続として使う

- 設定参照
  from kabusys.config import settings
  print(settings.duckdb_path)

注意点 / 運用ヒント
- OpenAI の呼び出しは API エラーやレート制限に対してリトライやフォールバックを備えていますが、API キーは必ず設定してください（score_* 関数はキー未設定時に ValueError を投げます）。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード中では空チェックを行っています。直接 SQL を編集・移植する際は注意してください。
- ETL 周りは差分取得 + backfill（デフォルト 3 日）で API の後出し修正を吸収します。バッチスケジュールでの定期実行に向いています。
- ニュース収集は外部 RSS に依存します。SSRF 対策や最大受信サイズ制限を含む保護が実装されています。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースセンチメント（OpenAI 呼び出し・バリデーション）
    - regime_detector.py           # MA200 + マクロセンチメント合成によるレジーム判定
  - data/
    - __init__.py
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py            # J-Quants API クライアント、保存関数
    - news_collector.py            # RSS 収集・前処理
    - calendar_management.py       # 市場カレンダー管理・営業日判定
    - quality.py                   # データ品質チェック
    - stats.py                     # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     # 監査ログ（監査スキーマ初期化）
    - etl.py                       # ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py           # ファクター計算（momentum/value/volatility）
    - feature_exploration.py       # 将来リターン / IC / 統計サマリー
  - research/*.py (その他)

（注）上記は主要ファイルの抜粋です。実プロジェクトでは追加のモジュール（execution/monitoring/strategy 等）が含まれる想定です。

開発とテスト
- 自動 .env 読み込みはデフォルトで有効。テストや CI で環境分離する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定して無効化してください。
- AI コールや外部 API 呼び出しはユニットテストでモックすることを想定した設計（各モジュールは内部呼び出し関数を差し替え可能）。

よくある質問（FAQ）
- Q: OpenAI のキーはどの環境変数を使いますか？
  A: OPENAI_API_KEY を参照します。score_news / score_regime は引数として明示的に api_key を与えることもできます。

- Q: DuckDB の初期テーブルはどこで作成しますか？
  A: audit.init_audit_db などの初期化関数を利用して監査用テーブルを作成できます。ETL 実行前にスキーマ初期化ロジックを用意することを推奨します（プロジェクト内に schema 初期化ユーティリティがある想定）。

最後に
- 本 README はコードベースの主要機能をまとめた概要です。実際の運用では .env.example、pyproject.toml（依存定義）、および起動スクリプト（systemd / cron / CI）を整備してください。必要であれば、起動例スクリプトやより詳細な運用手順（Slack 通知・監視設定・バックアップ）も作成できます。