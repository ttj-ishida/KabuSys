KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究を支援する Python ベースのシステムです。  
主な機能は以下の通りです：

- 注文実行エンジン（ExecutionEngine）: 実際の発注（またはペーパー発注）を行う
- 監視（Monitoring）: システム状態・注文・リスクを定期的にチェックしてログ・アラート・Kill Switch を管理
- ポートフォリオ構築: 候補選定・重み算出・ポジションサイズ決定・セクター制限等の純粋関数実装
- リサーチ: DuckDB を使ったファクター計算・特徴量探索モジュール
- AI 支援: ニュース NLP によるセンチメントスコアや市場レジーム判定（OpenAI API を利用）
- ツール: ペーパートレード検証レポート生成など

機能一覧
--------
- 実行（run_execution.py）
  - KABUSYS_ENV に応じて本番 / ペーパートレードを切替
  - BrokerClientFactory によるブローカークライアント生成
  - RiskManager / OrderManager / Reconciler を組み合わせた ExecutionEngine の起動
  - stop_requested.flag による外部停止受け付け、execution.pid の管理
- 監視（run_monitoring.py + monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor: 注文の滞留・異常約定などの監視（実装参照）
  - RiskMonitor: ドローダウン・ポジション数上限監視（kill flag 生成）
  - MonitoringEngine: 上記モニタを束ねてポーリング（MONITOR_POLL_INTERVAL で間隔設定）
  - SQLite に監視ログを永続化（monitoring_db）
- 環境設定支援
  - config_setup.py: 対話式で .env を作成 / 更新
  - validate_config.py: 起動前検証 CLI（--strict あり）
- リサーチ & ポートフォリオ
  - research: momentum / volatility / value ファクター、forward returns、IC 計算など
  - portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- AI モジュール（OpenAI）
  - ai.news_nlp: raw_news を集約して LLM へ送り銘柄毎にセンチメントスコアを生成し ai_scores に書込む
  - ai.regime_detector: ETF の MA200 とマクロニュースセンチメントを合成して market_regime を判定
- ツール
  - tools.paper_verification_report: ペーパー取引 DB から検証レポートを出力

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を作る:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証オプション）
   - 例:
     pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそれを利用してください）

3. プロジェクトルートに .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくはテンプレートをコピーして環境変数を設定
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（主なもの）:
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - DUCKDB_PATH: 分析用 DuckDB ファイル（default: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で参照）

4. 設定検証（起動前推奨）
   python -m kabusys.validate_config
   - --strict をつけると警告も失敗として扱います

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 下に DB やフラグファイルを置きます。logs/ にログが出力されます。

使い方
------
- 実行エンジン（本番またはペーパー）
  - 本番（KABUSYS_ENV=live）:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    -> paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）

- 監視ループ起動
  - デフォルト 60 秒間隔:
    python -m kabusys.run_monitoring
  - 環境変数で間隔上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず監視 DB は共通）

- .env の作成 / 更新
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュールの利用（プログラムから）
  - ai.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キー（OPENAI_API_KEY）が必要

停止 / Kill Switch / フラグファイル
----------------------------------
- プロセス停止要求:
  - run_execution / run_monitoring は data/stop_requested.flag の存在を監視しています。存在すると安全に終了します。
- Kill Switch:
  - リスク条件を満たすと data/kill.flag が作成され、ExecutionEngine が停止する仕組みです。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると engine 起動時に kill.flag を自動で消す挙動になりますが、本番では 0（消さない）を推奨します。

ログ
---
- ログ出力は kabusys.utils.logging_setup.setup_logging() で統一管理
- デフォルト: logs/<app_name>.log に日次ローテーション（30日保持）
- コンソール出力は stdout

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動ロード機能有）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 起動前チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込む
  - regime_detector.py     — レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ定義・永続化 API
  - system_monitor.py      — CPU/メモリ/データ鮮度/プロセス監視
  - risk_monitor.py        — ドローダウン・ポジション上限チェック
  - trade_monitor.py       — 注文関連の監視（滞留・異常等）
  - kill_switch.py         — kill.flag 管理
  - monitoring_engine.py   — 各 Monitor を束ねる
  - alert_manager.py       — アラート送信ロジック（LINE など）
- execution/
  - execution_engine.py    — ExecutionEngine（エントリは run_execution）
  - broker_factory.py      — ブローカークライアント生成
  - order_manager.py,
  - order_repository.py,
  - reconciler.py,
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — momentum/volatility/value 等
  - feature_exploration.py — forward returns / IC / summary
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py    — psutil を使った nice / affinity 設定
  - その他ユーティリティ

備考 / 運用上の注意
-------------------
- OpenAI やブローカー API を利用する機能は API キーや本番資格情報を要します。 .env に機密情報を保存しても Git にコミットしないでください。
- process_priority の設定やプロセスの nice 値変更は権限が必要になる場合があります（Linux の場合 root 権限が必要なケースなど）。
- DuckDB / SQLite のパスは Settings で指定できます。ペーパートレードは別 DB（data/paper_trading.db）に分離されます。
- 監視・kill logic は安全側を重視して設計されていますが、本番稼働前に validate_config とステージングでの十分な検証を行ってください。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください（存在する場合）。

問い合わせ / 開発
-----------------
- コードを読み、変更する場合は config/*.yaml や data ディレクトリの既存ファイルを確認してください。
- ユニットテスト / CI 用のスクリプトはリポジトリに合わせて構築してください（この README は主要な使い方と構成の概観を示します）。

以上。必要であれば「環境変数一覧の詳細」「各モジュールの API 使用例」「起動スクリプトの systemd / supervisor での運用例」などを追加で記載します。どの情報を優先して追記しますか？