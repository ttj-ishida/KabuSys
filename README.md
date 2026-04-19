README — KabuSys

概要
-----
KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。本リポジトリは下記の主要機能を提供します。
- 注文実行用エンジン（ExecutionEngine）
- 常時監視プロセス（Monitoring）
- ペーパートレード用分離DB・モックブローカー対応
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- ファクター計算・特徴量探索（DuckDB を使用）
- ニュースを LLM でスコアリングする AI モジュール
- 設定ウィザード・構成検証ツール・検証レポート生成

機能一覧
--------
- 実行・監視プロセス起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定関連
  - config_setup.py : 対話式 .env ウィザード（.env を生成/更新）
  - validate_config.py : .env と config/*.yaml の検証ツール（--strict オプションあり）
- モニタリング
  - system_monitor / trade_monitor / risk_monitor を束ねる MonitoringEngine
  - kill_switch による kill.flag 出力で ExecutionEngine 停止
  - monitoring_db: SQLite に監視ログ / トレードログ / リスクログ / ダッシュボードを永続化
- ペーパートレード
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 用の SQLite を利用（data/paper_trading.db など）
  - PAPER_FILL_MODE (instant/partial/never/reject) を設定可能
- リサーチ / ポートフォリオ構築
  - research: モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB）
  - portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター上限調整
- AI
  - ai.news_nlp, ai.regime_detector: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価・レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成（稼働率、成功率、レイテンシ等）

必要条件
--------
- Python 3.10 以上（型ヒントで | 演算子を使用しているため）
- SQLite（標準ライブラリ）
- 追加 Python パッケージ（少なくとも）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証をフルに行う場合。任意）
- ネットワークアクセス（実運用で kabuステーション / OpenAI を利用する場合）

（依存関係はプロジェクトに requirements.txt があればそれを使用してください。無い場合は上記パッケージを pip install してください。）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば pip install -r requirements.txt）

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従い J-Quants トークンや kabu API パスワード、DB パス等を設定

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL 扱いで確認: python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 、logs/ を使用します。設定に合わせて作成してください。
   - ログディレクトリは環境変数 LOG_DIR で変更できます。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、発注はモックで分離された PAPER_TRADING_SQLITE_PATH に記録
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant, partial, never, reject）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視 DB（本番用）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — ペーパートレード専用 DB
- LOG_LEVEL (INFO 等)
- LOG_DIR (logs ディレクトリを指定可能)
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH (デフォルト data/kill.flag) — KillSwitch が書き込むパス
- PID_FILE_PATH (デフォルト data/execution.pid) — ExecutionEngine の pid ファイル

使い方
------
1. 監視プロセス起動（常時監視）
   - MONITOR_POLL_INTERVAL を変更する例:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - デフォルトは 60 秒。0 以下の値は無効でデフォルトにフォールバックします。

2. 実行エンジン起動（発注 / ペーパートレード）
   - KABUSYS_ENV を指定して起動:
     - 本番想定: KABUSYS_ENV=live python -m kabusys.run_execution
     - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録され、本番 DB と完全分離されます。

3. 停止と Kill Switch
   - 実行プロセスを停止したい場合:
     - KillSwitch を動作させるには、監視（MonitoringEngine）から条件に応じて data/kill.flag が書き込まれます。ExecutionEngine は起動時に kill.flag を確認・実行中に存在すれば停止します。
   - 監視プロセスや実行プロセスを強制的に停止したい場合は、プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。

4. 設定の対話式作成・更新
   - python -m kabusys.config_setup

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログと DB
----------
- ログ:
  - デフォルトは logs/ ディレクトリに app_name ごとの日次ローテーションログを出力します（例: logs/execution.log, logs/monitoring.log）。
  - LOG_DIR 環境変数または setup_logging の引数で変更可能。
- DB:
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視用 monitoring.db（デフォルト data/monitoring.db）
  - ペーパートレードは paper_trading.db に記録（KABUSYS_ENV=paper_trading 時に切替）

注意事項 / 運用メモ
-------------------
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 1 にしないことを推奨します（自動クリアは危険）。
- validate_config の出力を運用前に確認してください（必須環境変数や DB パスの親ディレクトリ存在チェック等）。
- OpenAI を使う機能は API キーが必要です。失敗時はフェイルセーフ（0.0 等にフォールバック）する設計ですが、API コストやレート制限に注意してください。
- run_monitoring/run_execution はプロセス優先度を高く設定しようとします（set_process_priority）。権限の都合で設定に失敗する場合は警告が出ます。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- config_setup.py                — 対話式 .env ウィザード
- validate_config.py             — 設定検証 CLI
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — ペーパートレード検証レポート
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（OpenAI 統合）
  - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py             — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py              — （実装参照）トレード監視
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py              — （アラート送信ロジック; 実装が存在する前提）
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py
- monitoring/* / execution/* / data/* などの補助モジュール（コード参照）

（注）実際のリポジトリには execution/ や data/ 下にさらに多数のモジュール・スクリプトが含まれる想定です。上記は本リストから抜粋した主要ファイルです。

開発者向けメモ
--------------
- DuckDB 接続を渡して純粋関数（research モジュール）を実行する設計により、リサーチは本番口座データに影響を与えません。
- ai モジュールは API 呼び出しのラップと厳格なレスポンスバリデーションを行い、部分失敗時にも他データを保護する実装になっています。
- monitor 系は監視ログを永続化し、条件により kill.flag を書くことで ExecutionEngine の安全停止を実現します。

ライセンス・貢献
----------------
本リポジトリのライセンスやコントリビュートルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足や README に追加してほしい情報（例: 実際の requirements.txt、systemd サービス定義、Dockerfile など）があれば教えてください。README をその内容に合わせて補強します。