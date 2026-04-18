KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのミニマル実装です。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine: 発注ロジック・注文管理（本番 / ペーパートレード対応）
- Monitoring: システム監視・データ鮮度・リスク監視・Kill Switch
- Research: DuckDB ベースのファクター計算 / 特徴量解析
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- Portfolio Construction: 候補選定、重み計算、ポジションサイズ決定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード / 検証ツール
- ツール: ペーパー取引検証レポート生成

主な機能
--------
- 環境ごとに本番 / ペーパーを分離（KABUSYS_ENV により動作切替）
- 発注処理のリスク管理（ポジション上限・ドローダウン監視・送信/成立率集計）
- MonitoringDaemon：定期ポーリングで system/trade/risk を監視し、Kill Switch を発動
- DuckDB を使ったオンメモリ／分析用クエリ（prices_daily / raw_financials 等を想定）
- OpenAI を用いたニュースセンチメント評価（gpt-4o-mini など）
- ペーパートレード用の独立 DB と検証レポート生成
- ログはコンソール（stdout）と日次ローテートされたファイル（logs/*.log）に出力

必要要件
--------
- Python 3.10+
- 主要ライブラリ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（任意、config 検証で使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

セットアップ手順
----------------
1. レポジトリをクローン
   - git clone <repo-url>
   - (本コードは src/ 配下にパッケージを置く構成を想定)

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従い J-Quants / kabuステーション パスワードなど必須項目を入力します。
   - .env は Git にコミットしないでください（機密情報含む）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ作成（通常は自動作成されますが手動で用意する場合）
   - mkdir -p data logs

基本的な環境変数（代表）
------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方 / 実行方法
-----------------

実行系（ExecutionEngine）
- 本番 / ペーパートレードを切り替えるには KABUSYS_ENV を設定します。
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行はバックグラウンドで起動して PID ファイル（data/execution.pid）を生成します。
- 停止要求:
  - run_execution はプロジェクトルートの data/stop_requested.flag を監視しています。停止したい場合は空ファイルを作成してください:
    - touch data/stop_requested.flag
  - また監視コンポーネント（KillSwitch）は data/kill.flag を書き込み、ExecutionEngine に停止を促します。kill.flag は自動生成または手動で削除してください。

監視（Monitoring）
- 監視デーモンの起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔:
  - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
- 監視は MonitoringDB（SQLite）に永続化します（monitoring モジュールが init を実行）。

ツール類
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

ログ
----
- コンソール出力（stdout）およびファイル: logs/<app_name>.log（日次ローテート、30日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。

重要な挙動メモ
-------------
- run_monitoring は MONITOR_POLL_INTERVAL（デフォルト 60 秒）でモニタリングループを回します。
- run_monitoring の監視 DB 接続は「監視用 sqlite_path（Settings.sqlite_path）」を常に使用します（環境に依存せず本番用 path を参照する実装）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と完全分離します。
- KillSwitch はリスク条件（ドローダウン・ポジション上限等）を満たしたときに data/kill.flag を書いて ExecutionEngine を停止させます。kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START で制御（開発時のみ注意）。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys/ 以下の主なファイル / ディレクトリです（フルツリーは repo を参照してください）。

- src/kabusys/
  - __init__.py                 — パッケージ定義（バージョン等）
  - config.py                   — 環境変数 / Settings 管理
  - config_setup.py             — 対話式 .env 生成ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト

  - execution/                   — 発注エンジン関連（broker, engine, order_manager...）
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py         — システム・データ鮮度チェック
    - trade_monitor.py          — 注文ログ/約定異常検出（省略ファイルあり）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - monitoring_engine.py      — 3つの Monitor を束ねる
    - kill_switch.py            — Kill Switch 実装
    - alert_manager.py          — アラート送信（LINE 等／実装に依存）
  - portfolio/
    - portfolio_builder.py      — 候補選定 / 重み計算
    - position_sizing.py        — 発注株数計算
    - risk_adjustment.py        — セクター制限・レジーム乗数
  - research/
    - factor_research.py        — モメンタム / バリュー / ボラティリティ計算（DuckDB 参照）
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py               — ニュースセンチメントスコア算出（OpenAI）
    - regime_detector.py        — マクロ + MA200 を用いた市場レジーム判定（OpenAI）
  - monitoring/monitoring_db.py — 監視 DB 初期化と DB API
  - tools/
    - paper_verification_report.py — ペーパートレード結果の検証レポート生成
  - utils/
    - logging_setup.py          — ロギング初期化ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上のヒント
--------------------------
- .env に機密情報（API トークン等）を保存するため、絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にすることを推奨します（誤って Kill Switch を消さないように）。
- monitoring は本番の SQLite パスを常に参照する実装です。監視 DB と発注 DB を分離したい場合は設定を確認してください。
- OpenAI を使うモジュールは API の障害を考慮してフェイルセーフ処理（0.0 フォールバックやスキップ）を行いますが、APIキーや利用制限に注意してください。
- ローカルでの開発は KABUSYS_ENV=development にして、必要な外部 API 呼び出しをモックすることを推奨します。

追加情報
--------
- コード内の docstring とモジュールコメントに詳細な設計意図や注意点が記載されています。各機能を改修・拡張するときは docstring を参照してください。
- YAML 設定ファイル（config/*.yaml）を使用する設計箇所があります。PyYAML が無ければ検証はスキップされますが、実運用ではインストールしておくと良いです。

問題・改善提案
--------------
README や設定フローに不足している点があれば教えてください。必要に応じて起動例や systemd / supervisor 用のサービス定義、docker-compose 例なども追加できます。