# KabuSys

日本株向け自動売買システムのリファレンス実装 (小〜中規模)。  
本リポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築・リスク管理、リサーチ／ファクター計算、LLM を用いたニュース NLP などを含むモジュール群で構成されています。

注意：本 README はソースコードの説明と運用上の基本的な使い方をまとめたものです。実運用で使う場合は config の内容や本番環境用のガード（LINE 通知、Kill Switch 設定等）を必ず確認してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・停止・主要スクリプト）
- 環境変数・設定
- ディレクトリ構成
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株向けの自動売買プラットフォームの参考実装です。
- コンポーネントは分離されており、監視（Monitoring）・発注実行（Execution）・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）などで構成されています。
- SQLite（監視用 / ペーパートレード用）と DuckDB（分析用）をデータ保存に利用します。
- ペーパートレード（分離された DB と MockBroker）をサポートし、本番（live）環境とのデータ分離が可能です。

主な機能一覧
- Execution（発注エンジン）
  - 実口座 / ペーパートレードの切り替え
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / Reconciler / RiskManager による発注管理と整合性チェック
- Monitoring（監視）
  - システムリソース（CPU/MEM/DISK）および Execution プロセスの生存監視
  - 注文ログ・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（条件に応じた停止フラグ書き込み）
  - アラートの集約（AlertManager 経由）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け（等金額 / スコア加重）、ポジションサイズ計算（単元丸め、上限、集約キャップ）
  - セクター集中制限、レジームに応じた乗数
- Research（リサーチ / ファクター）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI（LLM を用いた処理）
  - ニュースを LLM でセンチメント付与（ai_scores へ書き込み）
  - マクロニュース + ETF MA を合成した市場レジーム判定
  - OpenAI API（gpt-4o-mini）を利用（API キー必須）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- 設定管理
  - .env 生成ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）

セットアップ手順（ローカル開発想定）
1. リポジトリをクローン
   - git clone <repo_url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必要なライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml のパース検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （パッケージ管理ファイルがあればそれに従ってください）
4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成（.env は絶対に Git にコミットしないでください）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- データベース
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (monitoring 用, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用, default: data/paper_trading.db)
- ログ
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (default: logs/)
- OpenAI
  - OPENAI_API_KEY (AI モジュール利用時必須)
- モニタリング
  - MONITOR_POLL_INTERVAL（秒、run_monitoring のポーリング間隔を上書き、デフォルト 60）
- Paper Trading 固有
  - PAPER_FILL_MODE (instant | partial | never | reject) — MockBroker の約定挙動

使い方（起動 / ユーティリティ）
- 実行スクリプト（モジュール実行）
  - ExecutionEngine を起動（環境に応じてペーパー／本番が切替）
    - python -m kabusys.run_execution
    - 実行時、KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録します。
  - Monitoring を起動（ポーリングで各モニタを実行）
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能
    - 監視は本番 sqlite_path を常に使用（環境にかかわらず）
  - 設定ウィザード
    - python -m kabusys.config_setup
  - 設定検証
    - python -m kabusys.validate_config
  - Paper Trading 検証レポート
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を指定する場合:
      - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

起動・停止に関する仕組み
- PID / フラグファイル
  - 実行エンジンは pid_file（デフォルト data/execution.pid）を使用
  - 停止フラグ:
    - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します
    - Kill Switch は data/kill.flag を書き込み、ExecutionEngine に「停止」信号を与える仕組み（Settings.kill_flag_path で経路変更可能）
  - KillSwitch は RiskMonitor 等から条件を満たすと kill.flag を書き込みます（冪等、不必要な再書き込みは行いません）

AI モジュール利用時の注意
- OPENAI_API_KEY を設定する必要があります（score_news / score_regime 等）
- API 呼び出しはリトライ・バックオフやレスポンス検証の実装が入っていますが、運用時はコスト・レート制限に注意してください

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定の読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注エンジン関連（BrokerFactory, Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に作成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 環境用)
    - kill.flag / stop_requested.flag / execution.pid などのフラグ／PIDファイル

運用上の注意
- .env は機密情報（API トークン等）を含むため、絶対に Git 等にコミットしないでください。
- KABUSYS_ENV=live に設定する場合は、LINE 通知設定や kill_flag_clear_on_start 等の保護設定を必ず確認してください。validate_config の live ガードが警告を出します。
- Kill Switch やリスクポリシー（ドローダウン閾値、ポジション上限など）を実運用に応じて十分検討してください。
- ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR 環境変数で変更可能です。
- AI（OpenAI）コールはコストとレート制限が発生します。API キー・利用ポリシーを運用に合わせて管理してください。
- DuckDB / SQLite のファイルパスは環境変数で切り替え可能です。テスト・開発・本番でファイルを分離してください。

サンプル .env（最小）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

付記
- ここで示した起動方法は開発環境向けの簡易な例です。プロダクション化する際はプロセス監視（systemd, Supervisor など）、バックアップ、ログローテーション設定、秘匿情報管理（Vault 等）を導入してください。
- 仕様やパラメータはコード内の docstring / コメントにも詳細が記載されています。必要に応じて該当モジュールのコメントを参照して下さい。

---

問題や改善提案がある場合はソースコード内コメントや issue を通じてフィードバックしてください。