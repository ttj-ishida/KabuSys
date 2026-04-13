KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコンポーネント群です。  
本リポジトリはトレード実行エンジン、監視（Monitoring）機能、リサーチ／ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）、ポートフォリオ構築ユーティリティなどを含むモジュール群で構成されています。  
各モジュールは可能な限り副作用を抑え、SQLite / DuckDB をデータ永続化層として利用する設計です。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパー（paper_trading）モードを切り替え可能
  - ブローカークライアントは環境に応じて実装切替（Mock を含む）
  - リスク管理、オーダーマネージャ、リコンシリエーションなどを統合
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard テーブルによる監視データ永続化（SQLite）
  - LINE によるアラート送信（AlertManager）
  - kill.flag を書く KillSwitch による ExecutionEngine 停止シグナル送出
  - streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Research / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算（prices_daily / raw_financials を参照）
  - 将来リターン、IC（Information Coefficient）等の統計的評価
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントの銘柄別スコアリング（ai.news_nlp）
  - マクロニュース + ETF MA200乖離を用いた日次レジーム判定（ai.regime_detector）
  - API 呼び出しには再試行・フェイルセーフの実装あり
- ポートフォリオ構築ユーティリティ
  - 候補選定、等金額／スコア加重配分、セクターキャップ適用、ポジションサイズ計算（単元丸め、集約キャップ適用）
- 補助ツール
  - paper_trading 用の検証レポート生成スクリプト（tools.paper_verification_report）

セットアップ
-----------
前提
- Python 3.10+（PEP 604 の型注釈（X | Y）を使用）
- SQLite（標準で利用可）
- DuckDB（Python パッケージ）

簡単な手順
1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合はそちらを利用）

環境変数（代表的なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は専用の PAPER_TRADING_SQLITE_PATH DB を使います（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な場面あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須な場面あり）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
- PAPER_FILL_MODE: paper_trading 時の Mock の約定モード（instant | partial | never | reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス（デフォルトは data 以下）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

.env の自動ロード
- config.py によりプロジェクトルート（.git または pyproject.toml）を探索し、
  .env（優先度低）→ .env.local（優先度高）の順で自動読み込みを行います。OS 環境変数は上書きされません（ただし .env.local は override=True）。

使い方
------
起動スクリプト
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（秒）。例: export MONITOR_POLL_INTERVAL=30

  特記事項:
  - Monitoring は KABUSYS_ENV に関係なく settings.sqlite_path（本番の monitoring.db）を使用します（監視用は本番 DB を参照する設計）。
  - 実行開始時にプロセス優先度を "high" に設定しようとします（OS / 権限に依存してスキップされる場合あり）。

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用の DB に記録され、MockBrokerClient を使用する想定です。
  - 起動時にリコンシリエーション（照合）やリスク管理が行われます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開き、Overview / Positions / Orders / System のタブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

AI / OpenAI関連
- ai.news_nlp.score_news(conn, target_date, api_key=None) ⇒ ai_scores テーブルへ書き込み
- ai.regime_detector.score_regime(conn, target_date, api_key=None) ⇒ market_regime テーブルへ書き込み
- どちらも OPENAI_API_KEY を指定するか、関数引数で api_key を渡してください。API エラー時はフォールバック挙動（部分失敗の安全性）があります。

プロセス制御 / kill flag
- KillSwitch は条件（ドローダウン超過、ポジション上限超過等）で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側は起動時にこのフラグを検出・クリアするオプション（Settings.kill_flag_clear_on_start）等を提供します。

ログレベル
- LOG_LEVEL 環境変数でログレベルを変更できます（DEBUG, INFO, WARNING, ERROR, CRITICAL）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み・Settings
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ初期化 + DB アクセスラッパ
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — LINE Notifications
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                    — ブローカ連携 / 注文管理系（省略）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py     — Momentum/Volatility/Value 計算
    - feature_exploration.py — forward returns, IC, 統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄別センチメント算出
    - regime_detector.py     — マクロ+MA200 でレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

注意点 / 実運用上のポイント
--------------------------
- DB（monitoring.db / paper_trading.db / kabusys.duckdb）はファイルベースです。運用環境ではバックアップ・配置（ディスク容量）に注意してください。
- Monitoring は monitoring 用 DB を直接操作します。監視情報は重要指標（稼働率・注文成功率・レイテンシ等）を蓄積します。
- OpenAI を利用する機能は API コストとレイテンシを考慮してください。API キーの管理に注意。
- process_priority / cpu_affinity の設定は OS 権限に依存し失敗し得ます（警告ログのみ）。権限昇格が必要な場合があります。
- paper_trading モードは実環境の注文とは分離する設計ですが、設定ミスを避けるため env の確認を行ってください（KABUSYS_ENV）。

開発・拡張
----------
- DuckDB 接続を受け取る設計なので、研究目的で簡単に SQL を投げてテーブルを参照できます。
- AI 呼び出し部分は _call_openai_api を patch することでテスト容易性を確保しています（ユニットテストでモック化可能）。
- portfolio / research の純粋関数群は副作用がないためユニットテストが書きやすいです。

ライセンス / 貢献
-----------------
- 本 README はコードベースの説明用です。実際のライセンスはリポジトリの LICENSE を参照してください。  
- バグ報告・機能拡張は Pull Request / Issue を送ってください。

付録: よく使うコマンド例
-----------------------
- 監視を 30 秒間隔で起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper トレード検証レポート（指定期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

質問や追加で README に載せたい情報があれば教えてください。README をより詳細なインストール手順や運用手順（systemd サービス定義例、バックアップ手順など）に拡張できます。