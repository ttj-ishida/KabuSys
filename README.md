# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントではプロジェクトの概要、主な機能、セットアップ手順、起動/利用方法、ディレクトリ構成を日本語でまとめます。

注意: ここでの説明は src/kabusys 以下のコードベースに基づいています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な機能は次の通りです。

- 発注エンジン（ExecutionEngine）による注文管理・リスク管理・ブローカー連携
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- Paper Trading（ペーパートレード）用分離 DB と MockBroker のサポート
- ファクター計算・特徴量探索などの研究用モジュール（DuckDB ベース）
- ニュースの NLP（OpenAI）を用いたセンチメント評価と市場レジーム判定
- .env の対話式セットアップ、設定検証ツール、検証レポート生成ツール
- 統一されたログ設定ユーティリティとプロセス優先度設定ユーティリティ

設計方針として、ルックアヘッドバイアス防止、フェイルセーフ（API失敗時のスキップやフォールバック）、永続化は SQLite / DuckDB を使用する点が特徴です。

---

## 機能一覧（抜粋）

- 環境設定
  - .env 対話ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- 実行／監視
  - 実行エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の時は MockBroker を使用し data/paper_trading.db を利用
    - 停止フラグ: data/stop_requested.flag の検出で安全停止
  - 監視ループ起動: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path を使用して記録
- 監視・キルスイッチ
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - 異常時に data/kill.flag を書き込み ExecutionEngine を停止させる KillSwitch
  - 監視データは SQLite（デフォルト: data/monitoring.db）に永続化
- 研究・分析
  - ファクター計算: calc_momentum / calc_volatility / calc_value（DuckDB 経由）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等
- AI（OpenAI）関連
  - ニュースセンチメント: kabusys.ai.news_nlp.score_news（gpt-4o-mini を想定）
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
  - API キーは OPENAI_API_KEY で指定（引数でも可）。API フェイル時はフェイルセーフで継続。
- 運用補助
  - ロギング共通設定: kabusys.utils.logging_setup.setup_logging
    - stdout と 日次ローテーションファイル（logs/<app_name>.log）を設定（30日保持）
  - プロセス優先度 / CPU affinity ユーティリティ: kabusys.utils.process_priority

---

## セットアップ手順（ローカル）

1. リポジトリをクローンしてルートへ移動
   - 仮にプロジェクトルートが存在する想定（.git または pyproject.toml）

2. Python 環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 少なくとも以下が必要（機能に応じて）:
     - duckdb, psutil, openai, (PyYAML は validate_config の YAML 検証で任意)
   - 例: pip install duckdb psutil openai PyYAML

4. .env の準備
   - 対話式ウィザードを実行して .env を初期作成:
     - python -m kabusys.config_setup
   - 自動読み込み: デフォルトでプロジェクトルートの `.env` と `.env.local` を読み込みます。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

6. データディレクトリ作成（必要に応じて）
   - logs/、data/ などのディレクトリを作成しておくとよい（logging_setup が自動作成も行いますが許可周りで失敗する場合がある）

7. OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時にキーを渡す

---

## 使い方（主要コマンド）

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag を削除しておく（停止フラグが立っていると起動しません）
  - paper_trading モード:
    - KABUSYS_ENV=paper_trading を .env に設定すると MockBrokerClient を使用し、data/paper_trading.db に書き込みます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL 環境変数（秒）を設定（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: data/stop_requested.flag を作成するとループが検知して安全終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db

運用に便利なファイル/フラグ:
- data/stop_requested.flag — 実行中の run_* スクリプトが検知して安全終了
- data/kill.flag — KillSwitch が発動した際に書き込まれる（ExecutionEngine 停止要求）
- data/execution.pid — ExecutionEngine の PID を記録するファイル（既定）
- logs/<app_name>.log — 日次ローテートログ

---

## 環境変数（主なもの）

必須（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

運用・オプション
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの執行モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

設定は .env または環境変数で与えます。Settings クラス（kabusys.config.Settings）がラップしています。自動ロードはプロジェクトルートの .env/.env.local（OS 環境変数が優先）です。

---

## 運用メモ / 注意点

- run_monitoring は監視ログ用に本番 sqlite_path を使用します（KABUSYS_ENV にかかわらず）。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- KillSwitch が kill.flag を書き込むと ExecutionEngine に停止シグナルが出ます（部分失敗時でも他のコードのスコアを保護するロジックあり）。
- OpenAI 呼び出しは再試行ロジックとパース検証を行いますが、APIキー未設定時はエラーになるため注意。
- ログは stdout とファイルの両方へ出力されます。ファイル出力は logs/ 配下に日次ローテート（30日保持）で保存されます。ログディレクトリ作成に失敗した場合はコンソールのみになります。

---

## ディレクトリ構成（抜粋）

次は src/kabusys 以下の主なファイル・フォルダです（実際のツリーは多少異なることがあります）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings（自動 .env 読み込み）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - research/
    - factor_research.py      — モメンタム・バリュー・ボラティリティ等の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化・CRUD）
    - monitoring_engine.py    — 各 Monitor 統合ループ
    - system_monitor.py       — CPU/メモリ/ディスク・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py*       — （参照あり、未掲示）アラート送信管理
    - trade_monitor.py*       — （参照あり、未掲示）注文ログ監視
  - execution/
    - execution_engine.py*    — ExecutionEngine 本体（参照あり）
    - broker_factory.py*      — ブローカークライアントファクトリ（Mock/実ブローカー切替）
    - order_manager.py*       — 注文管理
    - order_repository.py*    — 注文履歴永続化
    - reconciler.py*          — ブローカーと履歴の整合
    - risk_manager.py*        — 発注前リスクチェック
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - data/  — 実行時に使用する SQLite / pid / flag 等（プロジェクトルート直下の data/ を想定）
  - logs/  — ログファイル出力先（デフォルト）

（* はこの README に含められたコードスニペットで参照されているが、全文はここに掲示されていないモジュール）

---

## よくある運用フロー（例）

1. 初期設定
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. Paper Trading での動作確認
   - .env で KABUSYS_ENV=paper_trading に設定
   - python -m kabusys.run_execution
   - 取引ログは data/paper_trading.db に記録される
   - 実行後に検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

3. 監視プロセスの起動（別プロセス/ホスト）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL を適宜調整

4. 異常時
   - kill.flag が書かれると ExecutionEngine が停止する
   - stop_requested.flag を作成すると run_* のループが安全に終了する

---

README に記載しているのは主要な使い方とモジュールの概要です。コードにより具体的な実装や追加オプションがありますので、詳細は各モジュールの docstring コメントを参照してください。必要であれば README に起動例や運用チェックリストの追記、あるいは要求されたサンプル .env の雛形も作成します。どの情報を追加希望か教えてください。