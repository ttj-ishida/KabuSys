KabuSys — 日本株自動売買システム（README）
概要
- KabuSys は日本株向けのデータプラットフォーム / リサーチ / AI 支援の自動売買基盤コンポーネント群です。
- ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定トレース）などの機能を提供します。
- 設計方針として「ルックアヘッドバイアスの排除」「冪等性」「堅牢なリトライ・バックオフ」「DB 儲け・トレーサビリティ重視」を掲げています。

主な機能一覧
- ETL パイプライン
  - run_daily_etl: 市場カレンダー → 株価日足 → 財務データ取得と品質チェックを一括実行
  - 差分フェッチ、バックフィル、idempotent 保存
- J-Quants クライアント（data.jquants_client）
  - 株価（daily_quotes）、財務（statements）、JPX カレンダーの取得・保存
  - レート制限、トークン自動リフレッシュ、リトライ・バックオフ実装
- ニュース収集（data.news_collector）
  - RSS フィード収集、URL 正規化、SSRF 対策、トラッキング除去、raw_news への冪等保存
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のセンチメントスコア算出（ai_scores へ保存）
  - バッチ処理、レスポンス検証、リトライ・フェイルセーフ
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で bull/neutral/bear を判定
  - Look-ahead バイアス対策、API 失敗時のフォールバック
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合（未来日付・非営業日データ）検出
  - QualityIssue のリストを返し、呼び出し元で判定可能
- 研究向けユーティリティ（research）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC / 統計サマリ、Z スコア正規化
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（監査・トレーサビリティ）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - このコードベースで想定される主要依存:
     duckdb, openai, defusedxml
   例:
     pip install duckdb openai defusedxml
   ※ 実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数の設定
   - プロジェクトルートの .env（および .env.local）を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（Settings に依存）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu API パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャネル ID
     - OPENAI_API_KEY        : OpenAI API キー（ai モジュール使用時）
   - 任意 / デフォルト値
     - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
     - LOG_LEVEL   : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH : data/monitoring.db（デフォルト）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等

5. DB 初期化（監査ログなど）
   Python REPL 等で:
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)

基本的な使い方（コード例）
- DuckDB 接続を取得して日次 ETL を実行
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコア付け（OpenAI キー必要）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究（ファクター計算例）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026,3,20))

注意点・設計上の振る舞い
- Look-ahead バイアス排除:
  - 多くの関数は内部で date.today()/datetime.today() を直接参照しないよう設計されています（target_date を明示的に渡す）。
  - DB クエリは target_date 未満 / 以前などの排他条件を適切に使用します。
- 冪等性:
  - ETL 保存関数は ON CONFLICT DO UPDATE を使用して冪等に保存します。
  - news_collector は URL 正規化 → SHA256 ベースの ID により冪等性を担保します。
- フォールバック:
  - OpenAI 呼び出し失敗時や API エラー時、多くの処理は例外を投げるのではなくフェイルセーフ（0.0 スコアやスキップ）で継続する箇所があります（ログで通知）。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を順にロードします。
  - OS 環境変数は保護され、.env.local が上書き可能（override=True）ですが OS 環境変数は protected され上書きされません。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py               : パッケージ初期化（version, __all__ 等）
  - config.py                 : 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py             : ニュース NLP スコアリング（score_news）
    - regime_detector.py      : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       : J-Quants API クライアント（fetch/save_*）
    - pipeline.py             : ETL パイプライン（run_daily_etl 等）
    - etl.py                  : ETLResult 型の公開エントリ
    - calendar_management.py  : 市場カレンダー管理（is_trading_day 等）
    - stats.py                : 汎用統計ユーティリティ（zscore_normalize）
    - quality.py              : データ品質チェック（check_missing_data 等）
    - audit.py                : 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - news_collector.py       : RSS ニュース収集ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      : ファクター計算（momentum/value/volatility）
    - feature_exploration.py  : 将来リターン / IC / 統計サマリ
  - (strategy/, execution/, monitoring/ は public API として __all__ に含まれますが本リストの一部コードはここにありません)

さらに詳しい情報
- 各モジュールの docstring に設計方針、処理フロー、フェイルセーフ動作、クエリ仕様などの詳細が記載されています。開発や運用時は docstring を参照してください。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を前提にしており、厳密な JSON 出力を期待しています。API のレスポンスが期待外の場合はフェイルセーフ（スコア 0.0 やスキップ）します。

フィードバック / 貢献
- バグ報告や改善提案は Issue を立ててください。コードの追加や修正は Pull Request を送ってください。
- セキュリティ関連（API キー漏洩・SSRF 等）が疑われる問題があれば即時連絡をお願いします。

以上。お困りの点や README に追記してほしい具体的な利用シナリオがあれば教えてください。