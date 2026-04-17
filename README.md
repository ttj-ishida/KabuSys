KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小規模なフレームワークです。  
主な機能は以下のとおりです。

- 実取引 / ペーパートレードに対応した ExecutionEngine（発注・リコンシリエーション・リスク管理）
- システム状態・注文の監視（監視ログの永続化・LINE 通知・Kill Switch）
- ポートフォリオ構築ユーティリティ（候補選定・重み算出・ポジションサイズ計算・セクター制約）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- ニュースの NLP スコアリング / 市場レジーム判定（OpenAI API を利用）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 検証レポート生成ツール

主な設計方針:
- DuckDB / SQLite をデータ層に利用。DuckDB は時系列ファクター計算、SQLite は監視ログ／注文ログ等に使用。
- 本番環境と Paper Trading を分離（Paper は専用 SQLite を使用）。
- 外部 API 呼び出し（OpenAI 等）は明示的に API キーを渡すか環境変数で設定。
- ルックアヘッドバイアスを避ける設計（target_date を外部から渡す等）。

機能一覧
--------
- Execution
  - Broker 抽象化（実・モック切替）
  - OrderManager / OrderRepository / Reconciler による起動時の自動復旧
  - RiskManager（注文レート制限・ポジション上限等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検知
  - RiskMonitor: ドローダウン / ポジション数監視とログ記録
  - KillSwitch: 条件により Execution を停止するフラグファイル出力
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（data/monitoring.db を read-only で参照）
- Research / AI
  - ファクター計算（momentum, volatility, value）
  - forward returns / IC / 統計サマリー
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメントの集約スコア化（ai_scores テーブルへ書込）
  - regime_detector: MA200 とマクロセンチメントを合成した市場レジーム判定（market_regime テーブルへ書込）
- Tools
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを生成

セットアップ手順（ローカル）
---------------------------
以下は一般的な開発環境向け手順の例です。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要依存（本リポジトリで使用されるものの例）:
     - duckdb, psutil, openai, requests, streamlit

   例（明示的にインストールする場合）:
   - pip install duckdb psutil openai requests streamlit

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env を置くか環境変数を直接設定できます。
   - 自動で .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（Settings で参照され、実行に必須なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 便利な設定（デフォルト値あり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
     - DUCKDB_PATH: data/kabusys.duckdb
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信に必要

6. (任意) .env.example を参考に .env を作成してください（リポジトリに含めていない場合は README を参照）。

使い方（実行方法）
-----------------

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依存せず本番DBを参照）。

- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番DBと分離されます。
  - 実行中は data/execution.pid を作成、停止は data/stop_requested.flag または KillSwitch による data/kill.flag で制御されます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で参照します。MonitoringEngine が DB を作成・更新している必要があります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

- AI / リサーチ系のプログラム的利用
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - calc_momentum(duckdb_conn, target_date)

停止・フラグファイル
-------------------
- run_monitoring はリポジトリルートの data/stop_requested.flag を監視しており、存在するとループを抜けます。
- run_execution も同様に data/stop_requested.flag を見て起動を抑止したり停止します。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Execution 側は kill.flag を見て停止する設計になっています）。
- 実行開始時に kill_flag_clear_on_start 設定で起動時に kill.flag を自動削除できます（Settings.kill_flag_clear_on_start）。

注意事項 / 運用メモ
-----------------
- Settings は .env /.env.local を自動読み込みします（プロジェクトルートは .git または pyproject.toml で検出）。
- run_monitoring / run_execution はプロセス優先度を set_process_priority("high") で上げようとします。psutil の権限により失敗することがありますがログ警告が出てスキップします。
- OpenAI を使う機能は API キーが必須です。API 呼び出しはリトライやフェイルセーフ（失敗時はデフォルト値で継続）を組み込んでいますが、実運用では API コストとスロットリングに注意してください。
- DuckDB / SQLite のファイルパスは Settings で変更できます。Paper Trading は専用 SQLite を使用することで本番DBと分離しています。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要モジュールと説明です。

- src/kabusys/
  - __init__.py                     — パッケージ情報
  - config.py                       — 環境変数 / 設定管理（Settings）
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
- src/kabusys/monitoring/
  - monitoring_db.py                — SQLite による監視ログ永続化層（MonitoringDB、init_monitoring_db）
  - system_monitor.py               — システム状態・データ鮮度監視
  - trade_monitor.py                — 注文滞留・約定異常監視
  - risk_monitor.py                 — ドローダウン・ポジション上限監視
  - kill_switch.py                  — kill.flag 書込ロジック
  - monitoring_engine.py            — 各 Monitor をまとめるエンジン（テスト用 run_once / 本番 run）
  - alert_manager.py                — LINE 通知用（クールダウン管理）
  - streamlit_dashboard.py          — Streamlit ダッシュボード（起動コマンドあり）
- src/kabusys/execution/
  - order_manager.py                — 注文状態管理（OrderManager）
  - order_repository.py             — SQLite による注文永続化（OrderRepository）
  - reconciler.py                   — 起動時の照合・復旧処理
  - execution_engine.py / ...       — （省略されているが実行ロジック）
  - broker_factory.py / broker_api  — ブローカー抽象化、Mock/実装の切替
- src/kabusys/portfolio/
  - portfolio_builder.py            — 候補選定・重み計算
  - position_sizing.py              — 株数決定・バッファリング・丸め処理
  - risk_adjustment.py              — セクター制約・レジーム乗数
- src/kabusys/research/
  - factor_research.py              — momentum / volatility / value 計算（DuckDB）
  - feature_exploration.py          — forward returns / IC / summary
- src/kabusys/ai/
  - news_nlp.py                     — ニュース集約・OpenAI による銘柄別スコアリング
  - regime_detector.py              — MA200 とマクロセンチメントを合成したレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py    — Paper Trading DB を解析してレポートを出力
- src/kabusys/utils/
  - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ

ログ / DB / 一時ファイル
-----------------------
- デフォルトの SQLite（監視）: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- DuckDB（時系列データ）: data/kabusys.duckdb
- PID / フラグ:
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag

貢献 / テスト
-------------
- 小さな変更でも PR を歓迎します。ユニットテストを追加するとマージがスムーズです。
- モジュールは純関数で実装されている箇所が多く、単体テストが書きやすい設計です（research / portfolio 等）。

連絡
----
不明点や実運用に向けた改善提案があれば Issue や PR をお寄せください。

補足（よく使うコマンド例）
-------------------------
- 監視を 30 秒間隔で起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution を Paper Trading モードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

以上。必要であれば README の英語版や運用手順（systemd / supervisor / docker-compose 用の例）も作成できます。