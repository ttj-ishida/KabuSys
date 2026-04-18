# KabuSys

日本株向け自動売買システムの一部を切り出した Python コードベースの README（日本語）。

この README はリポジトリ内の主要スクリプト・モジュールを参照して作成しています。実行・運用にあたっては必ず `python -m kabusys.validate_config` などで設定検証を行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 主要環境変数（抜粋）
- プロジェクトディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買（ExecutionEngine）・監視（Monitoring）・リサーチ／ファクター計算・AI（ニュースセンチメント・レジーム判定）等のコンポーネントを含むシステムです。
- 本リポジトリには、起動スクリプト、環境設定ウィザード、設定検証ツール、監視/リスク管理、ポートフォリオ構築、リサーチ、AI 関連モジュール（OpenAI を利用）などが実装されています。
- 設定は .env ファイル（または環境変数）で管理。Paper Trading（ペーパートレード）用に発注/DB を本番と分離できます。

主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）。
- 設定管理
  - config_setup.py: .env を対話式に作成 / 更新するウィザード。
  - validate_config.py: .env と config/*.yaml の静的検証ツール。--strict オプションあり。
- 監視・リスク
  - monitoring/*: system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db など。監視ログは SQLite に永続化。
  - Kill Switch: 条件（ドローダウンやポジション上限など）で data/kill.flag を生成し ExecutionEngine に停止指示を出す仕組み。
- 発注／実行（概念）
  - execution/*: ブローカーファクトリ、ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler（詳細は該当モジュール参照）。
- ポートフォリオ構築
  - portfolio/*: 候補抽出、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群。
- リサーチ
  - research/*: ファクター計算（mom/value/volatility）、将来リターン、IC 計算、統計サマリー等（DuckDB を利用）。
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事のセンチメントを OpenAI でスコア化し ai_scores に保存。
  - ai/regime_detector.py: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成し market_regime を判定。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト（SQLite を参照）。

セットアップ手順（簡易）
1. Python 環境
   - Python 3.9+ を推奨（プロジェクト要件に合わせて調整してください）。
   - 仮想環境を作成することを推奨（venv / pyenv-virtualenv 等）。

     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows

2. 必要パッケージのインストール（最低限）
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML 検証オプションのため任意）

   例:

     pip install duckdb psutil openai PyYAML

   （プロダクションでは requirements.txt を作成して管理してください）

3. .env の作成
   - 対話式ウィザードで初期 .env を作成:

     python -m kabusys.config_setup

   - ウィザード実行後、設定内容を確認して .env に保存してください。

4. 設定検証
   - 設定が正しいかを検証:

     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告も失敗扱い

5. DB / ディレクトリ
   - デフォルトでは以下のファイル/ディレクトリが利用されます（必要に応じて .env で上書き）:
     - data/monitoring.db (SQLite, 監視ログ)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/kabusys.duckdb (DuckDB)
     - logs/ (ログファイル)
   - これらは起動時に自動作成される場合がありますが、アクセス権等を事前に確認してください。

使い方（コマンド例）
- 環境変数を設定（例: bash）

  export KABUSYS_ENV=development
  export LOG_LEVEL=INFO
  export JQUANTS_REFRESH_TOKEN=...
  export KABU_API_PASSWORD=...
  export OPENAI_API_KEY=...

- .env を使う場合は config_setup で作成するか環境変数を .env に記述。

- 実行エンジン起動（本番/ペーパーいずれでも同じコマンド）:

  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて paper_trading.db に記録します（本番 DB と分離）。

- 監視プロセス起動:

  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は常に本番 sqlite_path を使用する実装になっています（設定に注意）。

- 設定検証（繰り返し）:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定

停止・Kill スイッチ等
- 停止フラグ（停止要求）:
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して安全停止します（これらのスクリプトはいずれもこのファイルを監視）。
- Kill Switch（監視側からの強制停止）:
  - monitoring の KillSwitch は data/kill.flag を書き込み、ExecutionEngine に対して発注停止を促します。
  - ExecutionEngine は Settings.kill_flag_path（デフォルト: data/kill.flag）を参照して挙動を制御します。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs/）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか：0/1、デフォルト: 0）

ディレクトリ構成（主要ファイルと簡単な説明）
- src/kabusys/
  - __init__.py: パッケージ定義、バージョン
  - config.py: 環境変数/.env 自動ロードと Settings クラス（設定取得）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 設定検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート
  - utils/
    - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ローテーションファイル）
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py: 監視用 SQLite 永続化 API（テーブル定義・操作）
    - monitoring_engine.py: 各 Monitor を束ねるエンジン
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス状態のチェック
    - risk_monitor.py: ドローダウン・ポジション数監視
    - trade_monitor.py (存在する想定): 発注ログ・約定の整合性監視（コード参照）
    - kill_switch.py: kill.flag の生成・評価ロジック
    - alert_manager.py (存在する想定): LINE などへの通知管理
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など（発注系）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数計算（単元丸め、リスク制限）
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: momentum/value/volatility の計算（DuckDB）
    - feature_exploration.py: 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py: ニュースセンチメント（OpenAI）
    - regime_detector.py: レジーム判定（ETF MA + マクロセンチメント）
  - data/ (既定のデータ/ログ配置を想定)
    - monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid など

注意事項 / 運用上のポイント
- 本番（KABUSYS_ENV=live）では設定の取り扱いに細心の注意を払ってください（APIキーやパスワードを公開しない、kill flag 設定等）。
- OpenAI 等外部 API を使う機能は API キーとレート制限に依存します。レート制限やエラー時のリトライ・フォールバックが実装されていますが、運用監視を推奨します。
- monitoring は監視用 SQLite を使い永続化します。DB のバックアップや権限、I/O 性能も運用上重要です。
- logs/ 以下にアプリ名ごとの日次ローテートログが出力されます（設定: kabusys.utils.logging_setup）。
- Paper Trading は発注部分を本番 DB と分離しているため、設定次第で安全に検証可能です。

問い合わせ / 参照
- 各モジュールの docstring に設計方針・使用例が記載されています。特に AI / research / portfolio 関連は実装ノートが多く含まれますので参照してください。
- 実運用前に config_setup → validate_config → 少量のローカルテスト（paper_trading モード）で動作確認を行ってください。

以上。必要に応じて README を拡張（依存ライブラリのバージョン、CI / デプロイ手順、DB スキーマの詳細、テストの実行方法など）しますのでリクエストしてください。