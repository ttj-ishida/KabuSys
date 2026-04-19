KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの研究・ポートフォリオ構築・発注・監視を行う自動売買基盤のコードベースです。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン (ExecutionEngine)：発注・注文管理・リスク管理を行うランタイム
- 監視コンポーネント (Monitoring)：システム状態・注文状況・リスク指標を定期監視してアラート・Kill Switch を管理
- 研究用モジュール (research)：各種ファクター計算や特徴量探索
- ポートフォリオ構築 (portfolio)：銘柄選定・重み付け・サイズ計算等の純関数群
- AI モジュール (ai)：ニュースの NLP スコアリングや市場レジーム判定（OpenAI を使用）
- ユーティリティ（設定読み込み・ログ設定・プロセス優先度など）
- CLI ツール（.env 作成ウィザード、設定検証、Paper Trading 検証レポート 等）

主な特徴
--------
- 明確に分離されたモジュール設計（発注ロジックと研究ロジックは分離）
- Paper Trading モード（モックブローカー）と Live モードの切替を環境変数でサポート
- DuckDB（分析データ）と SQLite（監視・注文ログ）を併用
- システム監視・Risk Monitor・Kill Switch による安全ガード
- ニュースを LLM（OpenAI）でスコアリングする AI パイプライン
- 日次ローテーションログ + コンソール出力の統一的ログ設定

前提・依存
----------
最低限の依存（実行機能に応じて変わります）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を利用する場合）
- PyYAML（config の YAML 検証を使う場合）
（実際は requirements.txt を用意して pip install -r でインストールしてください。無ければ以下のように個別に入れてください）
例:
    pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリのクローン / ソース配置

2. Python 仮想環境を作成して依存をインストール
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
（requirements.txt が無い場合は上記の必須パッケージを個別にインストール）

3. .env の作成（推奨：対話式ウィザード）
    python -m kabusys.config_setup
   ウィザードは J-Quants トークンや kabuAPI パスワードなどの必須値を対話形式で生成します。
   生成された .env は絶対に Git にコミットしないでください。

4. 設定の検証
    python -m kabusys.validate_config
   --strict を付けると警告があっても失敗として扱います:
    python -m kabusys.validate_config --strict

主要な環境変数（要設定）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live）: 実行モード
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（任意、デフォルト: INFO）
- LOG_DIR（任意、デフォルト: logs/）

主な使い方
----------

1. ExecutionEngine の起動（本番/ペーパートレード）
- 実行スクリプト:
    python src/kabusys/run_execution.py
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し発注履歴は data/paper_trading.db に記録されて本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません（安全措置）。
  - 実行中は _EXECUTION_PID（data/execution.pid） に PID を書く等の処理があります。

2. 監視（Monitoring）起動
- 実行スクリプト:
    python src/kabusys/run_monitoring.py
- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60 秒）
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を参照します
  - stop_requested.flag を検知するとループを終了します

3. kill.flag を使った停止（Execution 停止）
- KillSwitch（kabusys.monitoring.kill_switch）はリスク条件に合致したとき data/kill.flag を書き込み、ExecutionEngine 側はこれを検知して停止します。
- 手動で停止シグナルを出すには kill.flag を作成します（内容は理由テキスト）。
- Execution 起動時は KILL_FLAG_CLEAR_ON_START=1 の設定により起動時に自動クリアするかを制御できます（本番では 0 推奨）。

4. Paper Trading 検証レポート生成
- スクリプト:
    python -m kabusys.tools.paper_verification_report
- オプション例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。--db オプションでも上書きできます。

5. .env 作成ウィザード / 設定検証
- 対話式 .env 作成:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
  --strict を付けると警告も失敗扱いになり exit code 1 を返します。

ログ設定
--------
- 共通ログ初期化は kabusys.utils.logging_setup.setup_logging(app_name="...") を用います。
- デフォルトでは StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）が設定されます。ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/。
- ログレベルは引数、環境変数 LOG_LEVEL、デフォルト(INFO)の優先順で決定されます。

AI 機能
-------
- ニュース NLP（kabusys.ai.news_nlp.score_news）:
  - raw_news と news_symbols を集約して OpenAI に送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込みます。
  - OpenAI API キーは OPENAI_API_KEY（環境変数）または関数引数で指定します。
  - バッチ処理、トリミング、リトライ・バックオフ、レスポンスバリデーションを実装しています。
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）:
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを組み合わせて 'bull'/'neutral'/'bear' を判定・永続化します。
  - API キーは同様に OPENAI_API_KEY を使用します。

モニタリング / リスク管理
-------------------------
- system_monitor: CPU/メモリ/ディスク/プロセス存続/データ鮮度をチェックして system_status にログ化します。
- trade_monitor: trade_logs を参照して滞留注文・約定異常などを検出（該当モジュール参照）。
- risk_monitor: dashboard（ポートフォリオ集計）を参照してドローダウンやポジション上限を監視、必要に応じて risk_logs を記録。
- monitoring_engine: 上記の監視を束ね、Kill Switch 評価や AlertManager 経由で通知を行います。

重要な挙動メモ
--------------
- Settings（kabusys.config.Settings）は自動的にプロジェクトルートの .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- KABUSYS_ENV:
  - development: 開発・テスト（発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、専用 SQLite）
  - live: 本番（実際発注）
- PAPER_FILL_MODE（paper_trading の約定挙動）:
  - instant | partial | never | reject（デフォルト: instant）
- monitoring は環境に関わらず Settings.sqlite_path（本番監視 DB）を使用する点に注意。Execution は is_paper により paper_sqlite_path を使用します（DB を分離）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数/.env 読み込み・Settings
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- kabusys/utils/
  - logging_setup.py — ログ初期化
  - process_priority.py — プロセス優先度 / CPU affinity
- kabusys/monitoring/
  - monitoring_db.py — SQLite の永続化レイヤ
  - system_monitor.py — システム監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py （存在想定） — 通知管理
- kabusys/execution/
  - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
  - broker_factory.py — ブローカークライアント生成（Mock/実ブローカー）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py ...
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 銘柄選定／重み／サイズ算出
- kabusys/research/
  - factor_research.py — ファクター計算 (momentum/volatility/value)
  - feature_exploration.py — IC, forward returns, 統計サマリー
- kabusys/ai/
  - news_nlp.py — ニュース NLP スコアリング
  - regime_detector.py — 市場レジーム判定
- kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

開発者向けメモ
---------------
- DB スキーマ変更は monitoring_db.init_monitoring_db にて冪等に適用するパターンを採用しています。マイグレーションロジックをここに置く想定です。
- 外部 API（OpenAI 等）呼び出しは専用の内部ラッパ関数経由で行い、テスト時は patch して置き換えやすい設計になっています（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- 直接 date.today()/datetime.now() を参照せず、関数引数で日付を渡す設計が多く、ルックアヘッドバイアスの軽減を意図しています。

よく使う実行コマンド まとめ
-------------------------
- .env 作成ウィザード:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
- Execution 起動:
    python src/kabusys/run_execution.py
- Monitoring 起動:
    python src/kabusys/run_monitoring.py
- Paper Trading レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 注意
-----------------
- .env に API キー等の秘密情報を含めるため、.gitignore 等で必ず除外してください。
- 本コードは学術・試作用途の参考実装です。live モードで実行する前に十分なレビューと検証（特にリスク設定・Kill Switch）を行ってください。

補足
----
README に書かれている挙動はソースコード（特に run_execution.py / run_monitoring.py / config.py / monitoring/* / ai/*）の注釈に基づいています。実運用前には必ず設定検証（validate_config）およびテスト（ペーパートレード）で全フローを確認してください。