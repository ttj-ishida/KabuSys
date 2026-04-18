# KabuSys

日本株向け自動売買システム（ライブラリ兼運用スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポート作成・AI（ニュースセンチメント）処理を含む自動売買基盤の一部です。モジュールは小さな責務に分割され、テストしやすい純粋関数群と運用スクリプト（エンジン）で構成されています。

主な特徴
- ExecutionEngine / Monitoring の起動スクリプト（run_execution, run_monitoring）
- 設定ウィザード（.env 生成）と設定検証ツール
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる安全停止）
- ポートフォリオ構築、ポジションサイズ計算、セクター制限などの純粋関数群
- Research（ファクター計算、IC 計算など）: DuckDB を利用した分析パイプライン
- AI モジュール（OpenAI を使ったニュースセンチメント評価 / レジーム判定）
- Paper Trading 用の検証レポート生成ツール

目次
- 機能一覧
- 必要条件
- セットアップ手順
- 使い方（実行例）
- 主な環境変数 / 設定
- 停止・Kill Switch に関する挙動
- ディレクトリ構成（主要ファイル説明）
- 補足・注意点

機能一覧
- 環境設定ウィザード: python -m kabusys.config_setup（.env を対話式生成）
- 設定検証: python -m kabusys.validate_config（必須環境変数や config/*.yaml の存在チェック）
- Execution エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading DB に分離
  - 起動時にプロセス優先度を上げる（可能な場合）
- Monitoring 起動: python -m kabusys.run_monitoring
  - SystemMonitor をポーリング（MONITOR_POLL_INTERVAL で間隔設定）
  - 監視結果は SQLite（monitoring.db）に永続化
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.score_news: raw_news を OpenAI に投げて銘柄単位のスコアを ai_scores に書き込む
  - kabusys.ai.regime_detector: ETF / マクロニュースを元に市場レジームを判定
- Research（ファクター計算、将来リターン、IC 計算）
- Portfolio（候補選定、重み付け、株数計算、セクター制限など）
- ログ設定ユーティリティ、プロセス優先度設定ユーティリティ、DB 初期化マイグレーション など

必要条件
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml を検証する場合）
- （任意）仮想環境の利用を推奨

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合）pip install -r requirements.txt
4. .env を作成
   - python -m kabusys.config_setup
     - 対話式ウィザードで J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを設定します
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再実行
6. データディレクトリやログディレクトリは自動作成されますが、権限等に注意してください

使い方（実行例）
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV を切り替えることで paper_trading / live / development を選択
  - paper_trading ではデータは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に分離
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（default: 60）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db で別 DB を指定
- AI / レジーム判定（プログラムから呼ぶ）
  - OPENAI_API_KEY 環境変数を設定して、ライブラリ関数を呼ぶ
    - 例: from kabusys.ai import score_news; score_news(conn, target_date)
  - 注意: OpenAI API キーが必要（環境変数 OPENAI_API_KEY または api_key 引数）

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant / partial / never / reject（paper_trading の Mock の約定挙動）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- LOG_DIR: ログ保存先（デフォルト: logs/）

停止・Kill Switch・フラグファイル
- 強制停止・運用のためのフラグファイルが data/ 以下に置かれます
  - stop_requested.flag: run_monitoring / run_execution がこのファイルを検知すると安全にループを抜けて終了します（手動停止に利用可）
  - kill.flag: KillSwitch が条件を満たした場合に書き込まれるファイル（ExecutionEngine を停止させるために使用）
  - execution.pid: ExecutionEngine の PID を記録するファイル（場所: data/execution.pid）
- KillSwitch の評価は RiskMonitor 等の結果を用いて行われ、必要なら kill.flag を書きます。kill.flag は既存なら上書きされません（冪等）。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 にしていると kill.flag を自動クリアする設定も可能（注意: 本番環境では 0 推奨）。

ログ
- ロギングは統一ユーティリティ kabusys.utils.logging_setup で設定されます
  - 標準出力（stdout）と日次ローテーションのファイル出力（logs/<app>.log）を行います
  - デフォルトで 30 日分保持

データベース
- DuckDB（分析用）: data/kabusys.duckdb（デフォルト）
- SQLite（監視ログ）: data/monitoring.db（デフォルト）
- Paper Trading 用 SQLite: data/paper_trading.db（paper_trading 時に使用）
- monitoring_db モジュールは起動時に必要テーブルを冪等に作成し、簡単なマイグレーション機能（カラム追加）を持ちます

ディレクトリ構成（主要ファイル・モジュールの説明）
- src/kabusys/
  - __init__.py: パッケージ定義
  - config.py: 環境変数の読み取り・Settings クラス（自動 .env ロードロジック含む）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 起動前設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じた DB 分離など）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: ログ設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite 永続化層（監視テーブル）
    - system_monitor.py: CPU/メモリ/ディスク / データ鮮度 / Execution プロセス監視
    - trade_monitor.py: （売買関連監視 — 省略されているファイル）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: Kill Switch 実装（kill.flag 書き込み）
    - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py: （アラート送信ロジック — 省略されているファイル）
  - execution/: Execution 関連コンポーネント（Engine, BrokerFactory, OrderManager, RiskManager 等）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数計算、aggregate cap、lot_size 丸めなど
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: Momentum / Value / Volatility 等のファクター計算（DuckDB 使用）
    - feature_exploration.py: forward returns, IC, 統計サマリ等
  - ai/
    - news_nlp.py: OpenAI を使ったニュースセンチメント集約・ai_scores への書込み
    - regime_detector.py: ETF MA とマクロニュースで市場レジームを判定
  - tools/
    - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト
  - data/: デフォルトの DB・フラグファイル等を置くディレクトリ（起動時に作成される）
  - logs/: ログファイル保存ディレクトリ（デフォルト）

補足・注意点
- .env は機密情報を含むため Git にコミットしないでください
- KABUSYS_ENV が live の場合は本番アラートや Kill Switch の注意メッセージが出ます。設定は慎重に
- OpenAI を使う機能は API キーが必須で、API のレート制限や課金に注意してください
- Paper Trading と本番 DB は分離する設計になっています（paper_trading モード時のみ paper DB を使用）
- ログディレクトリや DB の配置に失敗するとファイル出力が無効化され、コンソール出力のみになる場合があります
- 一部の外部依存（psutil, duckdb, openai, PyYAML）により、環境によっては追加インストールが必要です

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。より詳細な仕様やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等の設計ドキュメント）があれば、それに従ってパラメータ調整や運用手順を確認してください。必要であれば、各モジュールの詳細ドキュメント（docstring）を参照するか、README を拡張します。