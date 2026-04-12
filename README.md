KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買に関するコアライブラリ群（Execution、Monitoring、Portfolio Construction、Research、AI 補助）を含む Python パッケージです。モジュール設計は実運用を想定しており、監視・リスク検出・Paper Trading（検証）機能や、OpenAI を用いたニュース NLP／レジーム判定などを備えます。

主な特徴
--------
- 実行エンジン（ExecutionEngine）および発注管理（OrderManager / Reconciler）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE Push）
- 監視 DB（SQLite）と分析用 DB（DuckDB）を分離して管理
- Paper Trading モード（本番 DB と分離して data/paper_trading.db に記録）
- Portfolio construction（候補選定・重みづけ・サイズ計算・セクター制限）
- Research モジュール（ファクター計算、将来リターン、IC、統計サマリ）
- AI 補助：ニュースセンチメント（OpenAI）による ai_scores 書込み、マクロセンチメントと ma200 からのレジーム判定
- Streamlit ベースの監視ダッシュボード（read-only モードで監視 DB を表示）
- フェイルセーフ設計（DB マイグレーション、リトライ、部分書込みの保護）

セットアップ手順
----------------

1. Python 環境を準備
   - Python 3.9+ を推奨
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（代表的な依存）
   - pip install psutil duckdb requests openai streamlit
   - ※ 実際の環境では requirements.txt を用意している場合はそちらを使ってください。

3. プロジェクトルートの .env 読み込み
   - このパッケージは起動時に自動でプロジェクトルートの .env / .env.local を読み込みます（CWD に依存せず、__file__ を基準に .git または pyproject.toml を探索）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ作成
   - デフォルトで data/ 以下に DB 等が作成されます。必要に応じて作成してください。
     - mkdir -p data

5. 必須環境変数
   - JQUANTS_REFRESH_TOKEN (J-Quants API 用)
   - KABU_API_PASSWORD (kabuステーション API 用)
   - 上記が未設定の場合、Settings のプロパティ参照で ValueError が発生します。
   - OpenAI を利用する機能を使う場合は OPENAI_API_KEY を設定してください。

主要な環境変数（主なもの）
--------------------------
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- SQLITE_PATH: 監視 DB path（デフォルト: data/monitoring.db）
- DUCKDB_PATH: 分析用 DuckDB path（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信をスキップ）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行中プロセス PID / 停止フラグファイルのパス
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効）

基本的な使い方
--------------

1. 監視ループの起動（SystemMonitor をポーリング）
   - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で変更可能（デフォルト 60）
   - 起動:
     - python -m kabusys.run_monitoring
   - 動作:
     - プロセス優先度を high に設定し、sqlite（monitoring DB）と DuckDB に接続して SystemMonitor を定期実行します。
     - monitoring DB のテーブル（system_status / trade_logs / positions / risk_logs / dashboard）は自動で作成・マイグレーションされます。

2. 実行エンジン（ExecutionEngine）起動
   - 本番/ペーパートレードの切替:
     - KABUSYS_ENV=paper_trading を指定すると MockBroker を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
   - 起動:
     - python -m kabusys.run_execution
   - 動作:
     - ブローカークライアント作成 → OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を実行します。
     - 起動時にリコンシリエーション（未決注文の同期）を行います。

3. Streamlit 監視ダッシュボード
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - read-only で monitoring DB を開き、Overview / Positions / Orders / System タブを表示します。

4. Paper Trading 検証レポート生成
   - コマンド:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db で SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

5. AI 機能（ニュース NLP / レジーム判定）
   - 要: OPENAI_API_KEY（引数でも渡せます）
   - プログラムから呼び出し例（簡易）:
     - from kabusys.ai.news_nlp import score_news
       score_news(duckdb_conn, target_date, api_key="...")

     - from kabusys.ai.regime_detector import score_regime
       score_regime(duckdb_conn, target_date, api_key="...")

   - 機能:
     - news_nlp.score_news: raw_news を銘柄ごとに集約し OpenAI に送って ai_scores テーブルを更新します。最大バッチサイズやトークン制限・リトライを実装。
     - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成し market_regime に書き込みます。

注意点 / 運用上のポイント
-------------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring / Execution 起動時にプロセス優先度を上げる試みを行います（psutil 使用）。権限不足や非対応 OS の場合は警告が出てスキップされます。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（運用監視は常に実 DB を参照するため）。
- Paper Trading モードは本番 DB と完全に分離され、PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI API 呼び出しは外部ネットワーク依存であり、429 / network / 5xx 等の一時エラーに対して指数バックオフでリトライする実装です。API キーの制限やコストに注意してください。
- kill.flag による ExecutionEngine の停止シグナル機構があります。KillSwitch はリスク（ドローダウン・ポジション上限等）に応じてファイルを書き込みます。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__）
  - config.py                  — 環境変数 / Settings 管理（.env ロード含む）
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 監視 DB 初期化・永続層
    - system_monitor.py        — システム・データ鮮度チェック
    - trade_monitor.py         — 注文滞留・約定異常チェック
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 制御
    - alert_manager.py         — LINE push 通知
    - monitoring_engine.py     — 複数モニタ束ねてポーリング
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py         — 発注管理（OrderState Machine 入口）
    - reconciler.py            — 再起動時リコンシリエーション
    - (その他: broker_factory, execution_engine, order_repository など実装済みを想定)
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - position_sizing.py       — 株数決定・単元丸め
    - __init__.py
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — マクロ + MA200 合成によるレジーム判定
    - __init__.py
  - utils/
    - process_priority.py      — process priority / cpu affinity ユーティリティ
    - __init__.py

開発者向けメモ
---------------
- DB マイグレーションは簡易に init_monitoring_db 内で行われます（列追加などのチェック）。
- DuckDB を用いるモジュールは接続オブジェクトを受け取り SQL と Python を組み合わせて処理します（副作用を避ける設計）。
- OpenAI 呼び出しはモジュール内でラップされており、ユニットテストでは該当関数をモックして外部呼び出しを回避してください（ドキュメント内にモック対象関数名の記述あり）。
- Logging は基本 INFO レベルで設定されています。細かいデバッグは環境変数 LOG_LEVEL を設定して変更できます。

簡単な .env 例（テンプレート）
------------------------------
以下は最低限の例（実運用では秘密情報を安全に管理してください）。

- .env
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - OPENAI_API_KEY=...
  - KABUSYS_ENV=development
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LINE_CHANNEL_ACCESS_TOKEN=    # LINE 通知を使う場合に設定
  - LINE_USER_ID=

ライセンス / 貢献
-----------------
（この README では記載していません。実プロジェクトでは LICENSE と CONTRIBUTING を追加してください）

問い合わせ
----------
使い方や障害時の挙動について不明点があれば、コード内の docstring（各モジュール先頭）を参照してください。必要であれば README を拡張して具体的なデプロイ手順（systemd ユニット、cron、Docker）や監視運用手順を追記します。