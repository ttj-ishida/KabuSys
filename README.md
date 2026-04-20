# KabuSys — 日本株自動売買システム

概要
- KabuSys は日本株の自動売買／リサーチ基盤を目的とした小規模なプロジェクトです。
- 主な機能：発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・研究、AI を用いたニュースセンチメント／レジーム判定、ペーパートレード検証レポート等。
- 設計方針の一部：
  - 本番 DB とペーパートレード DB は分離（KABUSYS_ENV=paper_trading 時に切替）。
  - ルックアヘッドバイアス回避のため、日時参照は外部から与える設計。
  - フェイルセーフを重視し、API 失敗や部分失敗時に他データを保護する実装が多い。

機能一覧
- 実行（Execution）
  - ExecutionEngine：ブローカークライアントを介した発注フロー（本番 or Mock for paper_trading）。
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合（Reconciler）などのコンポーネントを組み合わせて運用。
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視と監視ログ永続化（SQLite）。
  - TradeMonitor / RiskMonitor：注文滞留、約定異常、ドローダウン・保有上限監視。
  - MonitoringEngine：上記モニタを定期実行し、Kill Switch 判定やアラート通知を実行。
  - kill.flag による ExecutionEngine 停止（Kill Switch）。
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）。
- 研究（research）
  - ファクター計算（momentum / volatility / value 等）、将来リターン計算、IC（情報係数）や統計サマリ。
  - DuckDB を用いた SQL + Python 実装。
- AI（ai）
  - news_nlp：OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリング（ai_scores テーブルへ書込）。
  - regime_detector：ETF（1321）の MA200 とマクロニュースの LLM スコアを組合せ市場レジーム判定（market_regime へ書込）。
- ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）。
- ユーティリティ
  - logging_setup：統一ログ設定（コンソール stdout + 日次ローテーションファイル）。
  - process_priority：プロセス優先度／CPU affinity 設定ユーティリティ。
  - config_setup / validate_config：.env 対話ウィザード / 設定検証 CLI。

動作要件（推奨）
- Python 3.10+（typing の | 演算子などを使用）
- 必須パッケージ（最低限）:
  - duckdb
  - openai
  - psutil
- 追加（任意）:
  - PyYAML（config/*.yaml の内容検証を行う場合）
- SQLite は標準ライブラリで使用

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb openai psutil
   - （任意）pip install pyyaml
   - プロジェクトに requirements.txt がある場合はそれを使用してください。
4. .env の作成（推奨：対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabu API パスワード 等を入力します。
5. 設定の検証
   - python -m kabusys.validate_config
   - 必須環境変数が未設定・不正な値がないかチェックします。--strict オプションで警告も失敗扱いにできます。
6. 初期 DB / ディレクトリ
   - デフォルトの DB・ログ・data ディレクトリは実行時に自動作成されます（例: data/, logs/）。
   - 監視 DB（data/monitoring.db）は起動スクリプトで初期化されます。

主な環境変数（概要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行制御 / 環境
  - KABUSYS_ENV — execution モード: development / paper_trading / live（default: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- データベース / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — Monitoring が使う監視 DB（Monitoring は env に関わらず本番 sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時の専用 SQLite
  - PID_FILE_PATH / KILL_FLAG_PATH — 実行関連のファイルパス（デフォルトは data/ 以下）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- その他
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — ペーパートレードの fill モード（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア、default=0。本番では 0 推奨）

使い方（主要コマンド例）
- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が利用され、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と完全分離）。
    - 停止を要求するにはプロジェクトルート `data/stop_requested.flag` を作成してください（実行中のプロセスはフラグを検知して停止します）。
    - Kill Switch により強制停止したい場合は `data/kill.flag` を作成します（KillSwitch ロジックにより書き込まれます）。
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依存せず本番 DB を参照する点に注意）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定できます。
- AI スコアリング / レジーム判定（ライブラリ API）
  - from kabusys.ai import score_news
  - from kabusys.ai.regime_detector import score_regime
  - 引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。

停止・キル関連
- グレースフル停止（各スクリプト共通）
  - run_monitoring / run_execution は data/stop_requested.flag を検知して停止します。
- Kill Switch（監視→実行エンジン停止）
  - KillSwitch はリスク条件（ドローダウン等）に応じて data/kill.flag を書き込み、ExecutionEngine 起動中にそのフラグを検出すると停止指示を送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動で消去します（本番では危険なため 0 推奨）。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成できない場合はコンソールのみ）。
- 起動スクリプトは setup_logging(app_name="execution"|"monitoring") を呼び出して統一管理します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメント処理（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視永続化層（初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度の監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - trade_monitor.py — （注文監視ロジック）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — （通知管理：LINE 等と連携する箇所）
  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - broker_factory.py — ブローカークライアント生成（Mock / 本番）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 特徴量探索・IC 等
  - data/
    - pipeline.py / stats.py 等（DuckDB / prices_daily テーブルへのアクセス）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定

運用上の注意
- 本番（KABUSYS_ENV=live）では設定値を慎重に管理してください。validate_config は本番時に有益な警告を出します。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。0 を推奨します。
- OpenAI を利用する機能は API 利用料・レート制限に注意してください。エラー時のフェイルセーフは実装済みですが、コストやレート制限に対する運用ルールを設けてください。
- DuckDB / SQLite のバックアップ、DB ファイルの権限・配置に注意してください。

開発・拡張
- モジュールは比較的単純なインターフェース（純粋関数または小さなクラス）で設計されているため、テストや差し替え（モック化）が容易です。
- news_nlp / regime_detector の OpenAI 呼び出し部分はテスト時に差し替え可能なように helper を分離してあります（ユニットテストで patch 可能）。

問い合わせ・貢献
- バグ報告・機能要望は Issues を立ててください。
- プルリクエスト歓迎。スタイルやテストを付けていただけると助かります。

以上で README になります。必要であれば以下を追加で作成できます：
- requirements.txt の提案
- systemd / supervisor / docker-compose 用の起動例
- 具体的な environment 変数テンプレート（.env.example）