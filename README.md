README
======

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。
本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注・リスク管理・注文管理）
- Monitoring（システム稼働監視・リスク監視・アラート管理・Kill Switch）
- Portfolio 構築（銘柄選定・配分・ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント評価・市場レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定等）
- ツール（Paper Trading 検証レポート等）

目的は、売買ロジックを安全に運用するための基盤機能（DB 管理、監視、Kill Switch、ポジション算出、API 呼び出しラッパー等）を提供することです。

主な機能
--------
- 実行（ExecutionEngine）
  - 本番／ペーパートレードの分離（KABUSYS_ENV=paper_trading 時は専用 DB / MockBroker）
  - リスク制御（RiskManager）・オーダーマネージャ・照合（Reconciler）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス生存を監視し SQLite に記録
  - TradeMonitor / RiskMonitor：滞留注文やドローダウンなどを検出・ログ記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止
  - MonitoringEngine：各モニタを束ねて定期実行
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分/スコア配分、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap のスケーリング）
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI を利用）
  - news_nlp.score_news: ニュースを LLM に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせて日次レジーム判定
  - リトライ・バリデーション・出力クリッピングなどフェイルセーフ実装
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成
- 設定サポート
  - config_setup.py : .env を対話的に生成・更新
  - validate_config.py : .env や config/*.yaml の事前検証
- ロギング / プロセス優先度設定ユーティリティ

前提・依存
----------
- Python 3.9+（typing 機能等を使用）
- 必須パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意（validate の YAML 検証や一部スクリプト）:
  - PyYAML
- SQLite / OS 標準ライブラリ（sqlite3 等）は組み込みで使用

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （設定検証で YAML を使う場合）pip install pyyaml

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリに同梱されていない場合あり）。

4. ディレクトリ作成（初回）
   - data/ と logs/ は自動作成されることが多いですが、手動で作る場合:
     - mkdir -p data logs

5. .env（環境変数）設定
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を直接作成（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...
   - 自動ロード挙動:
     - OS 環境変数 > .env.local > .env の優先順位で読み込まれます
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

使用方法
--------
- 実行エンジンを起動（デフォルトの動作）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）と MockBroker を使用
    - 起動時に data/execution.pid を生成（PID ファイル）
    - data/stop_requested.flag が存在すると起動を抑制 / 実行中に検出で停止
    - プロセス優先度を "high" に設定しようとします（psutil の権限に依存）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を変更（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）に書き込みます（monitoring は環境に関係なく同じ sqlite_path を使います）
  - 停止は data/stop_requested.flag を作成することで行えます

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると warnings もエラー扱いになる

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI 機能（プログラムから利用）
  - 必須: OPENAI_API_KEY を環境変数に設定するか、関数に api_key を渡す
  - 例（スクリプト内）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
  - regime_detector も同様に score_regime を呼び出して market_regime に書き込み可能

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: Broker は Mock、paper_db を使用
  - live: 実際の発注を行う可能性があるため注意
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject、デフォルト: instant）
- OPENAI_API_KEY（AI 機能利用時必須）

ログ
---
- ログ出力は kabusys.utils.logging_setup.setup_logging によって管理されます。
  - コンソール（stdout）とファイル（logs/<app_name>.log）へ出力
  - 日次ローテーション（30日保持）
- LOG_DIR 環境変数でログディレクトリを変更可能

データファイル / フラグファイル
------------------------------
- data/kabusys.duckdb  — 分析用 DuckDB
- data/monitoring.db    — 監視ログ（SQLite）
- data/paper_trading.db — ペーパートレード用 SQLite（paper_trading モード）
- data/execution.pid    — 実行エンジン PID（run_execution によって使用）
- data/kill.flag        — Kill Switch がトリガーした理由を記載（存在すると ExecutionEngine に停止命令）
- data/stop_requested.flag — 外部からプロセス停止を指示するためのフラグ（run_monitoring / run_execution が参照）

DB 初期化
--------
- monitoring 用のテーブルは init_monitoring_db(sqlite_conn) により作成されます（冪等）。
  - system_status, trade_logs, positions, risk_logs, dashboard などのテーブルとインデックスが作られます
  - マイグレーションでカラム追加も行われます（例: latency_ms, peak_value）

セキュリティ注意事項
--------------------
- .env は絶対にコミットしないこと（config_setup はヘッダに注意喚起あり）
- KABUSYS_ENV=live の際は LINE 通知設定や Kill Switch の設定を慎重に確認すること
- プロダクションでの実行は十分な権限・監視の下で行ってください

主要ファイル / ディレクトリ構成
------------------------------
下は本リポジトリで重要なファイル群の抜粋（src/kabusys 下）。実際のツリーは若干異なる場合があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ロギング共通化
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py
    - trade_monitor.py       — （実際の実装を参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（上記は本 README 作成時点での主要ファイルを抜粋したものです）

開発者向けメモ
--------------
- 設定読み込み順: OS 環境変数 > .env.local > .env。_find_project_root() によってプロジェクトルートを探索するため、CWD に依存しません。
- DB 接続:
  - Monitoring は常に settings.sqlite_path（本番 DB）を使用します（監視ログは本番 DB にまとめる設計のため）。
  - Execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して本番と完全に分離します。
- AI モジュールは OpenAI SDK を利用しており、API の失敗や 5xx 等に対してリトライやフェイルセーフを実装しています。
- ローカルテスト時に自動で .env をロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はリポジトリルートの LICENSE を参照してください（ここには含まれていません）。
- バグ報告・プルリクエスト歓迎です。重大な変更は設計方針（安全性・フェイルセーフ性）に配慮してください。

以上。README に含める追加情報や例コマンド（systemd / Docker / CI 用の起動例など）を希望される場合は教えてください。