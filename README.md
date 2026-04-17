KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
本リポジトリは以下の主要機能群を含みます。

- 実行エンジン（ExecutionEngine）：発注、リスク管理、約定の追跡
- 監視（Monitoring）：プロセス・システム状態・注文異常・ドローダウン監視、Kill Switch
- 研究（Research）：ファクター計算、フォワードリターン、IC 評価など
- ポートフォリオ構築：候補選定、重み算出、ポジションサイジング、セクター制限
- AI 補助：ニュースを LLM でスコアリングし市場レジームや銘柄センチメントを算出
- ユーティリティ／ツール群：.env ウィザード、設定検証、Paper Trading レポート生成 等

主な特徴
--------
- 実運用（live）とペーパートレード（paper_trading）を明確に分離（paper_trading 用の専用 SQLite）
- DuckDB を用いた研究用テーブル（prices_daily / raw_financials 等）を前提にしたファクター計算
- OpenAI（gpt-4o-mini）を利用したニュース NLP（フェイルセーフ・リトライ実装）
- 監視→Kill Switch→ExecutionEngine 停止のフローによる安全ガード
- .env の対話式作成ツールと起動前検証 CLI

前提・依存ライブラリ（主なもの）
--------------------------------
（実行環境に合わせて適宜インストールしてください）
- Python 3.9+（型ヒントや pathlib を多用）
- duckdb
- psutil
- openai
- requests
- PyYAML（config の YAML 検証を行う場合に必要）
その他ユーティリティは requirements.txt を用意している場合はそちらからインストールしてください（本コード断片には requirements ファイルが含まれていません）。

セットアップ手順
----------------

1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトルートには .git または pyproject.toml がある想定です。

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai requests pyyaml

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を作成してください。
   - 自動読み込みを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合: python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルトで使用されるファイルは data/ 以下に配置されます（duckdb ファイル・sqlite 等）。
   - 必要に応じて .env でパスを上書きしてください（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）。

必須環境変数（最低限）
---------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能を利用する場合（ai モジュール・regime_detector 等）

主なオプション環境変数
---------------------
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1でクリア）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY — OpenAI API キー（AI 機能）

使い方（起動・実行）
-------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動は KABUSYS_ENV に依存：
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込み
    - live: 実際のブローカークライアントを使用（設定により）
  - 実行中は data/execution.pid が書かれ、停止は data/stop_requested.flag の作成で検知して安全に停止します。

- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒、デフォルト 60）。
  - 監視は常に本番用の sqlite_path を使用します（環境にかかわらず monitoring DB は同一）。
  - 停止は data/stop_requested.flag の作成で制御されます。

- .env の作成ウィザード
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定例: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数、なければ data/paper_trading.db。

停止・Kill Switch の扱い
-----------------------
- Monitoring 側が条件を満たした場合、KillSwitch が data/kill.flag を書き込みます。ExecutionEngine は kill.flag の存在を確認して停止を促される設計です。
- 手動で ExecutionEngine を停止するにはプロセスに SIGINT（Ctrl+C）を送るか、data/stop_requested.flag を作ると run_execution/run_monitoring は検知して終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定管理（.env 自動ロードロジック含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores への書き込み）
  - regime_detector.py — マーケットレジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化（schema 初期化・操作ラッパ）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — LINE 通知（push）
- execution/ (発注周り)
  - order_manager.py, order_repository.py, execution_engine.py, broker_factory.py, reconciler.py, risk_manager.py など（実行ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築ロジック）
- research/
  - factor_research.py, feature_exploration.py（DuckDB を用いたファクター計算・解析）
- tools/
  - paper_verification_report.py — Paper Trading の検証用レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

DB・スキーマ関連
-----------------
- init_monitoring_db(conn) が監視用 SQLite のスキーマ（system_status, trade_logs, positions, risk_logs, dashboard 等）を冪等に作成します。run_execution / run_monitoring 起動時に自動的に呼ばれます。
- DuckDB は prices_daily / raw_financials / raw_news 等の分析用テーブルを前提にした処理が多数あります。DuckDB ファイルは DUCKDB_PATH で指定します。

運用上の注意
------------
- 本番環境（KABUSYS_ENV=live）では kill.flag・KILL_FLAG_CLEAR_ON_START の設定に特に注意してください（自動クリアは危険）。
- .env は機密情報を含むため決して Git にコミットしないでください。
- OpenAI キーやブローカー資格情報等は安全な方法で管理してください。
- プロセス優先度設定は psutil 経由で行います。適切な権限がないと警告が出ますが処理は継続します。

開発者向けメモ
---------------
- 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利）。
- news_nlp / regime_detector の OpenAI 呼び出しはテスト時に差し替え可能なように内部で _call_openai_api を分離しています（ユニットテストで patch できます）。
- 各モジュールは可能な限り副作用を避ける設計（DB 書き込み箇所は明示的）になっています。

よく使うコマンドまとめ
--------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

フィードバック・拡張案
---------------------
- 銘柄別の lot_size を stocks マスタから読み込む拡張（position_sizing の TODO）
- OpenAI 呼び出しの並列化やコスト最適化（チャンクサイズ・バッチ戦略）
- DuckDB スキーマ / ETL のサンプルスクリプト（prices_daily / raw_financials の投入手順）

問題が起きたら
---------------
- まず python -m kabusys.validate_config で設定差分やファイルパスを確認してください。
- monitoring や execution のログに WARN/ERROR が出ていないか確認し、必要に応じて LOG_LEVEL=DEBUG を .env で有効にして詳細ログを取得してください。

以上が README の概要です。必要に応じて具体的な起動例（systemd ユニットや Dockerfile、requirements.txt）を追加できます。追加したい事項があれば教えてください。