KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム（分析・ポートフォリオ構築・発注・監視・AI 補助）を構成する Python モジュール群です。  
ここに含まれるコードは、ローカル開発・ペーパートレード・本番（live）を想定した設計になっており、設定は .env ファイル／環境変数で行います。

主な特徴
--------
- 戦略・ポートフォリオ
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン計算、IC（情報係数）等の研究用モジュール
  - 候補選定（score/ equal）、重み付け、ポジションサイズ計算（単元株丸め・資金制約反映）
  - セクターキャップやレジーム乗数によるリスク調整
- 実行エンジン（ExecutionEngine）
  - ブローカークライアントを抽象化（本番 or Mock：KABUSYS_ENV=paper_trading で Mock を使用）
  - リスク管理、注文管理、リコンシリエーション等の実行周りコンポーネント
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログは SQLite（data/monitoring.db）に永続化
  - Kill Switch（閾値超過時に data/kill.flag を書き込んでExecutionEngineに停止シグナル）
- AI 補助
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込む
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
- ツール
  - 環境設定ウィザード（.env 生成）: kabusys.config_setup
  - 設定検証 CLI（.env / config/*.yaml の簡易検査）: kabusys.validate_config
  - Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report
- 共通ユーティリティ
  - ロギング設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度・CPU affinity 設定

必要条件（主な依存）
-------------------
- Python 3.9+（プロジェクトで厳密なバージョンは指定していません）
- パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の検証に使用）
- SQLite（標準ライブラリ）
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要

インストール（開発環境）
----------------------
1. リポジトリをクローンしてルートに移動。
2. 仮想環境を作成・有効化（推奨）。
3. 必要なパッケージをインストール:
   - もし requirements.txt があれば: pip install -r requirements.txt
   - なければ最低限: pip install duckdb psutil openai
   - YAML 検証を行う場合: pip install pyyaml

設定（.env）
-----------
プロジェクトルートに .env を作成する必要があります。対話式ウィザードで簡単に作成できます:

- .env の作成／更新（対話式ウィザード）
  - python -m kabusys.config_setup
  - 対話で各キーを入力し .env を保存します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションを付けると警告も FAIL 扱いになります。

重要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境指定
  - KABUSYS_ENV: development / paper_trading / live
    - paper_trading の場合、発注は MockBrokerClient を使用し data/paper_trading.db に記録
- DB / ログ関連
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — 監視用 SQLite（monitoring は常に本番 sqlite_path を参照）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- AI
  - OPENAI_API_KEY — OpenAI API キー
- 監視関連
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1)
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。run_monitoring で使用）
  - PID_FILE_PATH / KILL_FLAG_PATH — Settings 経由でカスタマイズ可能

起動方法（主要な CLI）
---------------------

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が paper_trading のときは paper DB を使用（data/paper_trading.db）
    - スレッドでエンジンを起動し、data/stop_requested.flag があれば停止
    - 実行時に PID ファイル（data/execution.pid）を書きます
    - プロセス優先度を "high" に設定しようとします（psutil 経由）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず）
    - 停止はプロジェクトルート/data/stop_requested.flag を作成して行えます

- .env 対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

停止・Kill Switch
-----------------
- 停止フラグ（即時停止要求）
  - run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を参照してループを終了します。管理者が停止させたい場合はこのファイルを作成してください。
- Kill Switch（リスク基準到達時の自動停止）
  - KillSwitch はリスク監視で閾値（ドローダウンやポジション上限）に到達すると data/kill.flag を書き込みます。Execution 側は起動時・実行中にこのフラグの存在を検知して適切に停止する設計になっています。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ロギング
-------
- デフォルト: logs/<app_name>.log（日次ローテーション、30日分保持）とコンソール出力（stdout）
- setup_logging() でログディレクトリやレベルを環境変数で上書き可能（LOG_DIR / LOG_LEVEL）

ディレクトリ構成（主要ファイル・モジュール）
-----------------------------------------
（以下は src/kabusys 以下の主要モジュール群）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュースを OpenAI でセンチメント付与
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - portfolio/
    - portfolio_builder.py   — 銘柄選定・スコアソート・重み計算
    - position_sizing.py     — 株数算出・単元株丸め・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル初期化 + CRUD ユーティリティ）
    - system_monitor.py      — システム・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （発注ログ監視など / 実装あり）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （通知の集約/送信管理 / 実装あり）
  - execution/
    - broker_factory.py      — ブローカークライアント生成
    - execution_engine.py    — ExecutionEngine 本体
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化（SQLite など）
    - reconciler.py          — 注文状態同期
    - risk_manager.py        — 発注前リスクチェック
  - data/                     — データ用ディレクトリ（デフォルト: data/）
  - utils/
    - logging_setup.py       — 統一ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

注意事項・運用メモ
----------------
- 監視（monitoring）は監視用 DB（SQLITE_PATH）を常に利用します。KABUSYS_ENV に関わらず本番用 sqlite_path を使用する点に注意してください。
- ペーパートレード（KABUSYS_ENV=paper_trading）は paper 用 sqlite（PAPER_TRADING_SQLITE_PATH）に分離されます。本番 DB と完全に分離して運用できます。
- OpenAI を使用する機能は API のコスト・レート制限に注意してください。実装にリトライやバックオフのロジックがありますが、運用時はキー管理とコール頻度に注意してください。
- .env は機密情報（API キー等）を含むため Git にコミットしないでください（config_setup の README でも注意喚起あり）。
- ローカルで試すときは KABUSYS_ENV=development にして実行し、必要な機能だけを順に有効化して検証するのが安全です。

よく使うコマンド例
-----------------
- .env を新規作成／更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ペーパー検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

サポート・拡張
--------------
- 新しい戦略や取引ルールは portfolio/ と execution/ に追加してください（ユニットテストを推奨）。
- DuckDB のデータ（prices_daily, raw_financials, raw_news 等）を用意すれば research/ や ai/ の機能をローカルで検証できます。
- YAML 設定ファイル（config/*.yaml）は generate_script 等で管理する想定です。validate_config が存在とパースをチェックします（PyYAML 必須）。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期バージョン）。
- ライセンス情報はリポジトリのトップレベルに LICENSE を置いて管理してください（本 README には含めていません）。

最後に
------
この README はコードの主要な利用方法と構成をまとめたものです。実運用前に必ず validate_config による検証、テストネットやペーパートレードでの十分な試験を行ってください。必要があれば各モジュール（monitoring, execution, ai, research など）のドキュメントを追加で用意してください。