# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。本リポジトリは、発注エンジン、監視コンポーネント、ポートフォリオ構築、ファクター計算、LLM を用いたニュースセンチメント評価などを含みます。

以下はコードベース（src/kabusys 以下）から作成した README です。

概要
----
KabuSys は以下の主要機能を持ちます。

- 発注実行エンジン（ExecutionEngine）とそれを補助する OrderManager / Reconciler
- 監視（MonitoringEngine） — システム状態、注文滞留、リスク（ドローダウン・ポジション上限）を定期チェックし、アラート/kill-flag を発行
- ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイズ計算、セクター制御、レジーム乗数）
- リサーチ用のファクター計算・特徴量探索（DuckDB を用いた prices_daily / raw_financials 参照）
- AI モジュール（OpenAI を用いたニュースセンチメント評価 / 市場レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード）

主な機能一覧
--------------
- run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper 用 DB と MockBroker を使用して本番 DB と完全分離。
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
- monitoring: system_monitor / trade_monitor / risk_monitor / monitoring_db / alert_manager / kill_switch / MonitoringEngine / Streamlit ダッシュボード
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research: ファクター計算（momentum/value/volatility）・特徴量探索（forward returns, IC, summary）
- ai: ニュース NLP（OpenAI で銘柄ごとに -1.0〜1.0 の ai_score を生成）、regime_detector（ETF の MA とマクロニュースを合成してレジーム判定）
- tools.paper_verification_report: Paper Trading の検証レポートを生成（期間指定可）

前提・依存
-----------
- Python 3.10 以上（コード内で型ヒントの | 記法を使用）
- 主要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使用する場合）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（OpenAI / LINE API / ブローカー API を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化:
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（pip の requirements.txt がある前提。なければ上記パッケージを個別に pip install）:
   pip install duckdb psutil requests openai streamlit

4. data ディレクトリ作成（DB のデフォルト保存先）:
   mkdir -p data

5. 環境変数を設定する (.env または .env.local をプロジェクトルートに置くことで自動読み込みされます)。
   自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（例）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading を指定すると run_execution は paper_sqlite_path を使用し、本番 DB と分離します。
- JQUANTS_REFRESH_TOKEN: （必須）J‑Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）の API キー
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager が LINE 通知を行う際に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill mode（instant / partial / never / reject）

簡易 .env 例
--------------
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

使い方
------
- 監視プロセスを起動（デフォルト 60 秒周期、MONITOR_POLL_INTERVAL で変更可能）:
  python -m kabusys.run_monitoring
  # 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  補足:
  - run_monitoring は Monitoring 用 SQLite（Settings.sqlite_path）を使用します（KABUSYS_ENV に関わらず本番 sqlite_path を参照する実装）。
  - プロセス優先度を high に設定しようとします（psutil 権限が必要）。

- ExecutionEngine を起動（実取引 or paper_trading）:
  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading をセットすると paper 用 DB を使用し、MockBrokerClient が利用されます（本番 DB と完全に分離）。
  - ExecutionEngine は起動時に Reconciler による自動復旧を行います。

- Streamlit ダッシュボードの起動（監視 DB を read-only で開く）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --from YYYY-MM-DD
    --to   YYYY-MM-DD
    --db   PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 機能（ニューススコア / レジーム判定）
  これらはライブラリ API として提供されています（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。
  OpenAI API キー（OPENAI_API_KEY）を設定することが必要です。

重要な挙動・運用ノート
---------------------
- run_monitoring は Settings に基づく sqlite_path を使用します。run_execution は KABUSYS_ENV によって paper 用 DB を使うか判定します。
- kill.flag 機構:
  - RiskMonitor や KillSwitch の評価で異常が検出されると KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine 側はこれを検出して停止します。
  - Settings.kill_flag_clear_on_start が True の場合は実行開始時に kill.flag を自動削除する設定があります。
- プロセス優先度 / CPU affinity:
  - 起動スクリプトはプラットフォームに応じてプロセス優先度や CPU affinity を設定しようとします（psutil を使用）。権限不足時はログに警告が出てスキップします。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要に応じて簡単なカラム追加（マイグレーション）を行います。
- テスト / デバッグ:
  - 環境自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストなどで便利です）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                — パッケージ初期化・バージョン
- config.py                  — Settings クラス（.env 自動読み込み / 環境変数取得）
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py          — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
- trade_monitor.py           — 注文滞留・約定異常監視
- risk_monitor.py            — ドローダウン / ポジション上限監視
- kill_switch.py             — kill.flag の書き込み・評価
- alert_manager.py           — LINE Push 通知（クールダウン管理）
- monitoring_engine.py       — 個別モニタを束ねるループ
- streamlit_dashboard.py     — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py           — OrderState Machine の外向き API
- reconciler.py              — 起動時の注文・ポジション突合（自動復旧）
- （その他：broker_factory, execution_engine, order_repository 等が存在する想定）

src/kabusys/portfolio/
- portfolio_builder.py       — 候補選定・重み計算
- position_sizing.py         — 株数決定・資金配分・単元丸め
- risk_adjustment.py         — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py         — Momentum / Volatility / Value ファクター計算（DuckDB）
- feature_exploration.py     — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py                — raw_news を OpenAI で評価して ai_scores へ書き込み
- regime_detector.py         — MA200 とマクロニュースでレジーム判定

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

src/kabusys/utils/
- process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

補足（開発者向け）
-----------------
- DuckDB を使って prices_daily / raw_financials 等の大規模データを高速に集計できます。research モジュールは DuckDB 接続を受け取り純粋関数として動作します。
- AI 周りは API の失敗に寛容（フェイルセーフ）に設計されています。OpenAI のレスポンスは JSON モードで受け取り、バリデーションを行います。
- ログレベルや細かな閾値は Settings の環境変数で設定できます。コード内のデフォルト値も参照してください。

問い合わせ / 貢献
-----------------
- バグ報告・機能要望は Issue を立ててください。
- コントリビュートは Pull Request を歓迎します。テスト・型注釈と簡潔なドキュメントを添えてください。

以上。README の内容について補足や追記したい項目があれば教えてください。必要ならサンプル .env.example や requirements.txt のテンプレートも作成します。