KabuSys — 日本株自動売買システム（README）
=====================================

概要
----
KabuSys は日本株の自動売買を想定したシステム群です。システムは以下の主要コンポーネントで構成されています。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（run_execution.py）
- Monitoring: システム稼働状況・データ鮮度・注文状態・リスクを監視する（run_monitoring.py）
- Portfolio / Research: 銘柄選定・配分・ファクター計算などのポートフォリオ構築・調査ロジック
- AI モジュール: ニュースセンチメントや市場レジーム判定（OpenAI を利用）
- ユーティリティ: ロギング設定・プロセス優先度設定・設定ウィザード等

このリポジトリはロジックをモジュール化しており、実行スクリプトを通じて起動します。ペーパートレーディング用の完全分離 DB や、Kill Switch による安全停止機構などを備えています。

主な機能
--------
- 実行エンジン（ExecutionEngine）
  - ブローカークライアント（実運用 / ペーパートレード切替）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager / Reconciler）
- 監視（Monitoring）
  - システムリソース（CPU/MEM/Disk）・プロセス生存・データ鮮度の監視
  - 注文滞留・約定異常・リスク（ドローダウン・ポジション数）監視
  - Kill Switch（条件達成時に data/kill.flag を作成して Execution を停止）
  - ログ永続化（SQLite：monitoring.db）
- ポートフォリオ構築（pure functions）
  - 候補選定、等金額 / スコア加重配分、リスク調整、ポジションサイズ計算
- リサーチ / ファクター算出（DuckDB を用いる）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）など
- AI（OpenAI）
  - ニュースセンチメント（news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定補助
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

前提（依存）
------------
主な Python ライブラリ（プロジェクトにより異なる）:
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）
必要に応じて pip 等でインストールしてください。例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン／展開する
   - プロジェクトルートに移動します（README があるディレクトリ）。

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. 環境変数（.env）を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要なオプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール利用時）
     - LOG_LEVEL（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、デフォルト 0）
   - .env の雛形は config_setup が生成します。生成後は:
     python -m kabusys.validate_config
     で設定チェックを推奨（--strict を付けると警告も失敗扱い）。

5. データディレクトリを作成
   - デフォルトの DB/logs などの親ディレクトリがない場合、起動時に自動作成されますがあらかじめ作成しておくと良いです。
   - 例: mkdir -p data logs

使い方（実行）
--------------
起動スクリプトはモジュールとして実行できます。

- 監視ループ（Monitoring）
  - デフォルトのポーリング間隔は 60 秒。
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（正の整数）。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
  - 実行:
      python -m kabusys.run_monitoring
  - 停止: プロセスを Ctrl+C するか、プロジェクトルート/data/stop_requested.flag ファイルを作成すると監視ループは検出して終了します。

- 実行エンジン（Execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB から完全分離）。
  - 実行:
      python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag ファイルを作成すると実行中のエンジンに停止要求が送られます（起動直後に既にフラグがある場合は起動を行いません）。
    - Kill Switch（監視側の条件で自動的に作成される data/kill.flag）もあります。kill.flag は Settings.kill_flag_clear_on_start=1 の場合に起動時にクリアされる設定がありますが、本番では 0 を推奨します。

- 設定検証
    python -m kabusys.validate_config
  - 警告も厳格に扱いたい場合:
    python -m kabusys.validate_config --strict

- .env 作成（対話ウィザード）
    python -m kabusys.config_setup

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB パスを指定できます。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
  - paper_trading: ExecutionEngine は mock ブローカーを使用し、専用 SQLite に記録
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- OPENAI_API_KEY (AI モジュールを使う場合に必須)
- LOG_LEVEL (default: INFO)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒。デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1。1 は起動時に kill.flag を自動クリアする)

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（30日保持）。
- setup_logging() により stdout とファイル出力が統合されます。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。

安全停止 / Kill Switch
---------------------
- 手動停止フラグ: project_root/data/stop_requested.flag
  - run_monitoring/run_execution はこのファイルの存在を監視し、検出時に終了／停止処理を行います。
- Kill Switch: monitoring 側の条件（ドローダウン超過やポジション数超過）で data/kill.flag が作成され、ExecutionEngine を停止させます。
  - KillSwitch クラスは flag の冪等な書き込み・クリア操作を提供します（clear()）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - config.py               — 環境変数 / Settings クラス（デフォルト値・検証含む）
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py    — 市場レジーム判定（ma200 + LLM）
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み計算
    - position_sizing.py    — 発注株数算出（単元丸め・集約 cap）
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — Momentum/Volatility/Value の計算（DuckDB）
    - feature_exploration.py— 将来リターン / IC / サマリー
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成 / 永続化層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文状態監視（滞留/約定異常等）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag の管理
    - monitoring_engine.py  — 各 Monitor を束ねる
    - alert_manager.py      — （通知処理、LINE 等の実装想定）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体
    - broker_factory.py     — ブローカークライアント生成（実運用 / mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - data/ (ランタイムで生成)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid など

補足 / 注意点
-------------
- Monitoring は Settings.sqlite_path（本番監視 DB）を使用します。環境にかかわらず監視ログは本番用の DB に残る点に注意してください（run_monitoring のドキュメント参照）。
- ExecutionEngine は KABUSYS_ENV=paper_trading のときに paper_sqlite_path を使用して DB 分離します。
- OpenAI を使う AI モジュールは API 呼び出しに失敗してもフェイルセーフで継続する設計ですが、API キーの設定やリトライ挙動には注意してください。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定して .env 自動ロードを無効化できます（テスト等で有用）。

トラブルシューティング（簡易）
-----------------------------
- .env を作成したが Settings が環境変数を読み取らない:
  - プロジェクトルート（.git または pyproject.toml）が正しく検出されない場合は自動ロードをスキップします。手動で export するか KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- ログファイルが作られない:
  - logs/ ディレクトリの作成権限やパスを確認。ログディレクトリに書き込みできない場合はコンソール出力のみになります（警告が標準エラーに出ます）。
- ペーパートレードのレポートが DB を見つけない:
  - tools/paper_verification_report は PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB パスを指定できます。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys/__init__.py に __version__ = "0.1.0" としています。
- ライセンス情報はリポジトリのトップレベルに従ってください（本 README には含めていません）。

最後に
------
この README はコードベースの主要点をまとめたものです。詳細な実装や追加設定は各モジュールの docstring / ソース内コメントを参照してください。必要であれば README に追記したい項目（例: デプロイ手順、systemd ユニット例、Docker 化手順など）を教えてください。