KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアモジュール群です。本リポジトリには以下の機能が含まれます（発注・モニタリング・ポートフォリオ構築・ファクター計算・AI を使ったニュース解析 等）。コマンドラインの起動スクリプトや対話式の .env ウィザード、検証ユーティリティも同梱しています。

主な設計方針
- 本番とペーパートレードを環境変数（KABUSYS_ENV）で切り替え可能
- DuckDB（分析用）と SQLite（監視 / 発注ログ）を利用
- OpenAI を使ったニュース NLP / レジーム検出をサポート（API キー必須）
- ログは統一的に設定され、日次ローテーションされる

主な機能一覧
----------------
- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアントの切替（paper_trading → MockBroker）
  - Order 管理 / Risk 管理 / Reconciler 等の基盤

- Monitoring
  - System / Trade / Risk モニタリング（監視ループ run_monitoring.py）
  - Kill Switch（条件に応じた停止フラグ書き込み）
  - 監視ログの永続化（SQLite, monitoring_db.py）

- Portfolio Construction
  - 候補選定・重み計算（等比率 / スコア加重）
  - セクター上限適用・レジーム乗数
  - ポジションサイズ計算（ロット丸め・集約キャップ等）

- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（前方リターン・IC 計算・統計サマリ）

- AI
  - ニュース NLP による銘柄別センチメント付与（OpenAI）
  - 市場レジーム検出（ETF MA とマクロニュースの合成）

- ユーティリティ
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - 統一ロギング設定 / プロセス優先度設定ユーティリティ

セットアップ手順
----------------
前提
- Python 3.9+ を想定（duckdb, psutil, openai などが必要）
- ローカル環境に SQLite が利用可能（標準ライブラリに含む）

1. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージ（例）:
     - pip install duckdb psutil openai PyYAML

2. プロジェクトルートに移動
   - 本 README と同じルートに src/ と .env（または .env を生成するためのウィザード）を置きます。

3. .env を作成（対話式推奨）
   - python -m kabusys.config_setup
   - ウィザードに従い必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit code 1）扱いになります。

環境変数の主要項目（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は発注はモック化され、data/paper_trading.db を使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時必須）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1。production では 0 推奨）

ログ
- ログディレクトリのデフォルトは logs/
- 各アプリケーションは logs/<app_name>.log に日次ローテートで書き出します（30日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging() を経由して統一されます

使い方（主要コマンド）
--------------------
1. .env 作成（対話式）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - strict モード: python -m kabusys.validate_config --strict

3. 監視ループの起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 起動時にプロセス優先度を高く設定し、MONITOR_POLL_INTERVAL（秒）でポーリングします。
   - 監視は Settings.sqlite_path（監視 DB）を使用します。monitoring は環境にかかわらず本番 sqlite_path を参照します。

4. Execution エンジンの起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録し、MockBrokerClient が使用されます。
   - 起動時に data/execution.pid（デフォルト）へ PID を書き、data/stop_requested.flag が存在すると起動しません。
   - 停止は data/stop_requested.flag を作成するか、監視側から kill.flag を書き込ませる方法があります。

5. Paper Trading 検証レポート（ツール）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。--db で指定可。
   - 稼働率・注文成功率・P95 レイテンシ等の判定を出力します。

6. AI 機能（プログラムから呼び出す）
   - 例: ニューススコア付与
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
   - OpenAI API キーが必要です。score_regime（regime_detector）も同様。

停止 / Kill Switch
- KillSwitch は監視コンポーネントが条件を満たしたときに data/kill.flag を作成します（ExecutionEngine はこれを検出して停止）。
- 管理者が即時停止を要求する場合は手動で data/kill.flag を作成できます（ファイルに理由文字列を保存）。
- stop_requested.flag は run_* スクリプトの早期終了用フラグ（stop リクエスト）です。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・.env の自動読み込みと Settings クラス
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコア
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite のスキーマ初期化・CRUD
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — (trade 関連監視) ※実装の詳細はリポジトリ参照
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 monitor を束ねるエンジン
  - alert_manager.py       — (通知管理) ※実装の詳細はリポジトリ参照
- execution/
  - execution_engine.py    — ExecutionEngine 実装（セッション実行）
  - broker_factory.py      — Broker クライアント生成
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/ (DB 層は上記参照)
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity 設定
- tools/
  - paper_verification_report.py

（上記に含まれない細かいモジュールや実装はソースツリーを参照してください）

補足・運用上の注意
-----------------
- 本番環境（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START の扱いに注意してください。自動クリアは危険です。
- monitoring は Settings.sqlite_path（監視 DB）を常に使用します。paper_trading 環境でも監視 DB は切り替わりません（設計上の仕様）。
- Execution は paper_trading 環境時に専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB とデータを分離します。
- OpenAI API 呼び出しにはレート制限やエラーがあるため、リトライとフェイルセーフ（失敗時はスコアを補完する等）の実装が入っています。API キーの管理には十分注意してください。
- DuckDB や SQLite のファイルパスは .env（DUCKDB_PATH / SQLITE_PATH など）で設定できます。ログやデータファイルは Git 管理から除外してください（.env は絶対にコミットしない）。

サポート / 開発
----------------
- 開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます（テストや CI 用）。
- モジュール単位でのユニットテストを作成してください（AI 呼び出しはモック化推奨）。
- 大きな変更を加える場合は validate_config.py の検証ロジックを拡張して起動前チェックを強化してください。

以上。必要であれば README にサンプル .env のテンプレートや Docker / systemd 用の起動例（ユニットファイル）なども追加できます。追加希望があれば教えてください。