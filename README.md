KabuSys
=======

日本株向けの自動売買 / リサーチ用ライブラリ兼実行基盤の一部です。本リポジトリには以下の主要機能を持つモジュール群が含まれます：実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量探索）、AI（ニュース NLP／レジーム判定）、紙上検証ツールなど。

本 README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（主要スクリプトの実行例）、およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は日本株自動売買システムのコンポーネント群です。設計方針の概略：

- 実行エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネントを備える
- Paper Trading（ペーパートレード）モードと Live（本番）モードを切り替え可能
- DuckDB / SQLite を用いたデータ保存と分析（prices_daily / raw_financials 等）
- OpenAI を用いたニュースセンチメント（AI モジュール）やレジーム判定機能
- 設定は .env ファイル（環境変数）で管理、対話式ウィザード／検証 CLI を提供
- ログは標準出力と日次ローテートログ（logs/<app>.log）に出力

主要機能一覧
--------------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading モードでは MockBroker を使用し、paper 用 DB に分離
  - 実行中の停止は stop flag（data/stop_requested.flag）や kill.flag により制御
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
  - システムリソース、データ鮮度、注文ログ、ドローダウンなどを監視
  - kill.flag を書き込む KillSwitch により自動停止トリガーを提供
- 設定ウィザード（config_setup.py）
  - .env の対話的作成・更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の存在や妥当性チェック（--strict オプションあり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL を判定
- ポートフォリオ構築ユーティリティ（portfolio/*）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数など
- リサーチ（research/*）
  - ファクター計算（momentum, volatility, value）や将来リターン、IC 計算、統計サマリ
- AI（ai/*）
  - ニュースセンチメント（news_nlp.py）および市場レジーム判定（regime_detector.py）
  - OpenAI API（gpt-4o-mini）を利用（API キーは OPENAI_API_KEY）

必要条件（依存パッケージ）
-----------------------
最低限想定される Python パッケージ（環境に合わせて適宜バージョン指定してください）：

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合）
- その他（プロジェクト内で追加の依存がある場合は requirements.txt を参照してください）

例：
pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローン / 配布物を配置
2. 仮想環境の作成（任意推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成（推奨: 対話式ウィザードを使用）
   - python -m kabusys.config_setup
     - J-Quants / kabuステーション API トークン等を入力してください
   - .env は Git にコミットしないでください
5. 設定の検証（必須ではないが推奨）
   - python -m kabusys.validate_config
   - 問題がある場合は出力メッセージに従って修正
6. DB ディレクトリや data ディレクトリの作成はスクリプトが自動作成しますが、必要に応じて先に作成して権限を確認してください

主要な環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- SQLITE_PATH: 監視用 SQLite（monitoring）デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス（分析用）デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading モード時の SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject） デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
--------------------

1) 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit(1)）

3) 実行エンジンの起動（Execution）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合:
     - MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます
   - 実行時に data/execution.pid に PID を書き込みます
   - 停止: data/stop_requested.flag を作成すると起動中のループが検知して停止します

4) 監視ループの起動（SystemMonitor を定期実行）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
   - 監視は Settings.sqlite_path を使用（Monitoring は環境に依存せず本番 sqlite_path を参照）
   - 停止フラグ: data/stop_requested.flag を作成すると監視ループが終了します

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     --db PATH を指定するか環境変数 PAPER_TRADING_SQLITE_PATH を設定

6) AI モジュールの利用（プログラムから呼び出し）
   - ニューススコアリング: from kabusys.ai.news_nlp import score_news
   - レジーム判定: from kabusys.ai.regime_detector import score_regime
   - いずれも OpenAI API キーを OPENAI_API_KEY か引数で渡します

ログ
---
ログ設定ユーティリティは kabusys.utils.logging_setup.setup_logging を通して行われます。ログは stdout と logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリは環境変数 LOG_DIR で変更可能です。

停止・Kill スイッチ（安全停止）
-----------------------
- 手動で監視・実行ループを止めるにはプロジェクトルートの data/stop_requested.flag を作成してください（両スクリプトはこのファイルを監視して停止します）。
- KillSwitch（data/kill.flag）: RiskMonitor 等が条件を満たした際に kill.flag を書き込み、ExecutionEngine 側で検知して安全に停止させる仕組みがあります（本番での自動停止ガード）。

データベース / マイグレーション
----------------------------
- monitoring_db.init_monitoring_db は必要なテーブルを冪等に作成します（マイグレーション的にカラム追加も行われる）。
- run_execution/run_monitoring は実行時に DB 接続を行い、init_monitoring_db を呼び出します（monitoring 用テーブルが存在することを保証）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール一覧（抜粋）です：

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - trade_monitor.py       — （注文監視：ソース参照）
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知管理：ソース参照）
  - execution/                — Execution 関連（OrderManager, BrokerFactory, Engine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（OpenAI 呼び出し）
  - data/                    — 実行時生成データ（logs/, data/*.db, flags 等）

補足・運用上の注意
-----------------
- .env は絶対にソース管理にコミットしないでください（機密情報含む）。
- KABUSYS_ENV を live に設定する際は十分な注意が必要です。validate_config は live 時に追加の警告を出します（LINE 通知など）。
- OpenAI API を使用する機能は外部 API 呼び出しに依存するためネットワーク・API レートに配慮してください（リトライ・バックオフ実装あり）。
- run_execution / run_monitoring はログと PID / flag ファイルにより外部から制御できます。運用監視時は logs と data ディレクトリの権限・容量に注意してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）。

問い合わせ / 開発
-----------------
- 開発者向け: 新しい依存を追加したら requirements.txt を更新し、config/*.yaml のテンプレートやドキュメントを併せて更新してください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env の読み込みを無効化できます。

以上がこのコードベースの利用開始に必要な概要と手順です。必要ならば各モジュール（ExecutionEngine、OrderManager、TradeMonitor、AlertManager など）の詳細な使い方・API ドキュメントも作成できますので、どの部分を深掘りしたいか教えてください。