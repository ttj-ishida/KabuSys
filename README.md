# KabuSys

日本株向け自動売買システムのリポジトリ（コードスニペットから作成された README）。  
この README はローカル開発 / ペーパートレード / 本番運用での起動、設定、主要機能の概要をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するコンポーネント群です。主な役割は以下のとおりです。

- データパイプライン（価格データ / 財務データなど）を参照してファクターを計算
- シグナルに基づく銘柄選定・配分・株数決定（ポートフォリオ構築）
- ExecutionEngine による発注制御（paper_trading では MockBroker を使用）
- 監視コンポーネント（System / Trade / Risk）と Kill Switch による安全停止
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI を利用）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、検証ツール、レポート生成）

設計方針として「本番環境のDB/発注を分離」「ルックアヘッドバイアスを避ける」「API失敗時はフェイルセーフで継続」などが採用されています。

---

## 主な機能一覧

- 環境/設定管理
  - .env 自動読み込み / 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 実行・監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB を利用
  - Monitoring（run_monitoring.py）
    - 定期的に System / Trade / Risk をチェックしアラート・Kill Switch を評価
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
- 監視永続化層
  - SQLite ベースの monitoring DB 管理（monitoring_db.py）
- ポートフォリオ構築
  - 候補選定・重み計算・ポジションサイズ決定（portfolio/）
  - セクター制約・レジーム乗数などのリスク調整
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等を DuckDB 経由で計算（research/）
  - 将来リターン・IC 計算・統計サマリ等
- AI（OpenAI）連携
  - ニュースのセンチメントスコア（news_nlp）
  - マーケットレジーム判定（regime_detector）
  - OpenAI API キー（OPENAI_API_KEY）が必要
- ツール
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

---

## セットアップ手順（開発環境）

1. Python 仮想環境作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール  
   （requirements.txt がない場合は主な依存を手動でインストール）
   - pip install duckdb psutil openai PyYAML

   注:
   - sqlite3 は標準ライブラリとして含まれます。
   - PyYAML は config/*.yaml の構文チェック時に使用されます（任意）。

3. プロジェクトルートに `.env` を作成する（推奨: config_setup を利用）
   - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記の最低限の環境変数を参照）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にする場合: python -m kabusys.validate_config --strict

5. データディレクトリ・ログディレクトリの作成（必要に応じて）
   - デフォルト DB / ログの場所:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
     - SQLite (監視): data/monitoring.db（SQLITE_PATH）
     - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
     - ログディレクトリ: logs/（環境変数 LOG_DIR で変更可）

---

## 必須 / 代表的な環境変数

最低限設定が必要なもの（validate_config によるチェック項目）：

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — AI 機能を使用する場合に必要
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）（任意）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH — DB ファイルパス（任意）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知設定（任意）

.env の例（最小）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env はリポジトリにコミットしないでください。

---

## 使い方（起動と各種コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も FAIL）: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用
    - 起動時に data/execution.pid を書き込み、停止は data/stop_requested.flag を置くことで受け付ける

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定（デフォルト 60）
    - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用
    - 停止はプロジェクト data/stop_requested.flag ファイルを作る（多くのスクリプトがこれを監視）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

- AI 機能（ニュースセンチメント / レジーム判定）
  - internal API 呼び出し: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - 実行には OPENAI_API_KEY が必要

- ログ
  - logs/<app_name>.log（app_name は "execution", "monitoring" 等）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

- Kill Switch / 停止フラグ
  - KillSwitch は条件に応じてデータディレクトリ（Settings.kill_flag_path デフォルト data/kill.flag）にファイルを書き、ExecutionEngine に停止シグナルを送ります
  - 手動停止には data/stop_requested.flag を作成すると run_* スクリプトがループを抜けます

---

## 注意点 / 運用上のヒント

- paper_trading 環境は本番の発注と完全に分離されます。PAPER_TRADING_SQLITE_PATH を利用してください。
- OpenAI API を使用する部分は外部課金が発生します。API キーの取り扱いに注意してください。
- process priority の設定（utils/process_priority.set_process_priority）は一部 OS で権限が必要です。権限不足の場合は警告が出てスキップされます。
- ログディレクトリや data ディレクトリの作成に失敗するとファイル出力が無効化され、コンソールのみでの出力になります。
- DuckDB / SQLite への書き込み時は排他や executemany の仕様に注意（コード内に互換性考慮の実装あり）。
- 本番運用（KABUSYS_ENV=live）の場合、LINE通知や Kill Switch の設定を慎重に確認してください（validate_config でチェック有り）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なソース配置（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring polling 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py               — SQLite 監視 DB レイヤ
    - monitoring_engine.py           — 各 Monitor の統括
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               — （取引監視: ファイルに未掲載だが存在想定）
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - alert_manager.py               — （アラート送信: ファイルに未掲載だが想定）
  - execution/
    - execution_engine.py            — 実行エンジン（EngineConfig, run_session 等）
    - broker_factory.py              — BrokerClientFactory（Mock / Live 切替）
    - order_manager.py
    - order_repository.py
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
    - news_nlp.py                     — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py              — マーケットレジーム判定
  - data/ (運用時に作成)
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db, paper_trading.db, etc.
  - logs/ (ログ出力先)

（注）一部ファイルはこの README 作成時にスニペットで公開されている範囲に基づき抜粋しています。実際のプロジェクトではさらに多くのモジュールや補助スクリプトが存在する可能性があります。

---

## 追加情報・貢献

- 設定や DB スキーマの変更を行う場合は validate_config や monitoring_db.init_monitoring_db のマイグレーションロジックを参照してください。
- AI 関連の外部呼び出しは単体テストでモックしやすいよう関数化されています（_call_openai_api を差し替え可能）。
- バグ報告や機能提案は Issue を通じてお願いします。

---

以上。運用や導入時に不明点があれば、該当スクリプト（config.py / run_*.py / monitoring/* / execution/*）のドキュメント文字列やログ出力を参照してください。