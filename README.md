# KabuSys

日本株向けの自動売買 / 研究 / 監視ライブラリ群。  
このリポジトリは取引実行エンジン、監視（Monitoring）機能、ポートフォリオ構築、ファクター計算、LLM によるニュースセンチメント評価などを含むモジュール群で構成されています。

概要・目的
- 本番運用 / ペーパートレード（分離された DB）両方に対応した自動売買基盤のプロトタイプ。
- DuckDB を使った時系列データ処理（ファクター計算・リサーチ）。
- SQLite による監視ログ・トレードログ永続化。
- OpenAI（gpt-4o-mini）を利用したニュース NLP（センチメント）と市場レジーム判定。
- 監視用ダッシュボード（Streamlit）・監視エンジン・アラート（LINE）機能。

主な機能
- ExecutionEngine（発注・注文管理・リコンシリエーション）
  - Broker クライアントの抽象化と Factory
  - OrderManager / OrderRepository による状態遷移・永続化
  - 起動時の自動リコンシリエーション（Reconciler）で再起動後の整合性回復
  - Paper trading モードでは MockBroker を使用し、DB を分離（data/paper_trading.db）
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / 実行プロセス / データ鮮度監視
  - TradeMonitor：滞留注文（stale order）/ 約定異常価格検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch：リスクトリガーで実行エンジンに停止フラグを書き込む（data/kill.flag）
  - AlertManager：LINE Messaging API でアラート送信（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（read-only DB 接続）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重重み計算
  - セクター制限、レジーム乗数適用
  - 株数決定（リスクベース、単元株丸め、aggregate cap）
- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value 等ファクター計算（DuckDB + SQL）
  - 将来リターン算出、IC（Information Coefficient）計算、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - raw_news を集約して OpenAI に送信 → ai_scores テーブルへ保存
  - マクロニュース + ETF(ma200) を合成して market_regime を算出
  - API 呼び出しはリトライ・バックオフ・バリデーション実装
- ツール
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ等）

セットアップ（開発用）
1. 必要な Python バージョン
   - Python 3.10 以上（| 型注釈等を利用しているため）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil requests openai streamlit
   - sqlite3 は通常 Python に同梱されています。

　（プロジェクトに requirements.txt がある場合はそれを利用してください）

環境変数（主なもの）
- KABUSYS_ENV: 起動環境（development / paper_trading / live） 既定: development
  - paper_trading の場合、発注は MockBroker を使用し DB を data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- PAPER_FILL_MODE: paper_trading のマッチ挙動（instant / partial / never / reject） 既定: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（既定: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（既定: data/execution.pid）
- KILL_FLAG_PATH: Kill flag ファイル（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） 既定: INFO
- MONITOR_POLL_INTERVAL: run_monitoring でのポーリング間隔（秒） 既定: 60
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 閾値（監視用）

（.env/.env.local をプロジェクトルートに置くことで自動的にロードされます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

使い方（代表的なコマンド）
- ExecutionEngine を起動（本番または paper_trading に応じて DB 分離）
  - python -m kabusys.run_execution
  - 実行前に環境変数 KABUSYS_ENV を設定（例: export KABUSYS_ENV=paper_trading）
  - 起動時にプロセス優先度（High）へ設定を試みます（権限に依存）

- Monitoring（単体の監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を上書き可能（秒）

- Streamlit ダッシュボード（監視 DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュールをプログラムから利用
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 引数 api_key を省くと環境変数 OPENAI_API_KEY を参照

注意事項 / 運用メモ
- paper_trading モードでは発注処理とモニタリング用 DB が本番と分離されます。paper_trading 用 DB は既定で data/paper_trading.db。
- Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用する仕様です（環境に依らず）。
- KillSwitch は data/kill.flag を用いたフラグファイル方式です。ExecutionEngine は起動時にこのフラグを確認し、KABUSYS_DISABLE_AUTO_ENV_LOAD 等の設定や KILL_FLAG_CLEAR_ON_START に基づくクリアを行う想定です。
- psutil によるプロセス優先度設定や CPU affinity の設定は OS と権限によって無視される可能性があります（警告ログが出ます）。
- OpenAI 呼び出しはネットワーク障害やレート制限に対してリトライロジックを持ちますが、API キー未設定や長期障害時は適切にフォールバック（0.0 など）する実装が入っています。
- DuckDB 側のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は運用データを投入する必要があります。リサーチ関数はこれらのテーブルを参照します。
- monitoring_db.init_monitoring_db() により監視用 SQLite の初期テーブルと簡易マイグレーションが実行されます。

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / Settings 管理)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリングループ起動スクリプト)
  - utils/
    - process_priority.py (プロセス優先度・CPU affinity ユーティリティ)
  - execution/
    - broker_api.py, broker_factory.py, ...（ブローカー抽象・実装）
    - execution_engine.py（実行エンジン本体）
    - order_manager.py（注文状態管理）
    - order_repository.py（SQLite 永続化）
    - reconciler.py（再起動時リコンシリエーション）
  - monitoring/
    - monitoring_db.py（SQLite テーブル初期化＆書込 API）
    - system_monitor.py, trade_monitor.py, risk_monitor.py（各監視コンポーネント）
    - monitoring_engine.py（複数監視の統合・ポーリング）
    - kill_switch.py, alert_manager.py
    - streamlit_dashboard.py（監視ダッシュボード）
  - portfolio/
    - portfolio_builder.py（候補選定 / 重み計算）
    - position_sizing.py（株数計算 / aggregate cap）
    - risk_adjustment.py（セクターキャップ / レジーム乗数）
  - research/
    - factor_research.py（Momentum/Volatility/Value）
    - feature_exploration.py（将来リターン / IC / 統計）
  - ai/
    - news_nlp.py（ニュースセンチメントスコア）
    - regime_detector.py（市場レジーム判定）
  - data/  (想定されるデータディレクトリ、実運用で作成)
    - kabusys.duckdb（DuckDB）
    - monitoring.db（監視 SQLite）
    - paper_trading.db（ペーパートレード SQLite）

開発・拡張ポイント（メモ）
- Broker 実装を追加すれば、複数の実ブローカーに対応可能。
- ポートフォリオ構築ロジックは純粋関数群として整理されているため、戦略チューニングが容易。
- DuckDB の schema（prices_daily / raw_financials 等）に合わせたデータ投入パイプラインが必要。
- OpenAI API の利用は API キー管理とコスト対策（バッチサイズ・トークン）を考慮すること。

トラブルシューティング
- DB ファイルが見つからない / 開けない
  - path が正しいか、ファイルが存在するか確認。Streamlit は read-only URI で接続するためパス解決に注意。
- OPENAI_API_KEY がない
  - ai モジュール呼び出し時に ValueError が発生します。環境変数を設定してください。
- psutil の権限エラー
  - プロセス優先度設定は管理者権限／sudo が必要な場合があります。失敗しても警告が出てスキップされます。

ライセンス・貢献
- 本リポジトリのライセンスや貢献フローはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上がこのコードベースの概要・セットアップ・使い方・構成です。必要であれば、README に含める具体的な .env.example、requirements.txt、起動スクリプトの systemd ユニット例、または各 DuckDB テーブルのスキーマ説明を追加で作成します。どれを追加しましょうか？