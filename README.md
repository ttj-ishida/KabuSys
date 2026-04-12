KabuSys
=======

日本株向けの自動売買システム（ライブラリ/ツール群）。  
戦略のポートフォリオ構築、ポジションサイズ決定、実行エンジン、監視、研究用ファクター計算、AIによるニュースセンチメント評価などの機能を含みます。

この README はコードベース（src/kabusys 以下）から抜粋して日本語で要点をまとめたものです。

概要
----
KabuSys は以下の主要コンポーネントを提供します。

- 実行コンポーネント（ExecutionEngine 等）: ブローカーへ発注し、注文状態管理・リスク管理を行う。
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使い、paper_trading 用 SQLite に記録して本番 DB と分離します。
- 監視コンポーネント（MonitoringEngine）: システム状態、注文滞留、ドローダウンなどをポーリング監視し、ログとアラートを出す。
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、リスク調整、数量算出（単元株丸めなど）。
- 研究用モジュール（research）: DuckDB を使ったファクター計算・将来リターン計算・IC 計算など。
- AI モジュール（ai）: OpenAI を利用してニュースのセンチメント評価や市場レジーム判定を行う。
- ツール: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボードなど。

主な機能一覧
-------------
- 環境変数読み込み（.env, .env.local の自動読み込み。無効化可能）
- Settings クラスによる集中設定管理（KABUSYS_ENV / DB パス / API キー等）
- Execution 系
  - 注文作成→送信→同期（リコンシリエーション）を行う OrderManager / Reconciler
  - paper_trading モードで本番 DB と分離
- Monitoring 系
  - SystemMonitor: CPU/メモリ/ディスク、PID 存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文チェック、約定価格異常検出
  - RiskMonitor: ドローダウン、ポジション上限監視・イベントログ
  - KillSwitch: 条件により ExecutionEngine 停止指示（flag ファイル書き込み）
  - AlertManager: LINE Push を用いた通知（クールダウンあり）
  - Streamlit ダッシュボードで可視化
- AI 系
  - news_nlp: ニュースを銘柄ごとに集約し OpenAI でセンチメントを付与、ai_scores に保存
  - regime_detector: MA200 とマクロニュースを組み合わせて市場レジーム判定
- Research / Data
  - DuckDB 接続を受けてファクター（momentum / volatility / value）や将来リターンを計算
- Tools
  - Paper Trading 検証レポート生成スクリプト（成功率・レイテンシ・稼働率の判定）

セットアップ手順
----------------
前提
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨: 仮想環境（venv / pyenv など）

依存ライブラリ（代表例）
- duckdb
- psutil
- openai
- requests
- streamlit

例: 仮想環境作成と最低限パッケージのインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください）

環境変数 / .env
- プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（OS 環境変数優先）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（空なら送信されません）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT など（Settings に多数あり）

使い方（コマンド例）
-------------------

モジュール実行（パッケージとして）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を変更する例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - paper_trading モードで起動するには:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - paper_trading モードは paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離されます。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

AI / リサーチ
- news_nlp / regime_detector は OpenAI API を使用します。実行前に OPENAI_API_KEY を設定してください。
- Research モジュールは DuckDB 接続を受けてファクターやIC を計算します。prices_daily / raw_financials 等のテーブルが必要です。

設定の振る舞い（主要ポイント）
- .env/.env.local はプロジェクトルート（.git または pyproject.toml のある場所）を基準に自動検出して読み込みされます。
- .env.local は .env の上書き（override=True）として読み込まれますが、もともと OS 環境変数にあるキーは保護されます。
- Settings クラス経由で各種設定を取得できます。必須キーが未設定の場合はエラーになります（_require を通じて ValueError）。

主要ファイル / ディレクトリ構成
-----------------------------
（コードベースの主要なファイルと各役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込みロジック、Settings クラス（集中設定管理）
  - run_monitoring.py
    - SystemMonitor をポーリングする起動スクリプト。MONITOR_POLL_INTERVAL による間隔制御。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。KABUSYS_ENV による paper_trading 切替。
  - execution/
    - reconciler.py — 起動時の注文・ポジション突合
    - order_manager.py — 注文状態遷移・ブローカー呼び出しを管理
    - order_repository.py, order_record.py, broker_factory.py, risk_manager.py など（発注周り）
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視用 DB 層（init_monitoring_db）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/PID/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag を書いて ExecutionEngine を停止させる
    - alert_manager.py — LINE への通知（プッシュ）
    - monitoring_engine.py — 監視モジュールを束ねるエンジン（run/run_once）
    - streamlit_dashboard.py — Streamlit でのダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定、等重・スコア重み計算
    - position_sizing.py — 株数決定、aggregate cap、単元株丸め
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py — ニュースをまとめて OpenAI でセンチメントスコア化し ai_scores に書込
    - regime_detector.py — MA200 とマクロニュースで日次レジーム判定
  - tools/
    - paper_verification_report.py — paper_trading の検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

データベース（監視用）スキーマ（監視用 SQLite）
- init_monitoring_db() により以下テーブルが作成されます（冪等）:
  - system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
  - trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
  - positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
  - risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
  - dashboard (id=1 の単一行保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)
- マイグレーションロジック: 必要に応じて列追加（例: trade_logs.latency_ms, dashboard.peak_value）

注意事項 / 運用上のポイント
------------------------
- paper_trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- AI 呼び出し（OpenAI）は API エラー・レート制限に対してリトライやフォールバック（0.0）を適用するなどフェイルセーフ実装がされていますが、API キーの管理は必須です。
- PID ファイル（Settings.pid_file_path）を用いて ExecutionEngine の生存チェックを行います。stale PID の検出時はファイルを削除してログに記録します。
- KillSwitch は flag ファイル（Settings.kill_flag_path）を書き込むことで ExecutionEngine 停止を誘導します。起動時に既存フラグをクリアするオプション（KILL_FLAG_CLEAR_ON_START）があります。
- LINE 通知は channel_access_token / user_id が空の場合は送信をスキップします。
- .env のパース実装はシェル風の quoted/escaped 値、コメント処理に対応していますが、フォーマットは .env.example を参照してください（リポジトリに例ファイルを置くことを推奨します）。

開発・テスト
------------
- モジュール単位でのテストを想定した設計（関数が副作用を最小化、外部 API 呼び出しは差し替え可能）。
- OpenAI 呼び出し部分はテスト時にモック化（patch）して使えるようになっています。
- MonitoringEngine.run_once() を使うことで 1 回だけ監視処理を実行して単体テストできます。

ライセンス / 貢献
-----------------
（この README に含まれていない既定のライセンスファイルがプロジェクトに含まれているはずです。プロジェクトルールに従ってください）

最後に
-----
この README はコードからの抜粋に基づく概要ドキュメントです。運用前に .env.example（存在する場合）を確認し、必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を設定してください。各モジュールの詳細な API やパラメータはソース内の docstring やコメントを参照してください。