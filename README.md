# KabuSys

日本株向け自動売買システムのコードベース README（日本語）

以下はリポジトリ内の主要コンポーネント・セットアップ・起動方法・ディレクトリ構成の説明です。開発者向けの簡潔なリファレンスとして利用してください。

注意: 本ドキュメントはソースコード（src/kabusys 以下）からの参照に基づいています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主要な機能群は次の通りです。

- 注文生成・送信・状態管理（Execution）
- 監視（Monitoring）：システム状態・注文滞留・リスク監視、アラート送信（LINE）
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクター制約）
- リサーチ（ファクター計算、将来リターン・IC 等の解析）
- AI 利用機能（ニュースの NLP スコアリング、レジーム判定。OpenAI API を利用）
- ツール（Paper Trading の検証レポート、Streamlit ダッシュボード 等）

設計方針の一部:
- DuckDB/SQLite をデータ層に利用（prices_daily / raw_financials / monitoring DB 等）
- 環境変数 / .env による設定管理（kabusys.config.Settings）
- Paper Trading モードは本番 DB と分離（専用 SQLite ファイル）
- 外部 API 呼び出しはフェイルセーフにして継続性を重視

---

## 主な機能一覧

- Execution（起動スクリプト: run_execution.py）
  - Broker クライアントの生成（本番 or Mock・paper_trading）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine 組み立て
  - 起動時のリコンシリエーション（未確定注文やポジション差分の整合）

- Monitoring（起動スクリプト: run_monitoring.py）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス状態を監視
  - TradeMonitor: 注文滞留、約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch / AlertManager: 条件に応じて停止フラグを書き込み・LINE通知
  - Streamlit ダッシュボード（読み取り専用）

- Portfolio（銘柄選定・重み算出・ポジションサイズ計算）
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes（単元株丸め・aggregate cap 等に対応）

- Research（ファクター計算・特徴量探索）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - DuckDB 接続を受け取り SQL / Python でデータを算出

- AI（OpenAI を利用）
  - news_nlp.score_news: raw_news を集約して銘柄別センチメントを LLM で採点し ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロニュースの LLM 評価を合成し market_regime に書き込む

- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを標準出力に出す
  - monitoring.streamlit_dashboard: Streamlit による監視ダッシュボード（read-only）

---

## 必要条件（依存関係）

最低限のライブラリ（コードから参照されたもの）:
- Python 3.9+（型注釈や構文に依存）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- その他標準ライブラリ

依存関係はプロジェクト側で requirements.txt / pyproject.toml がある場合はそちらを参照してください。ない場合は手動でインストールしてください（例）:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

3. 依存関係をインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記の主要パッケージを手動でインストール）

4. data ディレクトリの作成（初回起動時に自動で作成されることもありますが明示的に作ると便利）
   mkdir -p data

5. 環境変数の設定
   プロジェクトルートに .env（または .env.local）を置くことで自動ロードされます。
   主要な環境変数（例）:
   - KABUSYS_ENV=development|paper_trading|live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...  # AI 機能を使う場合必須
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - MONITOR_POLL_INTERVAL=（秒、監視プロセスのポーリング間隔、デフォルト 60）

   注意: Settings.require を通じて必須チェックされる変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと起動時に例外になります。

6. DB の初期化
   - monitoring 用の SQLite（デフォルト data/monitoring.db）は run_monitoring や run_execution が内部で init_monitoring_db を呼ぶため、最初の起動で自動作成されます。
   - DuckDB（デフォルト data/kabusys.duckdb）はデータ投入処理（別途の ETL）で準備する想定です。

---

## 使い方（起動・ツール）

基本的にモジュールのエントリポイントとして Python の -m を使うか、直接スクリプトを実行します。

1. 監視プロセス（Monitoring）
   - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
   - 実行例:
     python -m kabusys.run_monitoring
   - 停止:
     - プロセスを Ctrl+C で停止できます。
     - 外部から停止フラグを設定する場合はプロジェクトルートの data/stop_requested.flag を作成するとループ検知で終了します。

2. 実行エンジン（Execution）
   - KABUSYS_ENV により paper_trading モードでは MockBroker を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
   - 実行例:
     python -m kabusys.run_execution
   - 停止:
     - 同様に Ctrl+C または data/stop_requested.flag を作成しても終了処理が行われます。
   - 実行中は PID が data/execution.pid に書き込まれます。SystemMonitor はこれを監視してプロセス生存確認を行います。

3. Streamlit ダッシュボード（監視用）
   - 実行例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を読み取り専用で開きます。

4. Paper Trading 検証レポート
   - 実行例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     または DB を指定:
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   - デフォルトで PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照します。

5. AI 機能
   - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数）。
   - news_nlp.score_news(conn, target_date, api_key=None)
     - raw_news / news_symbols からニュースを集約して ai_scores に書き込みます。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルへレジーム判定を保存します。

6. 停止 / 強制停止フラグ
   - Execution の安全停止用 kill.flag:
     - KillSwitch.write 相当処理で data/kill.flag が書かれると ExecutionEngine 起動時に検出できます（Settings.kill_flag_path で場所指定可能）。
     - KillSwitch.clear() で削除可能（起動時に clear するオプションがあります）。
   - stop_requested.flag:
     - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を監視し、存在するとループを抜けて安全終了します。

---

## 設定 (Settings) と .env の挙動

- 設定は kabusys.config.Settings で提供されます。環境変数または .env/.env.local から読み込みます。
- 自動ロードの優先順位:
  OS 環境変数 > .env.local > .env
- 自動ロードを無効にする:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードをスキップします（テスト等で利用）。
- 必須変数が未設定の場合は Settings._require() により ValueError が発生します（起動を止める）。

主な設定キー（例）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能利用時必須）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject）
- LOG_LEVEL（INFO 等）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）

---

## よくあるトラブルと対処

- 起動時に ValueError: 環境変数 'X' が設定されていません
  - .env または環境変数を確認し、必要なキーを設定してください。

- OpenAI 呼び出しでエラーが出る / スコアが書き込まれない
  - OPENAI_API_KEY（環境変数または関数引数）を確認。
  - API のレート制限・一時エラーは実装側でリトライしていますが、APIキーの権限や課金状態を確認してください。

- Monitoring / Execution がすぐ終了してしまう
  - data/stop_requested.flag や data/kill.flag の存在を確認してください。不要であれば削除してください。

- Streamlit が DB を開けない（read-only）
  - DB ファイルのパスを正しく指定しているか、ファイルが存在するかを確認してください。MonitoringEngine によって DB が初期化されます。

---

## ディレクトリ構成（主要ファイル・モジュール）

src/kabusys/
- __init__.py
- config.py                         — 環境変数 / .env 読み込みと Settings
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト

パッケージ別フォルダ:
- ai/
  - news_nlp.py                      — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py               — レジーム判定（MA200 + マクロセンチメント）

- monitoring/
  - monitoring_db.py                 — SQLite による監視 DB 層
  - system_monitor.py                — システム・データ鮮度監視
  - trade_monitor.py                 — 注文滞留・約定異常監視
  - risk_monitor.py                  — ドローダウン・ポジション上限監視
  - kill_switch.py                   — kill.flag 書き込みユーティリティ
  - alert_manager.py                 — LINE Push 通知
  - monitoring_engine.py             — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py           — Streamlit での監視 UI

- execution/
  - order_manager.py                 — OrderManager
  - reconciler.py                    — 起動時リコンシリエーション
  - （その他 Execution 用モジュール: broker_factory, execution_engine, order_repository など）

- portfolio/
  - portfolio_builder.py             — 候補選定・重み計算
  - position_sizing.py               — 株数決定・制約処理
  - risk_adjustment.py               — セクターキャップ・レジーム乗数

- research/
  - factor_research.py               — ファクター算出（momentum / value / volatility）
  - feature_exploration.py           — 将来リターン・IC・統計サマリ

- tools/
  - paper_verification_report.py     — Paper Trading の評価レポート生成
  - __init__.py

- utils/
  - process_priority.py              — プロセス優先度 / CPU affinity ユーティリティ

その他:
- data/                              — 実行時に作成される DB / フラグファイル 等（data/*.db, data/execution.pid, data/kill.flag 等）

---

## 開発者向けメモ

- 設計では「ルックアヘッドバイアス防止」のため date.today() 等を直接参照しない設計方針が多くのモジュールで採られています（テスト容易性・再現性の向上）。
- AI 呼び出し部分はリトライ・バックオフやレスポンス検証を明示的に実装しており、部分失敗時も他データを保護するよう DB 操作を工夫しています。
- monitoring_db.init_monitoring_db は冪等で追加カラムのマイグレーション処理も含みます。
- process_priority.set_process_priority はプラットフォーム差を吸収しますが、権限不足等で失敗する可能性がありログに警告が出ます。

---

この README はコードベースの主要点をまとめたものです。実行時の詳細な挙動や追加のユーティリティは各モジュールの docstring / ソースコメントを参照してください。必要であれば、README にサンプル .env.example（必須キーの一覧）やセットアップ用スクリプトの追記も可能です。どの情報を優先して追記したいか指示してください。