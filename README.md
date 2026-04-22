README
=====

概要
----
KabuSys は日本株向けの自動売買・分析フレームワークです。本リポジトリには以下の主要コンポーネントを含みます。

- ExecutionEngine: 発注・リスク管理・オーダー管理を担当するエンジン
- Monitoring: システム稼働／オーダー状況／リスク監視と Kill Switch
- Portfolio モジュール: 銘柄選定、配分、サイズ計算、セクター制限などの純関数
- Research / AI: ファクター計算、特徴量探索、ニュース NLP（OpenAI）を用いたスコアリング、レジーム判定
- ツール: ペーパートレード検証レポート生成や設定ウィザード、設定検証 CLI

本 README はコードベース（src/kabusys 以下）を元に、セットアップ方法・使い方・ディレクトリ構成をまとめたものです。

主な機能
--------
- 環境に応じた ExecutionEngine（本番／ペーパー切替）
  - KABUSYS_ENV=paper_trading のとき MockBroker を使用し、ペーパートレード用 DB に記録して本番 DB と分離
- 監視（Monitoring）
  - システムリソース監視（CPU/Mem/Disk）、Execution プロセス生存チェック、データ鮮度チェック
  - トレードログ監視（滞留注文、異常約定等）
  - リスク監視（ドローダウン、ポジション数上限）
  - Kill Switch：条件満たすと data/kill.flag を生成し Execution を停止
- Portfolio 構築ユーティリティ（候補選定、重み付け、位置サイズ計算、セクター制限、レジーム乗数）
- Research（DuckDB を用いたファクター計算、将来リターン、IC 計算、統計要約）
- AI 機能
  - ニュース NLP による銘柄別センチメントスコア（OpenAI）
  - マクロニュース + ETF MA を用いた市場レジーム判定（OpenAI）
- ツール
  - 設定ウィザード（.env の対話式作成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

前提・依存ライブラリ
-------------------
最低限の依存（開発環境での利用例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合に任意）

インストール例:
- 仮想環境作成:
  python -m venv .venv
  source .venv/bin/activate
- 必要パッケージをインストール:
  pip install duckdb psutil openai PyYAML

注意: 実際の requirements.txt がある場合はそちらを利用してください。

環境変数（主なもの）
-------------------
.env（または環境変数）で設定します。config_setup で対話的に作れます。

必須（実運用時）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

主要オプション（デフォルトや説明）
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…） デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject） デフォルト: instant
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PID_FILE_PATH / KILL_FLAG_PATH: PID/kill flag のパス（デフォルトは data/ 以下）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒） デフォルト: 60

.env の自動読み込み
- 実行時、プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env を自動読み込みします。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
---------------
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作る（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

4. .env を作成（対話式推奨）
   python -m kabusys.config_setup
   - J-Quants / kabu API パスワードなど必須項目を設定してください。

5. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. データディレクトリの作成（必要に応じて）
   mkdir -p data logs

使い方（主要コマンド）
--------------------

ExecutionEngine を起動する
- 本番 / ペーパーは KABUSYS_ENV に従います。ペーパー時は独立 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
- 起動:
  python -m kabusys.run_execution
- 実行中は data/execution.pid（デフォルト）に PID ファイルを書きます。
- 強制停止: data/stop_requested.flag を作成するとループが終わります（run_execution/run_monitoring がチェック）。
- Kill Switch による安全停止: monitoring が条件を満たすと data/kill.flag を書き、ExecutionEngine 起動時に検出・停止します。

Monitoring を起動する
- 起動:
  python -m kabusys.run_monitoring
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能（秒）。デフォルト 60 秒。
- monitoring は常に本番の sqlite_path（Settings.sqlite_path）を参照して監視ログを保存します。

設定ウィザード（.env）
- 対話的に .env を作成:
  python -m kabusys.config_setup

設定検証
- 設定と config/*.yaml の存在・基本チェック:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

Paper Trading 検証レポート
- ペーパートレード DB（デフォルト: data/paper_trading.db）から指標を計算して標準出力に表示:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 機能の呼び出し（ライブラリ利用例）
- ニュース NLP（データは DuckDB の raw_news / news_symbols テーブルに入っている前提）:
  from pathlib import Path
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  score_news(conn, target_date=date(2026,4,20), api_key='sk-...')

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026,4,20), api_key='sk-...')

注意: OpenAI の呼び出しは課金対象／API レート制限の影響を受けます。API キー管理に注意してください。

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成してください）。
- ログ出力は kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。

Kill / Stop 制御
----------------
- 停止フラグ:
  - data/stop_requested.flag: ランタイムループ（run_execution / run_monitoring）が存在をチェックして終了します。ファイルの存在が確認されると安全に停止します（停止後は自動で削除されません）。
  - data/kill.flag: Monitoring の KillSwitch が書き込み、ExecutionEngine に対する停止シグナルとして機能します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされます（本番環境では 0 を推奨）。
- 実行中に外部から停止させたい場合はこれらのフラグファイルを作成してください（内容は理由テキストが書き込まれます）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理（Settings クラス）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

subpackages / モジュール
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（OpenAI）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py      — システム監視（CPU/Mem/Disk、データ鮮度、プロセス監視）
  - trade_monitor.py       — （トレード監視、滞留注文等）※詳細はコード参照
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch 管理
  - monitoring_engine.py   — 各 Monitor を統合してポーリング
  - alert_manager.py       — （通知管理、LINE など。コード参照）
- execution/
  - execution_engine.py    — ExecutionEngine 本体
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — ファクター計算（momentum / volatility / value）
  - feature_exploration.py — 将来リターン・IC 計算 etc.
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/monitoring_db.py etc.（上記に含む）

補足 / ベストプラクティス
------------------------
- 本番環境（KABUSYS_ENV=live）での起動前には必ず python -m kabusys.validate_config を実行して設定を検証してください。
- .env を絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注記あり）。
- OpenAI の API 呼び出しは可観測性とコストを考慮して使用してください。テスト時はモック化（unittest.mock.patch）を推奨します。
- monitoring は本番の sqlite_path を参照して監視ログを残す設計です。ペーパートレードで監視を行う場合は用途に応じた設定を行ってください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

問題報告 / 貢献
----------------
バグ報告や改善提案は issue を立ててください。プルリク歓迎します。コードを変更する際はユニットテスト・動作確認を追加してください。

以上。必要であれば README に追記してほしい点（例: 詳細な config/*.yaml の説明、実行例のログ抜粋、ユニットテスト実行方法 など）を教えてください。