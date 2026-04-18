KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視・アラート機構、ペーパートレード向け検証ツール、LLM を使ったニュースセンチメント・レジーム判定など、取引に必要な主要コンポーネントを含みます。

主な設計方針
- DuckDB / SQLite をデータ基盤に利用（分析用は DuckDB、監視・取引ログは SQLite）。
- 本番とペーパートレードを明確に分離（KABUSYS_ENV により挙動切替）。
- 外部 API（kabuステーション、J-Quants、OpenAI など）は設定可能で、失敗時はフェイルセーフで継続する設計。
- 環境変数を .env から自動読み込み（プロジェクトルートに依存）し、対話式ウィザードで .env を生成可能。

機能一覧
-------
- 設定管理・ウィザード
  - 対話式 .env 生成: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient を含む）
  - リスク管理、注文管理、再整合（reconciler）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite で system_status / trade_logs / risk_logs / positions / dashboard を永続化
  - Kill Switch（data/kill.flag）で ExecutionEngine を停止
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、ポジションサイジング、セクター制約、レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ
- AI コンポーネント
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア化と ai_scores への書込み
  - レジーム判定（ETF ma200 + マクロニュースの LLM センチメント合成）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
--------------
前提
- Python 3.10+（typing の | 演算子を使用）
- システムにより追加の OS パッケージが必要になることがあります（例: Windows/Linux の psutil 動作環境等）。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は設定 YAML の検証に使用（任意）: pip install pyyaml

   （リポジトリに requirements.txt があればそれを利用してください。）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV: development | paper_trading | live
- データベース:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB; デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB; デフォルト: data/paper_trading.db)
- OpenAI:
  - OPENAI_API_KEY
- ログ:
  - LOG_LEVEL (例: INFO)
  - LOG_DIR (デフォルト: logs/)
- その他:
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒。デフォルト 60）
  - PAPER_FILL_MODE（ペーパートレードの約定モード: instant|partial|never|reject）

使い方（起動例）
----------------

1. 設定ウィザード・検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - 実行前に data/stop_requested.flag が存在すると起動をスキップします。
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。

3. Monitoring（監視）起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。
   - 監視は環境に関わらず SQLite の本番 sqlite_path を使用します。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

注意事項・運用メモ
- Kill Switch
  - Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch の評価は MonitoringEngine 側で行われます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- ログ
  - 共通の logging セットアップを使用（kabusys.utils.logging_setup.setup_logging）。
  - デフォルトは stdout ストリームと logs/<app_name>.log に日次ローテーション（30日保持）。

- Paper vs Live
  - KABUSYS_ENV=paper_trading では発注はモックされ、履歴は data/paper_trading.db に記録されます。
  - 本番（live）では実ブローカーへ発注されます。設定を十分に確認してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるセンチメント
    - regime_detector.py      — レジーム判定（ma200 + macro sentiment）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義・永続化層
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — （Trade 監視処理）
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — （アラート送信管理）
    - monitoring_engine.py    — モニタ群の束ね実行
  - execution/
    - execution_engine.py     — 実行エンジン本体
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に使用するファイル群を格納する想定: .db, .pid, flag 等)

補足 / 開発者向けヒント
---------------------
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト等で便利）。
- OpenAI 呼び出し部分はリトライ・バックオフ・レスポンスバリデーションを備えています。API キーは OPENAI_API_KEY に設定してください。
- DuckDB への接続はモジュール内で受け渡して使う設計になっています（研究・AI モジュールは DuckDB 接続を引数で受け取る）。
- process_priority および CPU affinity の設定ユーティリティがあり、起動スクリプトで優先度を "high" に上げてから各エンジンを起動します（権限により失敗することがありますが警告でスキップされます）。

ライセンス / バージョン
----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリに含めてください（この README には含めていません）。

問題報告 / 貢献
---------------
バグ報告、機能提案や PR はリポジトリの Issue / Pull Request を通じて行ってください。README にないコマンドや設定項目はソース（config_setup.py, validate_config.py, run_*.py）を参照してください。

以上がこのコードベースの概要と基本的な運用手順です。必要であれば、起動例や .env のサンプル、よくあるトラブルシュートを追記します。どの情報を優先して追加しますか？