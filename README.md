KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。  
本リポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を用いたセンチメント評価）などの機能を提供します。  
主要コンポーネントは純粋関数 / モジュール化を意識して設計されており、SQLite / DuckDB をデータ層として利用します。

主な機能
--------
- ExecutionEngine
  - ブローカークライアント経由の注文送信・状態同期（再起動時のリコンシリエーションを含む）
  - Paper Trading（KABUSYS_ENV=paper_trading）用のモックブローカー・専用 DB
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring
  - システム状態・データ鮮度監視（CPU / メモリ / ディスク / 実行プロセスの存在）
  - 注文滞留・約定異常監視
  - KillSwitch（ファイルフラグで ExecutionEngine 停止指令）
  - LINE Push によるアラート送信
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定、等重/スコア重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）、将来リターン、IC（Information Coefficient）
  - DuckDB を用いたオフライン計算
- AI（OpenAI 統合）
  - ニュース記事のセンチメントスコアリング（ai_scores テーブルへ保存）
  - 市場レジーム判定（ma200 乖離 + マクロニュースセンチメント）

セットアップ
------------
1. Python 環境（推奨: Python >= 3.10）を準備
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主な依存ライブラリ（例）
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - （プロジェクトによって追加依存がある場合は requirements.txt を参照してください）

3. 環境変数／.env
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（OS 環境変数を上書きしない挙動）。
   - 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（一部）
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
     - KABU_API_PASSWORD — kabuステーション API（必須）
     - OPENAI_API_KEY — OpenAI を利用する場合（AI モジュール、任意だが機能するには必要）
     - KABUSYS_ENV — 実行環境: development | paper_trading | live (デフォルト: development)
     - PAPER_FILL_MODE — paper_trading の注文約定挙動: instant | partial | never | reject (default: instant)
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite DB（default: data/paper_trading.db）
     - SQLITE_PATH — 監視ログ用 SQLite（default: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH — プロセス監視 / kill フラグ用ファイルパス
     - LOG_LEVEL — ログレベル (DEBUG, INFO, ...)

使い方
------

起動スクリプト
- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト: 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番DBへ）

- ExecutionEngine の起動（実行部）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、data/paper_trading.db に記録されます（本番 DB と完全分離）。
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。

Paper Trading 検証レポート
- コマンドラインツール:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from / --to: レポート期間 (YYYY-MM-DD)
    - --db: SQLite ファイルパスを直接指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

Streamlit ダッシュボード
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - Dash の側では SQLite を読み取り専用で開きます。MonitoringEngine を先に動かしてデータを生成してください。

AI / OpenAI 関連
- ニュースのスコアリング（Python API）
  - 例:
    - import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - 必要: OPENAI_API_KEY（引数で上書き可）
- レジーム判定
  - 同様に kabusys.ai.regime_detector.score_regime を呼び出して market_regime テーブルへ書き込み

注意事項 / 実運用メモ
- Monitoring は常に sqlite_path（デフォルト data/monitoring.db）を使用します。環境にかかわらず監視ログは本番 DB を想定。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用して本番データと分離します。
- .env の自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使います。CI 等で異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を検討してください。
- process priority / cpu affinity の設定は psutil に依存します。権限不足で設定に失敗することがあるためログを確認してください。
- OpenAI API 呼び出しでは RateLimit/Timeout/5xx に対してリトライやフォールバック（macro_sentiment=0 やスキップ）する実装になっていますが、APIキーと利用料に注意してください。
- KillSwitch は指定パス（デフォルト data/kill.flag）へのファイル書き込みで ExecutionEngine 停止を指示します。ExecutionEngine 側はこのフラグを参照して停止する設計です。

ディレクトリ構成（抜粋）
----------------------
主要ファイル・モジュールの階層（コードベースから抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env ロード / Settings
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py         — システム状態 / データ鮮度監視
    - trade_monitor.py          — 注文滞留 / 価格異常監視
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - kill_switch.py            — kill.flag 書き込みユーティリティ
    - alert_manager.py          — LINE Push 通知
    - monitoring_engine.py      — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py    — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (他、ブローカー関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — マクロセンチメント + MA200 でレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py

開発 / テスト
--------------
- 単体関数は純粋関数として実装されている箇所が多く、ユニットテストが書きやすい設計です（DuckDB / SQLite の接続をモック化してテスト可能）。
- OpenAI 呼び出しや外部 API 呼び出しは関数単位で抽象化（テスト時にモック化しやすいよう設計されています）。

ライセンス / 貢献
----------------
- 本 README にはライセンス情報が含まれていません。実際の配布では LICENSE ファイルを設置してください。  
- バグ報告・プルリクエスト歓迎です。大きな変更は issue で事前に相談してください。

付録: よく使うコマンドまとめ
----------------------------
- 監視起動:
  - python -m kabusys.run_monitoring
- Execution 起動:
  - python -m kabusys.run_execution
  - Paper Trading:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上。必要であれば README の英語版や、環境ごとの起動例（systemd ユニット、Dockerfile、Compose）などの追記も作成します。どの内容を優先して追加しますか？