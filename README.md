KabuSys — 日本株自動売買システム
======================

このリポジトリは日本株の自動売買／研究／監視を目的とした軽量フレームワークです。  
コードは主に以下の役割を持つモジュール群で構成されています：注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（DuckDB を用いたファクター計算）、および AI を使ったニュース評価。

要点
- Python パッケージとして提供（src/kabusys 以下）
- 設定は .env（または環境変数）で管理。config_setup.py による対話式ウィザードあり
- 本番／ペーパートレードは KABUSYS_ENV により切替可能（development / paper_trading / live）
- 監視は SQLite（monitoring.db）にログを保存、分析用に DuckDB を利用
- OpenAI を使った NLP（ニューススコアリング / レジーム判定）機能あり（OPENAI_API_KEY 必須）

機能一覧
- ExecutionEngine 起動（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper trading 時は MockBroker を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - 起動時にプロセス優先度を上げる
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム状態（CPU / メモリ / ディスク）・データ鮮度監視
  - 取引ログ、リスクログ、ダッシュボード集計の永続化（SQLite）
  - Kill Switch（閾値超過で kill.flag を書き込み Execution を停止させる）
  - Alerts（AlertManager 経由で通知、LINE 等）
- Portfolio（portfolio パッケージ）
  - 候補選定、重み計算（等分/スコア加重）、セクター制限、ポジションサイズ計算
- Research（research パッケージ）
  - DuckDB によるファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成した市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計し検証レポートを出力
- 設定関連ユーティリティ
  - config_setup.py: .env の対話的作成
  - validate_config.py: 起動前の設定検証（YAML パースチェックは PyYAML が必要）

セットアップ手順（開発用）
1. Python 環境
   - 推奨: Python 3.10 以上（typing の | 演算子などを使用）
2. 仮想環境（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
4. 環境変数 / .env の用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使うなら:
     - OPENAI_API_KEY
   - 主な設定（デフォルトを記載）:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - PAPER_FILL_MODE=instant|partial|never|reject
   - 自動 .env ロード:
     - パッケージ読み込み時にプロジェクトルート（.git or pyproject.toml）から .env / .env.local を自動ロードします
     - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
- 実行（モジュールとして）
  - ExecutionEngine 起動（デフォルト: KABUSYS_ENV による挙動）
    - python -m kabusys.run_execution
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine のプロセスにシグナルを送る
  - Monitoring 起動（ポーリング）
    - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能（デフォルト 60 秒）
    - python -m kabusys.run_monitoring
  - 設定ウィザード
    - python -m kabusys.config_setup
  - 設定検証
    - python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ログ
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
  - LOG_DIR 環境変数で変更可能
  - setup_logging で出力先を統一（stdout + 日次ファイル）
- 停止制御 / Kill Switch
  - 外部から ExecutionEngine を即時停止したい場合:
    - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine 側の挙動により停止されます（設定による）
  - 手動停止フラグ（監視 / 実行スクリプトが監視するフラグ）:
    - data/stop_requested.flag を作成すると run_monitoring/run_execution はループを抜けて終了します
  - ExecutionEngine の PID は data/execution.pid（デフォルト）に書かれます

重要な環境変数（サマリ）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作切替 / パス
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト data/paper_trading.db)
  - PID_FILE_PATH (実行 PID ファイル、デフォルト data/execution.pid)
  - KILL_FLAG_PATH (kill.flag のパス、デフォルト data/kill.flag)
- ロギング / 動作
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
- AI
  - OPENAI_API_KEY（news_nlp / regime_detector を利用する場合）
- その他
  - PAPER_FILL_MODE (paper_trading 時の擬似約定モード: instant|partial|never|reject)

データファイル / フラグ（デフォルト）
- data/kabusys.duckdb  — DuckDB（分析）
- data/monitoring.db    — 監視用 SQLite
- data/paper_trading.db — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時）
- data/execution.pid    — 実行エンジンの PID（デフォルトパス）
- data/kill.flag        — Kill Switch が書き込む停止フラグ
- data/stop_requested.flag — 管理者がプロセス停止をリクエストするためのフラグ（run_*.py が監視）

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - monitoring/ (DB / logs 関連)
  - tools/
    - paper_verification_report.py

運用上の注意
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にしておくことを推奨（誤って Kill Flag をクリアしないため）。
- .env は絶対にバージョン管理に含めないこと（機密情報を含む）。
- OpenAI 等の外部 API を使用する機能は API キー、課金、レートリミットおよびプライバシーに注意して運用してください。
- DuckDB / SQLite ファイルは起動ユーザーが書き込み可能な場所に配置してください。
- プロセス優先度の設定には権限が必要な場合があり、失敗してもプロセスは継続します（警告ログのみ）。

よくあるコマンド例
- ウィザードで .env を作る:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視をデフォルトで起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジンを起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポートを出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
- この README にはライセンス情報を含めていません。リポジトリで定義された LICENSE を参照してください。
- バグ修正や機能改善は Pull Request を歓迎します。大きな設計変更は事前に Issue で相談してください。

附記
- ドキュメント中のデフォルトパスや閾値はコード中にコメントで説明があります。実運用時は config/*.yaml（必要に応じて）や環境変数でチューニングしてください。