KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／研究／監視用ライブラリ群です。本リポジトリは以下の主要機能を提供します。

- 注文送信・状態管理（ExecutionEngine, OrderManager, Reconciler 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ計算）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュースを用いた AI スコアリング / 市場レジーム判定（OpenAI 利用）
- Paper Trading の検証レポート生成ツール
- Streamlit による監視ダッシュボード

主な特徴
-------
- モジュール化された純粋関数群（ポートフォリオ・研究機能は DB 依存を限定）
- DuckDB を使った高速なバッチ分析（prices_daily / raw_financials 等を想定）
- SQLite による監視データ永続化（monitoring.db）
- OpenAI を使ったニュースセンチメント評価（API エラーに対する堅牢なリトライ）
- 実行時にプロセス優先度・CPU affinity を設定するユーティリティ（psutil）

必要な依存パッケージ（例）
-------------------------
以下は主要な依存パッケージ例です。プロジェクトに requirements.txt がある場合はそちらを使用してください。

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ...
   - cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   ※実運用ではバージョン管理された requirements.txt を使ってください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動ロードは OS 環境変数を優先）。
   - テスト時に自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に分離して記録します。
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API のパスワード
- KABU_API_BASE_URL: kabus API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID 書き込み先（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（"1" にするとクリア）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（%）

使い方
------

1) 実行エンジン（Execution）
   - 本番／Paper Trading の ExecutionEngine を起動します。起動時に process priority を "high" に設定します。
   - コマンド例:
     - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を指定すると、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

2) 監視ループ（Monitoring）
   - SystemMonitor（監視ループ）を起動して定期的に状態を記録・アラートします。
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
   - コマンド例:
     - python -m kabusys.run_monitoring

   - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視は本番 DB を見る想定）。

3) Streamlit ダッシュボード
   - 監視データを可視化する簡易ダッシュボードです。
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - monitoring.db を読み取り専用で開きます。MonitoringEngine を先に起動して DB を作成してください。

4) Paper Trading 検証レポート
   - 過去期間の paper_trading DB を集計してレポートを出力します。
   - コマンド例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - デフォルト DB パスは data/paper_trading.db。--db で上書き可能。

5) AI（ニュース NLP / レジーム判定）
   - OpenAI の API キーが必要です（OPENAI_API_KEY）。
   - コード API:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらの関数は DuckDB 接続（kabusys.data 側で DuckDB を用意）を受け取り、テーブル群（raw_news, news_symbols, ai_scores, prices_daily 等）を参照します。
   - 実行時は API エラー時のフォールバックや部分失敗に対する堅牢性を備えていますが、API キー未設定時は ValueError を raise します。

運用上のポイント / 注意事項
--------------------------
- PID ファイル: ExecutionEngine は起動時に pid ファイルを書きます。SystemMonitor はその PID を見てプロセス生存確認を行います。stale PID が検出されるとファイルを削除してリスクログに記録します。
- Kill Switch: RiskMonitor 等がトリガー条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側でこの flag を見る実装があることを前提）。
- 環境ファイル読み込み: プロジェクトルート（.git または pyproject.toml を基準）から .env, .env.local を自動読み込みします。OS 環境変数は保護されます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- psutil の優先度設定や CPU affinity は権限が必要な場合があり、設定に失敗すると警告ログが出ます（処理は継続されます）。
- DuckDB / SQLite の書き込み時にはアクセス権限やファイルロックに注意してください（複数プロセスでの同一ファイルアクセスは考慮が必要です）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）

- monitoring/
  - monitoring_db.py             — SQLite 監視 DB 初期化 + DB API
  - system_monitor.py            — システム状態・データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常監視
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag による停止シグナル生成
  - alert_manager.py             — LINE 通知送信ユーティリティ
  - monitoring_engine.py         — 複数 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py       — Streamlit ダッシュボード

- execution/
  - reconciler.py                — 起動時のリコンシリエーション（注文・ポジション突合）
  - order_manager.py             — 注文管理（作成・送信・同期）
  - order_repository.py          — （省略）DB レイヤー（Order 用）
  - ...（BrokerFactory, ExecutionEngine など）

- portfolio/
  - portfolio_builder.py         — 候補選定・重み算出
  - position_sizing.py           — 株数計算・投資上限処理
  - risk_adjustment.py           — セクターキャップ・レジーム乗数

- research/
  - factor_research.py           — モメンタム / ボラ / バリュー 等のファクター計算
  - feature_exploration.py       — 将来リターン・IC・統計サマリー

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

- utils/
  - process_priority.py          — プロセス優先度・CPU affinity 設定ユーティリティ

補足（開発者向け）
-----------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、意図的に環境を固定してください。
- DuckDB 接続には SQL を多用しています。大規模プロセスや並列実行ではファイルロックに注意してください。
- AI モジュールは OpenAI API のレスポンス形式（JSON Mode）に依存しています。API の振る舞い変更に備えてエラーハンドリングが組まれていますが、運用での監視を推奨します。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"
- ライセンス情報はリポジトリのトップレベルファイル（LICENSE 等）を参照してください。

お問い合わせ
------------
不明点や拡張の提案がある場合はリポジトリの issue を作成してください。