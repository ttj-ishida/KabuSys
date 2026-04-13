README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を目的とした軽量な Python コードベースです。
主要機能は以下の通りです:

- 注文管理・発注エンジン（ExecutionEngine）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（RiskManager）とポジションサイズ計算（Portfolio モジュール）
- 監視サブシステム（System / Trade / Risk モニタ）とアラート（LINE）
- Paper Trading 用の分離された DB モード
- DuckDB を用いたファクター計算・リサーチ
- ニュースの LLM（OpenAI）によるセンチメントスコアリングと市場レジーム判定
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

特徴
----
- 設定は環境変数 / .env ファイルで管理（自動読み込み機能あり）
- Paper Trading（KABUSYS_ENV=paper_trading）時はモックブローカーを使い、本番 DB とは分離
- 監視は SQLite（monitoring.db）へログを永続化、DuckDB は時系列/リサーチ用に利用
- OpenAI を用いたセンチメント評価は失敗時に堅牢にフォールバック（フェイルセーフ設計）
- プロセス優先度・CPU affinity 設定ユーティリティで運用環境に配慮

セットアップ
------------
前提
- Python 3.9+（コードは型アノテーションや modern stdlib を利用）
- SQLite（標準ライブラリで利用可能）
- 必要な Python ライブラリ（下記）

推奨インストール手順（仮想環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール（例）
   - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を置く（任意）
   - プロジェクトは起動時に自動で .env / .env.local を読み込みます（OS 環境変数を上書きしない挙動）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（必須 / 推奨）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルトは development。
  - paper_trading の場合、別 SQLite（PAPER_TRADING_SQLITE_PATH）が使用されます。
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject、デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH: ExecutionEngine の PID / kill flag 用パス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

注意: Settings クラスは起動時に環境変数の検証を行います。不正な値だと起動時に例外が発生します。

使い方（起動・コマンド）
-----------------------

1) 監視ループ（SystemMonitor 単体）
- 目的: system_status / trade_logs / risk_logs / dashboard などの監視を継続して記録
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）

ポイント:
- 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
- 監視は Settings.sqlite_path を常に使用（KABUSYS_ENV に依存せず本番 DB を参照します）。

2) 実行エンジン（ExecutionEngine）
- 目的: ブローカー接続、OrderManager、RiskManager、Reconciler を組み立ててトレードを実行
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
  - 起動時にリコンシリエーション（未確定注文の突合）を行い、安全にセッションを再開します。

3) Paper Trading 検証レポート
- 目的: Paper Trading DB の稼働率・注文成功率・レイテンシなどを集計してレポート出力
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

4) Streamlit ダッシュボード（監視 UI）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用で SQLite を開き、Positions / Orders / System / Overview を表示します。

5) AI 機能（ニューススコアリング、レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols -> ai_scores に銘柄別センチメントを書き込む
  - OPENAI_API_KEY を設定（または api_key 引数）
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込み
- 注意:
  - OpenAI 呼び出しは再試行やエラー時のフォールバックが組み込まれていますが、API キー未設定時は ValueError を送出します。

運用上の重要点
---------------
- kill.flag:
  - KillSwitch はリスク閾値（ドローダウン超過、ポジション上限超過等）で data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 起動時に flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START）があります。
- PID ファイル:
  - ExecutionEngine は起動時に PID を data/execution.pid に書き、SystemMonitor は PID の存在・生存確認でプロセス状態を判定します。stale PID は自動で削除されアラート記録されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は idempotent にテーブルを作成し、既存 DB にないカラムを追加する簡易マイグレーションを含みます（例: peak_value, latency_ms）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト（paper_trading 分離対応）

subpackages:
- kabusys/monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py            — 注文滞留・約定異常監視
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — flag ファイルによる停止シグナル管理
  - alert_manager.py            — LINE Push 通知ラッパー
  - monitoring_engine.py        — 複数モニタの束ねとポーリング
  - streamlit_dashboard.py      — Streamlit ベースの監視ダッシュボード

- kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py         — (一部実装がこの README には含まれていませんが存在)
  - execution_engine.py         — Engine 組み立て / run_session（主要実行ロジック）

- kabusys/portfolio/
  - portfolio_builder.py        — 候補選定・weight 計算
  - position_sizing.py          — 株数計算・aggregate cap
  - risk_adjustment.py          — セクター上限・レジーム乗数
  - __init__.py

- kabusys/research/
  - factor_research.py          — momentum/volatility/value ファクター計算（DuckDB）
  - feature_exploration.py      — 将来リターン計算・IC・統計サマリ
  - __init__.py

- kabusys/ai/
  - news_nlp.py                 — raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py          — マクロニュース + ETF MA200 合成によるレジーム判定
  - __init__.py

- kabusys/utils/
  - process_priority.py         — プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

- kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - __init__.py

ライセンス・貢献
----------------
- 本リポジトリにライセンス表記がない場合は利用前に著作権者に確認してください。
- バグ修正や機能追加は Pull Request を歓迎します。テスト・型チェックの追加を推奨します。

補足（よくある質問）
-------------------
Q. Paper Trading と本番 DB はどのように分離されていますか？
A. KABUSYS_ENV=paper_trading のとき、run_execution は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視側は別 DB（monitoring.db）を参照する点に注意してください。

Q. .env の読み込みを無効にできますか？
A. はい。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップします。

Q. OpenAI の呼び出しでキーがないとどうなりますか？
A. AI 機能（news_nlp.score_news, regime_detector.score_regime）は API キーが未設定だと ValueError を送出します。運用バッチでの自動実行時は必ずキーを設定してください。

以上がこのコードベースの概要と起動・運用のための基本的な手引きです。運用前に settings（環境変数）を確認し、データベースや LINE の通知設定などを整えてください。必要ならば README に例となる .env.example を追加することを推奨します。