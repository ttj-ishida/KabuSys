# KabuSys — README (日本語)

注意: この README は src/kabusys 以下のコードベースを元に作成しています。実行前に .env を正しく設定してください。

## プロジェクト概要
KabuSys は日本株自動売買システムのコアライブラリ群です。注文実行エンジン、監視/アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI を用いたニュースセンチメント評価など、実運用を想定したコンポーネントで構成されています。設計方針として、以下を重視しています。

- 本番/ペーパートレードの分離（環境切替）
- ロギング・監視（監視データは SQLite に永続化）
- DuckDB を用いた分析処理（prices_daily / raw_financials 等）
- OpenAI を使ったニュースNLP / レジーム判定機能（オプション）
- テストしやすい純粋関数群（ポートフォリオ構築など）

バージョン: 0.1.0（src/kabusys/__init__.py）

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - 環境に応じて MockBroker（paper_trading）または実ブローカーを使用
  - 発注・注文管理・リスク管理・再整合処理を組み合わせて実行
  - PID ファイル / stop フラグ管理
- 監視プロセス（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - kill.flag による ExecutionEngine 強制停止（Kill Switch）
  - 監視データは SQLite（monitoring.db）へ永続化
  - MONITOR_POLL_INTERVAL で間隔を調整可能（デフォルト 60 秒）
- 設定周り
  - .env 対話式作成ウィザード（config_setup）
  - 起動前チェックツール（validate_config）
  - Settings クラスで環境変数管理（自動読み込みロジックあり）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ適用など
- 研究/リサーチ（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC 計算、統計サマリー
- AI（ai）
  - ニュース記事のセンチメント評価（OpenAI）
  - 市場レジーム判定（MA + マクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート出力スクリプト（tools/paper_verification_report）

## 要件（実行環境）
- Python 3.10 以上（typing に `X | Y` 構文を使用）
- 推奨パッケージ（最低限の例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML 検証を行う場合）
- SQLite は標準ライブラリで OK

例（仮想環境内で）:
pip install duckdb psutil openai PyYAML

> 実際の requirements はプロジェクトに応じて用意してください。

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動。

2. Python 仮想環境を作成して依存パッケージをインストール。

3. .env の作成（対話式ウィザード推奨）
   - 実行:
     python -m kabusys.config_setup
   - 生成される .env はプロジェクトルートに保存されます（既存値の読み込み・更新に対応）。
   - 重要な必須変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 環境例:
     KABUSYS_ENV=development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=...（AI 機能を使う場合）

4. 設定検証（起動前チェック）
   - 実行:
     python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付ける:
     python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - ログ: デフォルトは logs/
   - DB: デフォルトは data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db

注: Settings モジュールはプロジェクトルートの .env/.env.local を自動読み込みします（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## 使い方（主要コマンド）

- 実行エンジン起動（通常）
  - python -m kabusys.run_execution
  - 起動前に KABUSYS_ENV が paper_trading のときは paper_trading 用の MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 実行中に data/stop_requested.flag を作成するとエンジンへ停止シグナルが送られ、シャットダウンします。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可能）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔: 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可（正の整数のみ有効）。
  - 監視は本番用 sqlite_path を常に使用（環境に依らず）。監視 DB の初期化・マイグレーションは自動実行されます。
  - 監視プロセスは data/stop_requested.flag の存在で終了します。

- .env 作成/更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit code 1

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - OPENAI_API_KEY 環境変数を設定する必要があります（score_news / score_regime 等）。
  - ニュース NLP:
    - kabusys.ai.score_news を呼び出して ai_scores テーブルへ書き込み
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime を呼び出して market_regime テーブルへ書き込み

## 主要環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- データベース:
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- ロギング:
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - LOG_DIR（ログ出力先。logging_setup が参照）
- 実行制御:
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）
- 監視:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）
- Paper Trading:
  - PAPER_FILL_MODE (instant | partial | never | reject) — MockBroker の挙動を制御

（詳しいプロパティは src/kabusys/config.py 内 Settings クラスを参照してください）

## 運用上の注意 / 動作仕様
- ペーパートレードと本番は DB を分離:
  - paper_trading では PAPER_TRADING_SQLITE_PATH が使用され、本番の monitoring.db を上書きしません。
- Kill Switch:
  - 各監視結果から KillSwitch が判定されると data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - kill.flag の存在は ExecutionEngine 側でチェックされ、存在する場合は起動を拒否または停止します。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 により起動時自動クリアが可能（本番では推奨しない）。
- 停止フラグ:
  - data/stop_requested.flag の作成で run_monitoring / run_execution のループを安全に終了できます（外部制御用）。
- ログ:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトで使用しています。デフォルトは logs/<app_name>.log（日次ローテーション、30 日保持）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は簡易なマイグレーション（カラム追加）を実行します。
- AI 関連:
  - OPENAI_API_KEY が必要。API 呼び出しはリトライロジック・検証ロジックを含むが、API キー未設定時は例外が投げられます。
- 権限:
  - set_process_priority は psutil を用いて優先度設定を試みますが、失敗（AccessDenied 等）した場合は警告を出してスキップします。

## ディレクトリ構成（主要ファイルと役割）
以下は src/kabusys 以下の概観（主要モジュールのみ抜粋）:

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理、.env 自動読み込み
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor（監視）起動スクリプト
  - utils/
    - logging_setup.py — 統一ロギング設定
    - process_priority.py — 優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層（テーブル定義・読み書き API）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス生存チェック
    - trade_monitor.py — （注文関連の監視: 滞留注文・約定異常等）※詳細はソース参照
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — （アラート送信の抽象化）※実装参照
  - execution/ — ExecutionEngine や注文管理周り（エンジン / risk manager / broker factory 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・キャップ/スケーリング
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py — マーケットレジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（各ファイルの詳細な docstring を参照してください）

## よくある操作例 / 便利情報

- 監視だけを一度だけ実行してテストする:
  - モジュール単位で MonitoringEngine を組み立て、run_once を呼ぶ（テスト用）。
- MONITOR_POLL_INTERVAL の設定:
  - 環境変数で秒数を指定。0 や負の値は無効でデフォルト（60 秒）にフォールバックします。
- kill.flag を手動でクリア:
  - data/kill.flag を削除するか、設定で自動クリアを有効にする（本番では注意）。
- Paper Trading の検証:
  - ペーパートレード DB を指定して tools/paper_verification_report でレポート生成。

## 最後に
この README はコード内の docstring / コメントを元に要点をまとめたものです。実行前に必ず python -m kabusys.validate_config で設定を検証してください。さらに詳しい内部仕様やアルゴリズムは各モジュール（src/kabusys 以下）の docstring を参照してください。質問や改善点があればお知らせください。