README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。
本リポジトリには、実行エンジン起動スクリプト、監視（Monitoring）周りの実装、ポートフォリオ構築ロジック、研究用ファクター計算、AI（OpenAI）を使ったニュース NLP・レジーム判定、各種ユーティリティや CLI（.env ウィザード・設定検証・検証レポート生成）などが含まれます。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に完全分離して記録。
- 監視サブシステム（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine による定期チェック
  - SQLite ベースの監視 DB（monitoring_db）とアラート処理の土台
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止制御
- ポートフォリオ構築（portfolio）
  - 候補選定、スコア重み・等金額重み、ポジションサイズ計算、セクター上限適用、レジーム乗数など
- 研究モジュール（research）
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）や IC 計算、特徴量要約
- AI モジュール（ai）
  - OpenAI を用いたニュースのセンチメントスコアリング（news_nlp）および市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）

セットアップ手順
----------------
※ ここでは一般的な Python 環境での手順を示します。実際の依存関係はプロジェクトの requirements.txt を参照してください（本サンプルには同ファイルが含まれていないため、下記は推奨パッケージの例です）。

1. Python 環境
   - Python 3.10+ を推奨（コード中で型の '|' を使用しています）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

4. プロジェクトルートに移動（README と同階層）
   - cd <project-root>

5. 初期設定 (.env) の作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
     - 主要な必須環境変数:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
       - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - 他に DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL 等を設定できます。
   - 手動で .env を作る場合は .env.example を参考にしてください。

6. 設定検証
   - python -m kabusys.validate_config
   - 必須項目や config/*.yaml の整合性をチェックします。
   - --strict オプションを付けると警告も失敗扱いになります。

使い方
------
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使い、本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書き込みます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は環境に関係なく本番用 sqlite_path（SQLITE_PATH）を参照して監視ログを記録します。
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先して DB を指定）

- .env ウィザード
  - python -m kabusys.config_setup
  - 既存 .env があればその値を再利用できます。

- 設定検証 CLI
  - python -m kabusys.validate_config [--strict]

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime を呼ぶ際は OPENAI_API_KEY が必要です（引数で渡すことも可能）。
  - OpenAI の呼び出しはリトライや JSON レスポンス検証など堅牢化を行っています。

- Kill Switch / フラグファイル
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine に停止シグナルを送ります。
  - 実行開始時に Kill Flag を自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番では推奨されません。

設定／環境変数（主要）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨（機能により必須）:
  - OPENAI_API_KEY（AI 機能）
- その他:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）
  - PAPER_FILL_MODE（paper_trading の MockBroker 挙動: instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み/検証、Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 分離）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py         — OpenAI を用いたニュースセンチメントスコアリング
  - regime_detector.py  — マクロ＋ETF MA による市場レジーム判定
- monitoring/
  - monitoring_db.py    — SQLite に対する永続化レイヤ
  - system_monitor.py   — CPU/メモリ/disk / データ鮮度 / PID チェック
  - trade_monitor.py    — 滞留注文・約定価格異常チェック
  - risk_monitor.py     — ドローダウン・ポジション上限の監視
  - kill_switch.py      — kill.flag の作成/削除
  - alert_manager.py    — （アラート送信の土台）
  - monitoring_engine.py— すべての Monitor を束ねるエンジン
- execution/
  - order_manager, order_repository, execution_engine 等（発注ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定、等分・スコア重み
  - position_sizing.py   — 発注株数計算、リスク制限・丸め処理
  - risk_adjustment.py   — セクターキャップ、レジーム乗数
- research/
  - factor_research.py   — momentum/value/volatility 等のファクター計算（DuckDB 前提）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - process_priority.py  — プロセス優先度／CPU affinity 設定ユーティリティ

運用上の注意
------------
- run_monitoring は monitoring 用 DB（SQLITE_PATH）に対して常に「本番 DB パス」を使います。監視は環境に依らず本番 DB を参照する設計です。
- paper_trading は発注先・DB を本番から分離するためのモードです。必ず KABUSYS_ENV=paper_trading を設定して動かしてください。
- Kill Switch（data/kill.flag）や stop_requested.flag（data/stop_requested.flag）／execution.pid（data/execution.pid）などはファイルベースでプロセス制御を行います。CI/CD や手動運用時はこれらのファイルの取り扱いに注意してください。
- OpenAI API を使う箇所は外部 API の可用性に依存します。API 失敗時のフェイルセーフが各モジュールに組み込まれていますが、キー管理（OPENAI_API_KEY）は厳重に行ってください。

トラブルシュート
----------------
- 設定検証でエラーが出る場合は python -m kabusys.config_setup で .env を再作成し、python -m kabusys.validate_config で再確認してください。
- psutil による優先度設定で AccessDenied が出る場合、管理者権限が必要なことがあります。警告が出るだけで実行自体は継続します。
- DuckDB / SQLite に関するエラーは DB パスやファイルのパーミッションを確認してください。
- OpenAI 呼び出しでレート制限やネットワークエラーが発生した場合はモジュール側でリトライを行いますが、APIキーやネットワーク環境を確認してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: src/kabusys/__version__ = 0.1.0
- ライセンス情報や詳細はプロジェクトルートの LICENSE 等を参照してください（本サンプルに含まれていない場合があります）。

改良提案（参考）
----------------
- requirements.txt / packaging metadata を追加して依存管理を明確化する。
- systemd / PM2 等でプロセス管理する場合は pid ファイルや停止フラグの扱いをドキュメント化する。
- テストを追加して key コンポーネント（position sizing、risk checks、news_nlp のパース等）を保護する。

以上。README の追加修正や各コマンドの詳細な実行例が必要であれば教えてください。