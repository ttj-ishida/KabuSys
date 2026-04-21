KabuSys
=======

日本株向けの自動売買・リサーチ基盤（モジュール群）の一部実装です。  
本リポジトリは以下の機能群を提供します（※一部実装はモックまたは呼び出し先モジュールに依存します）:

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）コンポーネント（System / Trade / Risk）
- Kill Switch（リスクトリガーで Execution を停止するフラグ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ機能（モメンタム / バリュー / ボラティリティ等のファクター計算、特徴量探索）
- AI 支援（ニュースのセンチメントスコアリング、レジーム判定：OpenAI API を利用）
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証 CLI）
- ペーパートレード向け検証レポート生成ツール

主な設計方針（一部）
- DuckDB（分析用）、SQLite（監視・発注ログ）を併用。
- 環境変数 / .env による設定管理（config モジュール）。
- 本番・ペーパートレードは DB を分離（KABUSYS_ENV）。
- OpenAI 呼び出しはリトライ・バリデーションなどを備えた堅牢な実装。

機能一覧
--------
- config_setup: 対話式ウィザードで .env を生成/更新（python -m kabusys.config_setup）
- validate_config: .env と config/*.yaml を起動前に検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録
- run_monitoring: SystemMonitor のポーリングループを起動（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず production sqlite_path（data/monitoring.db）を使用して初期化
- monitoring: system_status / trade_logs / positions / risk_logs / dashboard の永続化と各種モニタ
  - KillSwitch による data/kill.flag 書き込みで ExecutionEngine を停止可能
- ai.news_nlp: raw_news をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores に書き込み
- ai.regime_detector: ETF 1321 の MA とマクロ記事センチメントから market_regime を算出
- research: duckdb を使ったファクター計算・特徴量解析ユーティリティ
- portfolio: 候補選定 / 重み付け / ポジションサイズ計算 / セクター制御
- tools.paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを生成

セットアップ手順
---------------
前提: Python 3.10+ を想定（typing, match 等の使用はなしだが、モダンな環境を推奨）。  
依存パッケージ（主なもの）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
これらを pip でインストールしてください（requirements.txt がない場合は明示的にインストール）。

例:
- 仮想環境の構築（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil openai PyYAML

環境変数 / .env の準備
- 対話式ウィザード（.env を生成・更新）
  - python -m kabusys.config_setup
- 主要な必須環境変数（.env へ設定する項目）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
- 主要な任意/デフォルト設定
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード DB）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR（デフォルト: INFO）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード挙動、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 を推奨）

設定検証
- .env と config/*.yaml の基本チェック:
  - python -m kabusys.validate_config
  - 厳格モード（警告もエラーとして扱う）: python -m kabusys.validate_config --strict

使い方
-------
基本的な起動/実行コマンド:

- ExecutionEngine 起動（通常の実行）
  - python -m kabusys.run_execution
  - 注意: 起動時に data/stop_requested.flag があると起動を中止します
  - 起動直後にプロセス優先度を "high" に設定します（プラットフォームに依存）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録

- Monitoring 起動（ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒。stop フラグはプロジェクトルート/data/stop_requested.flag
  - 監視は monitoring DB を初期化し、SystemMonitor.check_once() を繰り返します

- Kill Switch 制御
  - KillSwitch は RiskMonitor 等で条件充足時に flag ファイル（デフォルト data/kill.flag）を書き込みます
  - ExecutionEngine は kill.flag を検出して停止します（KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアするオプションあり）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - 簡易的に稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を出力します

- .env ウィザード
  - python -m kabusys.config_setup
  - 生成された .env を保存後、python -m kabusys.validate_config で確認することを推奨

環境変数の要点（まとめ）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: 実際のブローカーアクセスを模擬、DBは paper_sqlite_path を使用
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: データストアのパス
- OPENAI_API_KEY: ai.news_nlp / ai.regime_detector を利用する際に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_PATH (Settings.kill_flag_path): KillSwitch の flag ファイルパス
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（1=する）

ロギング
- kabusys.utils.logging_setup.setup_logging(app_name=...)
  - stdout に StreamHandler を出し、さらに logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/）
  - ログディレクトリが作成できなければコンソール出力のみで継続

注意事項 / 運用メモ
- run_execution.run_session はスレッドで実行され、data/stop_requested.flag の検出で停止処理をトリガします
- monitoring は監視用の SQLite（monitoring.db）を初期化します。監視は本番 DB に影響を与えないように設計されていますが、設定の誤りに注意してください
- OpenAI を使う処理は APIキーと呼び出し料が必要です。API 呼び出し失敗時はフォールバック動作（スコア=0 など）をする実装になっていますが、APIキーは必ずセットしてください
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。validate_config は live 向けの追加警告を出します

ディレクトリ構成（抜粋）
--------------------
以下は src/kabusys 配下の主要ファイル／モジュール（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/.env ロードと Settings 定義
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py         — 市場レジーム判定（MA + LLM）
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py     — 将来リターン / IC / 統計
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py           — SQLite テーブル定義 & MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py (参照実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - utils/
    - __init__.py
    - logging_setup.py           — 共通ロギング設定
    - process_priority.py        — プロセス優先度 / CPU affinity 設定

（上記に含まれないモジュール・ファイルは省略しています。実システムでは execution.*, data.*, strategy.* などの追加モジュールが存在します）

開発メモ / テスト
- 各コンポーネントは依存注入（DB コネクションやクライアント）でテストしやすく設計されています（例: SystemMonitor, MonitoringEngine.run_once など）。
- OpenAI / ブローカー呼び出しはユニットテスト時にモックしてください。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 "0.1.0"）。

お問い合わせ / 変更
- 本 README はコードベースから主要情報を抜粋してまとめたものです。実運用にあたっては config/*.yaml（生成スクリプト使用）や運用手順書に従ってください。

以上。必要があれば、セットアップ手順の詳細（requirements.txt の推奨内容や systemd / supervisor の起動例、ログローテーション方針、cron タスク等）を追記します。どの情報がさらに必要か教えてください。