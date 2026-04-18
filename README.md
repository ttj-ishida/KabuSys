# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプトを収めたリポジトリ用 README（日本語）。

以下はソースコード（src/kabusys 以下）を基に作成したドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。  
主要機能は以下の通り:

- 戦略・ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI を使ったニュースセンチメント評価 / 市場レジーム判定（OpenAI）
- 実行エンジン（ExecutionEngine）起動スクリプト（ペーパートレードと本番を分離）
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる停止）
- ロギング設定ユーティリティ、プロセス優先度設定などのユーティリティ群
- Paper Trading の検証レポート生成ツール

設計方針として、DuckDB / SQLite をデータ層として使い、外部 API 呼び出しや本番注文処理は設定に応じて分離されています（`KABUSYS_ENV=paper_trading` など）。

---

## 機能一覧（主要機能）

- config 管理
  - .env を自動読み込み / 対話式ウィザードで .env を生成（config_setup）
  - 設定検証 CLI（validate_config）
- 実行 / 監視
  - run_execution: ExecutionEngine 起動スクリプト（paper_trading 用 DB 分離）
  - run_monitoring: SystemMonitor のポーリングループ起動
  - stop/kill フラグ（data/stop_requested.flag, data/kill.flag）でプロセス制御
- 監視 DB（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを冪等に初期化
  - MonitoringDB クラスによる読み書き API
- モニタリング/アラート
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス検出、データ鮮度チェック
  - TradeMonitor / RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch: ルールに応じた kill.flag 書き込み
  - MonitoringEngine: それらをまとめて定期実行・アラート送信
- ポートフォリオ構築
  - 候補選定、等ウェイト・スコア加重ウェイト、ポジションサイズ計算（単元株丸め、aggregate cap）
  - セクターキャップ、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン / IC / 統計サマリー
- AI 系
  - news_nlp: OpenAI を使ったニュースセンチメント（銘柄単位）→ ai_scores テーブルへ書き込み
  - regime_detector: ETF の MA とマクロニュースから市場レジーム判定（LLM を利用）
- ツール
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力

---

## セットアップ手順

前提:
- Python 3.10+（ソースで | 型注釈を使っているため）
- Git clone などでリポジトリを取得し、作業ルートがプロジェクトルートになるように配置

1. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 以下は主要な依存例です（プロジェクトに requirements.txt がある場合はそれを使ってください）
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML — validate_config が YAML の検証を行う場合に必要
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を作成し必要な環境変数を設定
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY を設定

4. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラーにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリと初期 DB
   - デフォルトでは以下のパスが使われます（必要であれば .env で上書き）
     - DUCKDB_PATH = data/kabusys.duckdb
     - SQLITE_PATH = data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
     - PID_FILE_PATH = data/execution.pid
   - 起動時にログディレクトリ（デフォルト logs/）が自動作成されます。LOG_DIR を変更可能。

注意:
- 実行スクリプトはプロセス優先度や PID 操作を行います。psutil による権限問題で警告が出る場合がありますが、通常はフォールバックして動作します。

---

## 使い方（主要スクリプト・API）

基本的にモジュールはモジュール実行可能（python -m ...）です。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モード切替:
    - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込まれる（本番 DB と分離）
  - 停止:
    - プロジェクトルートの data/stop_requested.flag を作成すると、既に起動中の run_execution が検知してエンジンを停止します
  - PID:
    - PID はデフォルト data/execution.pid に記述されます（Settings.pid_file_path で変更可能）

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 無効な値（0 以下や非数）を与えるとデフォルト 60 秒にフォールバック
  - run_monitoring は実行環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH で既定パスを上書き可能

- AI 機能（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルへ書き込む。api_key を渡すか OPENAI_API_KEY を環境変数に設定
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを判定して market_regime テーブルへ書き込む

- ロギング
  - setup_logging(app_name="execution") などで root ロガーを統一的に初期化
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: logs/execution.log）
  - LOG_DIR 環境変数で変更可能

- Kill Switch / Stop Flag
  - KillSwitch は条件に応じて Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine はこれを検出して停止を試みる
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアする（本番では 0 推奨）

---

## 重要な環境変数（抜粋とデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DB パス
  - DUCKDB_PATH — data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH — data/monitoring.db（デフォルト）
  - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 時）
- ログ/PID
  - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs）
  - PID_FILE_PATH — data/execution.pid（デフォルト）
- モニタリング / 実行制御
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1"で有効、デフォルト "0"）
- Paper Trading
  - PAPER_FILL_MODE — instant / partial / never / reject（MockBroker の挙動、デフォルト: "instant"）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector などで使用

---

## 開発・運用上の注意

- 実行スクリプトはプロセス優先度を変更しようとします（psutil を利用）。権限不足で警告が出る場合は通常は無視して大丈夫です。
- run_execution は paper_trading と本番の DB を分離するため、誤って本番口座で発注してしまうリスクを下げています。KABUSYS_ENV を正しく設定してから起動してください。
- Kill Switch（data/kill.flag）や stop_requested.flag による停止は冪等性を意識して実装されています。必要に応じて flag ファイルを作成 / 削除して制御できます。
- OpenAI など外部 API 呼び出しはリトライやフォールバック（失敗時は安全側の値）を行うよう設計されていますが、API キーや利用料には注意してください。
- validate_config により起動前に主要設定やファイルパスの存在有無、YAML のパース可否などをチェックできます。運用前に一度実行することを推奨します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys ディレクトリの主要ファイル／パッケージと役割の一覧です。

- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数・設定取得ユーティリティ（Settings クラス）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース + LLM）
  - monitoring/
    - monitoring_db.py — SQLite を用いる永続化層（テーブル初期化 / API）
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - monitoring_engine.py — 複数モニタの統括ループ
    - ...（TradeMonitor / AlertManager 等の他ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — 各種ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/ （実行関連コンポーネント; エンジン、ブローカーラッパ等）
    - (OrderManager, ExecutionEngine, BrokerFactory 等)

（注）上記はこの README 作成時点のコードベース抜粋に基づく一覧です。実際のリポジトリにはさらにファイル・サブパッケージが存在する可能性があります。

---

## よくある操作（例）

- .env を作って検証 → ペーパートレードで起動（例）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視をデフォルト間隔（60s）で起動
  - python -m kabusys.run_monitoring

- 監視を15秒間隔で起動（実験用）
  - MONITOR_POLL_INTERVAL=15 python -m kabusys.run_monitoring

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

以上。必要であれば README に以下を追加できます：

- requirements.txt / poetry のサンプル
- systemd / supervisor 用のサービスユニット例
- さらに詳細な API ドキュメント（各モジュールの関数説明）
- 運用手順（デプロイ、バックアップ、ログローテーション設定）

どの情報を追記したいか教えてください。