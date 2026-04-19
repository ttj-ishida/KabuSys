KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株の自動売買／リサーチ／監視を目的とした軽量なシステムコンポーネント群を含みます。
各コンポーネントは独立して動作するよう設計されており、実運用（live）・ペーパートレード（paper_trading）・開発（development）に対応しています。

本 README はソースコード（src/kabusys）を基に、日本語での利用手順・構成説明をまとめたものです。

目次
-----
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（主要）
- 使い方（実行コマンド）
- 主要コンポーネントの動作ポイント
- ディレクトリ構成
- 補足（ログ・停止フラグなど）

プロジェクト概要
----------------
KabuSys は以下のような責務を持つモジュール群で構成されています（抜粋）:

- ExecutionEngine: 発注・注文管理・リスク管理・約定・照合等の実行系
- Monitoring: システム稼働・注文状態・リスクの定期監視とアラート、Kill Switch の判断
- Portfolio: 候補選定・重み計算・ポジションサイズ計算、セクター調整などの純粋関数群
- Research: DuckDB を使ったファクター計算・特徴量探索・将来リターン計算など
- AI: OpenAI を用いたニュースセンチメント評価や市場レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト
- 設定補助: .env の対話式ウィザード（config_setup）/ 設定検証 CLI（validate_config）

主な機能
--------
- 発注エンジン（本番 / ペーパートレード切替）
- モニタリングループ（CPU/メモリ/Disk/プロセス監視、データ鮮度確認）
- Kill Switch：条件に応じて ExecutionEngine を停止するフラグを書き込む仕組み
- ポートフォリオ構築ロジック（候補選出、等配分・スコア配分、リスクベース）
- ポジションサイズ算出（単元丸め、投下資金制限、aggregate cap）
- DuckDB を用いたファクター計算（モメンタム・バリュー・ボラティリティ等）
- OpenAI を用いたニュースセンチメント（ai_scores）・レジーム判定
- ペーパートレード検証レポート出力（成功率、レイテンシ、稼働率判定）

必要条件
--------
- Python 3.9+
- 推奨パッケージ（一部必須）
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（config の検証で利用するが必須ではない）
- SQLite は標準ライブラリで利用
- その他: ネットワーク接続（kabuステーション / OpenAI 利用時）

インストール（例）
-----------------
1. リポジトリをクローン / 展開
2. 仮想環境作成と有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要ライブラリをインストール（例）
   - pip install duckdb psutil openai pyyaml

セットアップ手順（推奨ワークフロー）
----------------------------
1. .env を作成（対話式ウィザードを推奨）
   - python -m kabusys.config_setup
     - J-Quants / kabu API のトークンなどを入力します。
     - .env は生成されます。絶対に Git にコミットしないでください。

2. 設定検証
   - python -m kabusys.validate_config
     - --strict をつけると警告も失敗扱いになります。

3. 必要なディレクトリを作成（ログ・データ等）
   - mkdir -p data logs

主要環境変数（抜粋）
--------------------
（環境変数の多くは .env に記載します。ここは主要項目の要約）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI を用いる機能で必要
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant | partial | never | reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動消去するか（0/1、本番では 0 推奨）
- PID_FILE_PATH, KILL_FLAG_PATH — PID / kill flag ファイルパス（デフォルトは data/ 以下）

使い方（実行コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番DBと完全分離）
    - 起動時にプロセス優先度を high に設定します（psutil を利用）
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します
    - 実行中に data/execution.pid を利用して PID 書き込みが行われます

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（監視 DB）を使用します
  - 停止は data/stop_requested.flag ファイルの作成で行います（検知するとループ終了）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH も利用可

- AI / リサーチ API は Python モジュール経由で利用
  - 例（ニューススコアを付ける）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, date(2026,4,1), api_key=os.environ["OPENAI_API_KEY"])
  - 例（レジームスコア）:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, date(2026,4,1), api_key=...)

主要コンポーネントの動作ポイント
------------------------------
- Logging
  - kabusys.utils.logging_setup.setup_logging(app_name="execution"|"monitoring")
  - 標準出力（stdout）と logs/<app_name>.log（日次ローテート）へ出力
  - デフォルトログディレクトリ: logs/

- Kill Switch / Stop Flags
  - KillSwitch は監視結果に応じて KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込むことで Execution を停止させる
  - Execution/Monitoring の実行ループは data/stop_requested.flag を見て終了する
  - Execution は起動時に KILL_FLAG_CLEAR_ON_START==1 なら kill.flag を自動でクリアする設定が可能（本番では無効推奨）

- データベース
  - DuckDB: 分析／リサーチ用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視ログ・トレードログ（デフォルト data/monitoring.db）
  - Paper trading 用 SQLite は paper_trading 環境で分離（data/paper_trading.db）

- プロセス優先度・CPU affinity
  - 実行エントリは起動時に set_process_priority("high") を呼び出します（psutil 必須）
  - 実行環境依存で失敗した場合は警告ログを出し続行

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）です。実際のリポジトリは src/ にパッケージが存在します。

- src/kabusys/
  - __init__.py                — パッケージ初期化（__version__）
  - config.py                  — 環境変数読み込み・Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py         — monitoring 用 SQLite テーブル定義・永続層
    - monitoring_engine.py     — 各モニタの統合ループ
    - system_monitor.py        — CPU/MEM/DISK/データ鮮度監視
    - trade_monitor.py         — （注文ログ等の監視：ソース参照）
    - risk_monitor.py          — ドローダウン・ポジション制限の監視
    - kill_switch.py           — kill.flag の書き込みロジック
    - alert_manager.py         — （アラート送信の統合）
  - execution/
    - execution_engine.py      — ExecutionEngine 中核（run_session 等）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - broker_factory.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py         — ログ初期化
    - process_priority.py      — プロセス優先度設定
  - data/                      — デフォルトで data/ に DB・フラグ等を置く想定（作成してください）
  - logs/                      — ログ出力先（デフォルト）

補足（運用上の注意）
-------------------
- .env の管理は慎重に:
  - シークレット（トークン・パスワード）は絶対にリポジトリにコミットしないでください
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って自動クリアしてしまうのを防止）
- Monitoring は sqlite_path（監視 DB）を常に使用します。環境にかかわらず本番監視 DB を参照する設計になっています（要注意）
- ペーパートレードは本番 DB と分離されるよう実装されています（PAPER_TRADING_SQLITE_PATH）
- OpenAI を利用する機能は API のレート制限やエラー時にリトライ・フォールバックのロジックがありますが、API キー・課金ポリシーには注意してください
- DuckDB に対する executemany のバージョン依存などの互換性を考慮した実装箇所があります（古い DuckDB での注意）

よくあるコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースから主要な利用法・設計方針を簡潔にまとめたものです。各モジュール（execution/*, monitoring/*, ai/*, research/*）には詳細な docstring が含まれているため、必要に応じてソースを参照してください。運用前に必ず python -m kabusys.validate_config で設定を検証してください。