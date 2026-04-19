README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本コードベースは以下の主要機能を備えます。

- 実行エンジン（ExecutionEngine）: ブローカーとの発注、注文管理、リスク管理を行う。
- 監視（Monitoring）: システム状態・注文状態・リスクを定期チェックし、Kill Switch やアラートを発生させる。
- ポートフォリオ構築（Portfolio）: 候補選定、配分重み、ポジションサイズ計算、セクター制限など。
- リサーチ（Research）: DuckDB 上の価格・財務データからファクター・将来リターン・IC などを計算。
- AI 支援機能（AI）: OpenAI を用いたニュースセンチメント、マクロセンチメント（レジーム判定）。
- 運用・検証ツール: 設定ウィザード、設定検証、Paper Trading 検証レポート等。

特徴
----
- 環境に依存しない設定読み込み（.env / .env.local / OS 環境変数）
- Paper Trading と Live を明確に分離（paper_trading 用 DB を利用）
- DuckDB を用いたオンプレミスなリサーチ用クエリ
- OpenAI（gpt-4o-mini）を用いたニュース／マクロセンチメント処理（任意）
- 監視 DB（SQLite）に監視・ログを永続化し、Kill Switch を介してエンジンを安全停止

依存関係（主なもの）
-------------------
最低限の依存パッケージ（環境によって追加で必要になる可能性あり）:
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config で YAML 中身を検証する場合に必要）

インストール例（venv を想定）:
- pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. リポジトリをクローン / プロジェクトディレクトリへ移動。

2. 仮想環境の作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install duckdb psutil openai PyYAML
   （必要に応じて requirements.txt を用意している場合は pip install -r requirements.txt）

4. .env の作成:
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     このウィザードは .env を生成 / 更新します。デフォルト値や秘密項目のマスク入力に対応。

5. 設定検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

環境変数（主要なもの）
---------------------
（.env で管理する想定）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に書き込む
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使うときに必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring で利用。デフォルト 60）

使い方（主要なスクリプト）
------------------------

1. 設定ウィザード（.env の作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   挙動:
     - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録。
     - 起動時に data/stop_requested.flag が存在する場合は起動しない。
     - data/execution.pid に PID を書き出す。
     - 停止は data/stop_requested.flag を作成することで行える（外部からフラグを立てる）。

4. 監視ループ起動（SystemMonitor）
   - python -m kabusys.run_monitoring
   挙動:
     - Settings による sqlite_path（監視 DB）・duckdb_path を開いて監視を行う。
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
     - 監視ループは data/stop_requested.flag を検出すると終了する。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

6. AI 関連（プログラムから呼ぶ例）
   - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=...)
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=...)

停止・Kill Switch
-----------------
- 外部から実行中エンジンや監視ループを停止するには、プロジェクトルートの data/stop_requested.flag を作成します（scripts はこのファイルの存在を検出してループを終了します）。
- 実行の安全装置として KillSwitch が存在し、リスク基準（ドローダウンやポジション数超過）で data/kill.flag を書き込み、ExecutionEngine 側で停止をトリガできます。
  - KillSwitch をクリアするには Settings.kill_flag_clear_on_start の設定に注意（本番では 0 推奨）。

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - デフォルトでは stdout と logs/<app_name>.log に日次ローテートで出力（30日保持）
  - LOG_DIR 環境変数や引数でログディレクトリを変更可能
  - LOG_LEVEL は環境変数または .env の LOG_LEVEL で制御

監視 DB（SQLite）スキーマ概要
----------------------------
monitoring_db.init_monitoring_db により作成される主なテーブル:
- system_status: cpu/memory/disk/process_ok 等の時系列
- trade_logs: 発注イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, latency_ms 等）
- positions: 現在の保有（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスク関連のアラートログ
- dashboard: 集約（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

開発・リサーチ用モジュール
-------------------------
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary 等。DuckDB 接続を与えて実行。
- kabusys.portfolio: 候補選定 / 重み算出 / ポジションサイズ決定 / セクターキャップ等の純関数群。
- これらは基本的に DB を読み取るかメモリ計算のみで副作用を持ちません（テストしやすい実装）。

主要なディレクトリ構成
--------------------
プロジェクトルート（抜粋）:
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前の設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定
    - monitoring/
      - monitoring_db.py       — 監視 DB 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/               — ExecutionEngine & ブローカー関連（簡潔化）
    - portfolio/               — portfolio_builder, risk_adjustment, position_sizing
    - research/                — factor_research, feature_exploration
    - utils/
      - logging_setup.py
      - process_priority.py
    - tools/
      - paper_verification_report.py
- data/                       — 実行時に作られることが多い（DB, flag, pid など）
- logs/                       — ログ（デフォルト）

注意事項 / ベストプラクティス
-----------------------------
- production（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に注意する（本番では自動クリアを無効化推奨）。
- Paper Trading は本番 DB と明確に分離されます。KABUSYS_ENV=paper_trading を使うと paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
- OpenAI を使用する機能は API キーを要し、使用にはコストとレイテンシが伴います。API の呼び出し失敗時はフォールバック（スコア 0.0 等）しますが、運用ポリシーを定めてください。
- ログディレクトリの作成に失敗した場合はファイル出力が無効になりますが、コンソール出力は行われます。
- DuckDB / SQLite ファイルパスは .env で調整可能です。運用環境では永続領域に置いてください。

補足（実行例）
---------------
- ウィザードで .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視をバックグラウンドで起動（例）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジンを起動（ローカルテスト・Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
------------------
本リポジトリの設計方針や実装上の疑問、貢献（Issue / PR）は README のあるリポジトリに従って行ってください。

（以上）