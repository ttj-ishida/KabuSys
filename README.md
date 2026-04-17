README
====

概要
----
KabuSys は日本株向けの自動売買 / 研究基盤です。シグナル生成・ポートフォリオ構築・発注実行・監視・レポーティング・AI（ニュースセンチメント／レジーム判定）など、実運用を意識したコンポーネント群を含みます。  
設計方針としては「本番 DB/発注 API には直接触れないリサーチモジュール」「ペーパートレードと本番の明確な分離」「環境変数による設定管理」「フェイルセーフな外部 API 呼び出し（リトライ・フォールバック）」を重視しています。

主な機能
--------
- 実行エンジン (ExecutionEngine)
  - ブローカークライアントを通じた発注管理（paper_trading モードでは MockBrokerClient を使用）
  - リスク管理（ポジション上限・ドローダウン等）
  - 注文履歴の管理（SQLite）
- 監視 (Monitoring)
  - システム状態監視（CPU / メモリ / ディスク、プロセス生存確認）
  - 注文滞留・約定異常の検出
  - リスク監視（ドローダウン・ポジション上限）と Kill Switch（flag ファイルによるエンジン停止）
  - アラート管理（LINE 等の通知を想定）
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、レジーム乗数、セクター上限適用
  - 株数決定（lot サイズ丸め、aggregate cap のスケーリング）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（OpenAI 利用）
  - ニュースのセンチメント評価（ai_scores への書き込み）
  - マーケットレジーム判定（ma200 とマクロニュースの合成）
  - （API 呼び出しは安全なリトライとフォールバック実装）
- ツール
  - Paper Trading 検証レポート生成 script（orders / monitoring データから各種指標を算出）
- 設定関連
  - .env を対話的に生成/更新する config_setup.py
  - 起動前に設定を検証する validate_config.py

セットアップ
-----------
前提
- Python 3.9+（コードは型注釈を使用）
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml のパース検証を行う場合。省略可）

推奨インストール手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存関係インストール
   - pip install duckdb psutil openai pyyaml
     （OpenAI / PyYAML は用途に応じて追加）
3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

環境変数と .env
- .env をプロジェクトルートに作成することで主要な設定を管理します。自動ロード機能があるため、import 時に .env の値が参照されます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- よく使う環境変数（一部とデフォルト）:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能利用時に必須)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — 監視 DB（本番）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
  - KABUSYS_ENV (development | paper_trading | live) — 実行モード
  - LOG_LEVEL (default: INFO)
  - KILL_FLAG_CLEAR_ON_START (0|1)
  - MONITOR_POLL_INTERVAL (監視ループの秒間隔、default: 60)

.env を対話的に作る（推奨）
- python -m kabusys.config_setup
  - ウィザードに従って .env を生成できます（秘密値はマスク表示されます）。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

使い方（主要な起動コマンド）
----------------------------
1) 監視ループ起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は常に Settings.sqlite_path（本番用 monitoring DB）を使用します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します。

2) 実行エンジン起動（ExecutionEngine）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録します（本番 DB と完全分離）。
  - 起動時に data/execution.pid が作成されます。プロセス監視は system_monitor が行います。
  - 停止: data/stop_requested.flag を作成すると実行エンジン停止処理がトリガーされます。

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。
  - 稼働率、注文成功率、送信率、レイテンシ等を算出して PASS/FAIL を判定します。

4) AI 関連（コード経由）
- kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用してニュースセンチメントやレジーム判定を実行できます。OpenAI API キーは OPENAI_API_KEY 環境変数、または関数引数で渡します。
  - 例（簡易）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")

注意事項 / 実運用メモ
- paper_trading モードは発注を模擬します。本番環境（KABUSYS_ENV=live）では十分に検証を行ってから運用してください。
- Kill Switch: kabusys.monitoring.kill_switch が一定のリスク条件で data/kill.flag を作成すると ExecutionEngine を停止させる挙動があります。本番では KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では 0 推奨）。
- DB 初期化とマイグレーション: monitoring_db.init_monitoring_db は必要なテーブル/カラムを冪等に作成・マイグレーションします。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び出して高優先度を要求します。OS・権限により失敗する場合はログ出力してスキップします。
- 外部 API（OpenAI 等）呼び出しはリトライ・フォールバック実装がありますが、API キーの管理・レート制限には注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトの主要モジュールは src/kabusys 以下にまとまっています。代表的な構成は次の通りです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証ツール
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores へ書込）
    - regime_detector.py     — レジーム判定（ma200 + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/               — 発注・Engine 関連（OrderRepository 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    — データパイプライン / utilities（prices_daily などを想定）
  - utils/
    - process_priority.py
  - ...（その他ユーティリティ・モジュール）

データ / フラグファイル（project root の data ディレクトリ）
- data/monitoring.db          — デフォルトの監視 SQLite（SQLITE_PATH）
- data/paper_trading.db       — paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb        — DuckDB（DUCKDB_PATH）
- data/stop_requested.flag   — run_*.py が存在チェックする停止フラグ
- data/kill.flag             — Kill Switch が作成する停止フラグ（Execution 停止用）
- data/execution.pid         — ExecutionEngine が自身の PID を書き込むファイル

サンプル .env（抜粋）
--------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ライセンス / 貢献
----------------
リポジトリ固有のライセンスやコントリビュート準備があればプロジェクトルートの LICENSE や CONTRIBUTING を参照してください。

補足
----
- モジュール間の公開 API は各モジュールの docstring を参照してください。README は起動・設定・高レベルの使い方をまとめたものです。
- 追加のコマンドやスクリプトがある場合はプロジェクトの scripts/（存在するなら）や top-level Makefile を参照してください。

質問や README の改善希望があれば、どの情報を追加したいか教えてください。