README.md

概要
- KabuSys は日本株の自動売買・研究・監視を支援する Python パッケージです。
- 本リポジトリには、ExecutionEngine（発注エンジン）、Monitoring（稼働監視 / リスク監視 / Kill Switch）、ポートフォリオ構築、ファクター/リサーチ、AI ベースのニュース NLP（OpenAI 経由）、および各種ユーティリティ／ツールが含まれます。
- 設計方針として、実行系と研究系を分離し、DB（SQLite / DuckDB）と環境変数による設定管理、ログの統一的運用、フェイルセーフ（API失敗時のフォールバック、部分書き込み保護）を重視しています。

主な機能一覧
- Execution
  - 実際のブローカー（kabuステーション）またはペーパートレード用 MockBroker を使った ExecutionEngine（発注・注文管理・リスク管理・Reconciler 等の起動スクリプトを含む）
  - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB に完全分離して記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス死活、データ鮮度の監視・ログ化
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン／ポジション上限の検出
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - MonitoringEngine: 各モニタを束ねてポーリング実行、アラート発行連携
- Portfolio construction
  - 候補選定、等配分・スコア加重、リスク補正（セクター上限・レジーム乗数）、株数決定（単元丸め、aggregate cap、コストバッファ）
- Research
  - ファクター計算（モメンタム・バリュー・ボラティリティなど）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ
- AI（OpenAI 経由）
  - news_nlp: ニュース記事を集約し LLM でセンチメントを算出して ai_scores に保存
  - regime_detector: ETF MA とマクロセンチメントを組み合わせて市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成
- ユーティリティ
  - 環境設定ウィザード（config_setup）、設定検証 CLI（validate_config）
  - ロギング設定ユーティリティ（logs/<app>.log に日次ローテート）
  - プロセス優先度 / CPU affinity セットアップ

セットアップ手順（ローカル開発向け）
1. Python（推奨: 3.10+）をインストール
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイルの検証を行う場合に必要: pip install PyYAML
   - （requirements.txt がある場合はそれに従ってください）
4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - これによりプロジェクトルートに .env が作成・更新されます
   - 自動読み込みはデフォルトで有効。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります
6. データディレクトリ / ログディレクトリ
   - デフォルト DB・ログパス:
     - DuckDB: data/kabusys.duckdb  (環境変数 DUCKDB_PATH で変更可)
     - Monitoring SQLite: data/monitoring.db  (環境変数 SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db  (PAPER_TRADING_SQLITE_PATH)
     - ログ: logs/<app>.log （LOG_DIR 環境変数で変更可）
   - 必要に応じて data/ や logs/ を作成（多くのコードは自動作成を試みます）

重要な環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行制御 / ファイルパス
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視／停止関連）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- 監視間隔（モニタ専用）
  - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- ペーパートレード挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

使い方（主要スクリプト / CLI）
- 環境作成・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
- Monitoring を起動（常駐プロセスとして）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: data/stop_requested.flag を作成するとループが終了（監視スクリプト内部の停止フラグ）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を利用し data/paper_trading.db に記録
  - 実行中に停止したい場合は data/stop_requested.flag を作成して待機ループにより停止
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db で DB パスを指定
- AI 関連
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して利用
  - 必須: OPENAI_API_KEY（ない場合は ValueError）

ログと運用
- logging_setup.setup_logging により stdout と 日次ローテートされたファイル（logs/<app>.log）へ出力
- ログ回転は 30 日保持
- プロセス優先度（set_process_priority）を起動直後に high に設定する挙動が既定の起動スクリプトで行われます（権限により設定できない場合は警告が出ます）

停止・Kill Switch の利用
- KillSwitch はリスク条件（ドローダウン・ポジション上限）に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨
- 手動で強制停止したい場合:
  - data/kill.flag を作成すると ExecutionEngine が停止するように設計されています（監視側と Execution 側で連携）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード集計・検証ツール
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマ・永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor の統合ループ
    - (trade_monitor, alert_manager などが存在)
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数決定ロジック等
    - risk_adjustment.py     — セクター上限・レジーム乗数等
  - research/
    - factor_research.py     — 各種ファクター計算（DuckDB 利用）
    - feature_exploration.py — 将来リターン / IC /統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 経由）
    - regime_detector.py     — マクロ + MA によるレジーム判定
  - execution/               — Execution 関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - data/ (実行時生成)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル

注意事項・運用上のポイント
- 本番環境（KABUSYS_ENV=live）では KEY・パスワード等の管理に細心の注意を払ってください。validate_config は live モードで追加警告を出します。
- OpenAI の呼び出しは外部 API に依存するため、API 失敗時はフォールバック（0.0 等）が入る設計だがログや監視を必ず設定してください。
- データベースのパスや挙動は環境変数で容易に切り替えられます（ペーパートレードは本番 DB と分離）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。

貢献・開発
- 新しい設定項目や依存ライブラリを追加する場合は config_setup と validate_config を更新して対話式/検証に反映してください。
- ローカルでの単体テストや CI は DB ファイルを一時パスにして実行してください（自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が便利です）。

以上。README の改善点や追加したい使用例があれば教えてください。