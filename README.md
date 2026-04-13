KabuSys
======

日本株向けの自動売買システムのモジュール群です。バックエンドの発注・監視・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント／レジーム判定）などを含むライブラリ兼実行用スクリプト群として実装されています。

主な設計方針
- core ロジックは可能な限り純粋関数または DB 分離で実装（テスト容易性を確保）
- 本番データと Paper Trading は明確に分離（環境変数 KABUSYS_ENV により切替）
- DuckDB を使ったリサーチ／ファクター計算、SQLite を使った監視ログ保存
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロセンチメントはオプション（API キー必須）
- 自動的な .env ロード機能を持つ（プロジェクトルートの .env / .env.local）

機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象（BrokerClientFactory）により本番 or モックの切替
  - OrderManager / Reconciler による発注・再同期・ポジション整合
  - RiskManager による発注前リスクチェック
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン
  - SQLite に監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を永続化
  - AlertManager による LINE プッシュ通知（任意）
  - KillSwitch による外部停止フラグ（data/kill.flag）生成
  - Streamlit ベースの簡易ダッシュボード
- Portfolio construction
  - 候補選定・重み付け（等分・スコア加重）
  - セクター上限適用、レジーム乗数計算
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース記事を集約して OpenAI でセンチメントを算出し ai_scores に書き込む（news_nlp）
  - マクロニュース + ETF MA200 を用いた日次レジーム判定（regime_detector）
- Tools
  - Paper Trading 検証レポート出力ツール（tools/paper_verification_report.py）

セットアップ手順（開発環境）
- 前提
  - Python 3.9+ を推奨（コードは型ヒント等を使用）
  - SQLite（組み込み）および DuckDB を利用
- 依存パッケージのインストール（例）
  - pip install duckdb psutil openai requests streamlit
  - 実際は requirements.txt を用意している場合はそれを使ってください（本コードベースには含まれていません）。
- プロジェクトルートに .env を作成（.env.example を参照）
  - 自動ロードはデフォルトで有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 主な環境変数（代表例）
  - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合必須）
  - KABUSYS_ENV: execution の実行環境（development / paper_trading / live） デフォルト: development
    - paper_trading の場合は MockBrokerClient を使い data/paper_trading.db（デフォルト）へ記録
  - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject） デフォルト: instant
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視ログ用 SQLite パス（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で上書き可能、デフォルト: 60）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

データベース・初期化
- 監視関連テーブルは init_monitoring_db() で作成・簡単なマイグレーションが実行されます。
  - 実行スクリプト（run_monitoring / run_execution）は起動時にこの初期化を行います。

使い方（主なコマンド）
- 監視ループを起動（Production 向け監視プロセス）
  - KABUSYS_ENV に関係なく monitoring は本番 sqlite_path を使います。
  - 実行例:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ExecutionEngine を起動（発注プロセス）
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading 用の MockBrokerClient を用い、別 DB（data/paper_trading.db）へ記録されます。
  - 実行例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading 検証レポート（コマンドラインツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- AI / リサーチ機能の呼び出し（プログラムから）
  - news_nlp.score_news(conn, target_date, api_key=...)：DuckDB 接続を渡してニューススコアを書き込む
  - regime_detector.score_regime(conn, target_date, api_key=...)：日次レジーム判定を実行
  - research の関数群（calc_momentum 等）は DuckDB 接続を渡して利用

注意点・運用上のメモ
- OpenAI を利用する機能は API キーが必須。API 呼び出しで失敗した場合はフェイルセーフ（スコア0やスキップ）する設計ですが、キー自体は必ず設定してください。
- run_monitoring / run_execution 起動時にプロセス優先度を "high" に変更する処理が入っています（psutil に依存）。権限不足時は警告を出してスキップします。
- Paper Trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。誤って本番 DB を上書きしないよう運用上の取り扱いに注意してください。
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から .env, .env.local を自動で読み込みます。
  - OS 環境変数は保護され、.env.local は上書き（override=True）で読み込まれます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定の読み込みロジック
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (本コード断片では省略されている箇所あり)
    - broker_factory.py
    - broker_api.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/（運用時に生成されることを想定）
    - kabusys.duckdb (default DUCKDB_PATH)
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (paper trading 用)

開発者向けメモ
- 多くのモジュールは外部接続（DB / ブローカー / OpenAI クライアント）を引数で受け取るため、単体テストが書きやすくなっています。OpenAI／外部 API 呼び出しはテスト時に patch して差し替えられるよう設計されています（例: _call_openai_api の差し替え）。
- DB スキーマのマイグレーションは簡易的に INIT 時にカラム追加を行う実装になっています（init_monitoring_db）。

ライセンス / 貢献
- 本リポジトリにライセンスファイルが含まれている場合はそれに従ってください。開発改善やバグ修正は Pull Request を歓迎します。

以上。導入や実行で不明点があれば、利用する環境（OS、Python バージョン、使用する機能／スクリプト）を教えてください。具体的な起動コマンドや .env のテンプレート例を提供します。