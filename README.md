KabuSys — 日本株自動売買システム
======================

このリポジトリは日本株向けの自動売買／リサーチ／監視ツール群を収めたパッケージです。  
ここに含まれるモジュールは取引実行エンジン（ExecutionEngine）／監視（Monitoring）／ポートフォリオ構築／ファクター計算／AI を用いたニュース解析など、実運用を見据えた機能群で構成されています。

本 README ではプロジェクト概要・機能一覧・セットアップ手順・基本的な使い方・ディレクトリ構成を日本語でまとめます。

要件
----
- Python 3.10+
- 必要ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
  - （その他: sqlite3 は標準ライブラリ）
- 実行環境に応じて追加の依存が必要になることがあります。requirements.txt がある場合はそれを使用してください。

プロジェクト概要
------------
KabuSys は次の機能を備えた日本株自動売買システムのライブラリ兼実行スクリプト集合です。

- ExecutionEngine: 発注／オーダー管理／リスク管理／注文再帰（reconciler）等を担う実行エンジン（本番とペーパートレードを分離）
- Monitoring: システム稼働状況や取引ログを監視し、アラート生成や Kill Switch の発動を行う
- Portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限などのポートフォリオ構築ロジック（純粋関数群）
- Research: DuckDB を用いたファクター計算・特徴量解析ツール群
- AI: OpenAI を使ったニュースのセンチメント解析（news_nlp）／市場レジーム判定（regime_detector）
- Tools: ペーパートレードの検証レポート生成スクリプトなどのユーティリティ
- 設定管理 CLI: .env 対話式ウィザード（config_setup）・設定検証（validate_config）

主な機能一覧
------------
- 自動起動スクリプト:
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV によりペーパートレード DB を使用）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（定期的に system_status を記録）
- 設定管理:
  - config_setup.py — .env を対話的に作成/更新
  - validate_config.py — 環境変数や config/*.yaml の基本検証（--strict あり）
- 監視:
  - system_monitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス確認
  - trade_monitor / risk_monitor / monitoring_engine / kill_switch: 注文滞留・価格異常・ドローダウンなどの監視と Kill Switch 発動
  - monitoring_db: SQLite を用いた監視ログ永続化
- ポートフォリオ:
  - 候補選定、等重・スコア加重、リスクに基づく株数決定、セクター上限適用、レジーム乗数
- リサーチ:
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン・IC 計算、統計サマリー
- AI:
  - news_nlp: ニュース記事を集約して OpenAI に送りセンチメントスコアを ai_scores に書き込む
  - regime_detector: ETF（1321）MA とマクロニュースを組み合わせて market_regime を算出・書き込み
- ツール:
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・成功率・レイテンシなど）

セットアップ手順
----------------
1. リポジトリをクローンする／パッケージソースを取得する
   - 例: git clone <repo>

2. Python 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

   （依存はプロジェクト構成や利用機能により増減します。requirements.txt がある場合はそれを使ってください）

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視ログ）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用 DB）
     - LOG_LEVEL: DEBUG/INFO/...
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード約定モデル）
     - KILL_FLAG_CLEAR_ON_START: 0 or 1（本番では 0 推奨）

   - 自動 .env 読み込み:
     - このパッケージは起動時にプロジェクトルート（.git か pyproject.toml）を探索して .env/.env.local を自動読み込みします。
     - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. ディレクトリの準備
   - logs/ および data/ ディレクトリは自動生成されることが多いですが、必要に応じて権限や配置を確認してください。

基本的な使い方
------------

- 設定検証
  - python -m kabusys.validate_config
  - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

- ExecutionEngine（本番/ペーパー）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません（停止フラグ）。
    - エンジンは data/execution.pid に PID を書きます（設定で変更可能）。
    - 起動前に KILL_FLAG_CLEAR_ON_START=1 を設定していると既存の kill.flag を自動クリアする挙動になります（本番では推奨されません）。

- Monitoring（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を指定可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視テーブルに書き込みます（監視 DB は共有されることに注意）。
    - 停止は data/stop_requested.flag を作成するか Ctrl+C（KeyboardInterrupt）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- AI モジュール（ニューススコア等）
  - OpenAI API キー: OPENAI_API_KEY を環境変数で設定するか、各関数に api_key 引数を渡してください。
  - 例（Python REPL）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
  - AI モジュールは失敗フェイルセーフ設計（API 失敗時はスコアをスキップまたは 0.0 にフォールバックすることがあります）。

- ログ
  - logs/<app_name>.log に日次ローテーションでログが出力されます（デフォルト logs/）。LOG_DIR 環境変数で変更可能。
  - setup_logging() を各起動スクリプトで呼んで統一的に設定されます。

- Kill Switch / Stop フラグ
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に原因文字列を書き込み、ExecutionEngine を停止させるための仕組みです。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring/run_execution の外部停止トリガーとして用いられています。
  - KillSwitch.clear() を使うと kill.flag を削除できます（起動時のクリーンアップなどで使用）。

設定（主な環境変数まとめ）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- LOG_LEVEL: DEBUG|INFO|...
- LOG_DIR: ログ保存先ディレクトリ
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_PATH: data/kill.flag（上書き可）
- PID_FILE_PATH: data/execution.pid（上書き可）
- KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
-----------------------------
リポジトリ内にある主なモジュールと役割（src/kabusys を基点に抜粋）:

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース + LLM）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 層（表作成・読み書きユーティリティ）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度確認
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （取引監視; ファイル中に実装あり）
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py — （アラート送信。LINE 等の統合ポイント）
  - execution/
    - execution_engine.py — Execution エンジン（起動・セッション制御）
    - broker_factory.py — ブローカークライアントの生成（実/モック切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの主要コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定 / 集約制限
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - data/ (補助: pipeline, stats 等)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

利用上の注意
-----------
- 本システムは実際の発注機能を含むため、本番（KABUSYS_ENV=live）で動かす場合は環境変数・APIキー・kill flag の取り扱い・アクセス権限等を十分に確認してください。
- .env は機密情報（API トークンやパスワード）を含むため、Git 等のバージョン管理には絶対に含めないでください。
- ExecutionEngine はペーパートレードと本番で DB を分離する設計ですが、設定ミスにより本番 DB を参照する可能性があるため、validate_config を実行して環境設定を確認してください。
- AI（OpenAI）呼び出し部分は API 利用料が発生します。テスト時はモック化するか API キーを指定しない実行に注意してください。

よく使うコマンドまとめ
---------------------
- .env の作成／更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- SystemMonitor（監視）起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- REPL から機能を呼ぶ（例: AI スコア付与）:
  - python
    - from kabusys.ai.news_nlp import score_news
    - # DuckDB 接続オブジェクトを渡して score_news(conn, target_date, api_key=...)

サポート / 貢献
----------------
- バグ報告や改善提案は issue にて受け付けてください。
- 大きな変更はブランチを作成して Pull Request を送ってください。

以上が README の概要です。必要ならばインストール要件の具体的な requirements.txt、より詳細な運用手順（systemd/cron/コンテナ化例）、ユニットテストの実行方法などの追加ドキュメントも作成できます。どの項目を拡張しますか？