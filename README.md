# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ、ポートフォリオ構築、実行・監視、AI 補助など）。このリポジトリはモジュール単位で構成されており、単体実行できる起動スクリプトや運用用ツール類を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python ベースの自動売買基盤です。

- DuckDB / SQLite を用いた時系列データ解析と永続化
- ファクター計算、リサーチ用ユーティリティ（momentum / volatility / value など）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine / OrderManager / Reconciler による発注実行と起動時リコンシリエーション
- 監視（System / Trade / Risk）とアラート送信（LINE push）
- AI 補助モジュール（ニュースのセンチメント集約、レジーム判定） — OpenAI API を利用
- 運用ツール（Paper Trading レポート生成、Streamlit ダッシュボード等）

設計方針の一部：
- ルックアヘッドバイアス排除（target_date 等を外部から渡す）
- 本番 DB と Paper Trading の分離（環境により別 SQLite を使用）
- フェイルセーフ（API失敗時のフォールバックや例外を吸収する設計）

---

## 主な機能一覧

- リサーチ
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials を使ったファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析・IC 計算・統計サマリ

- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier（セクター集中やレジーム考慮）

- 実行（Execution）
  - OrderManager / OrderRepository / Reconciler：注文ライフサイクル管理・再同期
  - ExecutionEngine 起動スクリプト（run_execution.py）

- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor：定期チェックと SQLite へのログ記録
  - MonitoringEngine：複数モニタの統合ポーリングループ
  - AlertManager：LINE による通知（クールダウン制御付き）
  - kill_switch：条件で ExecutionEngine 停止フラグを書き込み
  - streamlit_dashboard：監視ダッシュボード起動用

- AI（OpenAI）
  - news_nlp.score_news：ニュース記事をまとめて LLM で銘柄別センチメント算出・DB 書込み
  - regime_detector.score_regime：ETF MA とマクロニュースの LLM 評価を合成して日次レジーム判定

- ツール
  - tools.paper_verification_report：Paper Trading DB から検証レポートを生成

---

## セットアップ手順

前提：
- Python 3.9+ 推奨（コードは型アノテーション等を使用）
- SQLite（組み込み）、DuckDB が必要
- ネットワークアクセスが必要な機能（LINE API / OpenAI）は対応トークンが必要

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的にロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須、または利用可能な主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必要に応じて）
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
     - KABUSYS_ENV — environment: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定モード: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他しきい値系（LOG_LEVEL, CPU_THRESHOLD_PCT 等）
   - MONITOR_POLL_INTERVAL 環境変数で監視ループのポーリング間隔を秒単位で上書き可能（デフォルト 60）。

4. データディレクトリ
   - デフォルトで data/ 以下に DB 等を置く設計になっています。必要に応じてディレクトリを作成してください。
     - mkdir -p data

5. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に監視テーブルの初期化（init_monitoring_db）を行います。手動で初期化したい場合は小スクリプトを呼ぶか、これらを1回起動してください。

---

## 使い方（起動・ツール）

以下は代表的な起動方法です。環境変数は起動前に export / set してください。

- 監視ループを起動（監視DBは settings.sqlite_path を参照）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # ポーリング間隔 30 秒

- 実行エンジン（ExecutionEngine）を起動
  - 本番環境:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（MockBroker を使い、data/paper_trading.db を使用）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - 日付指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI センチメント / レジーム判定（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)  # api_key None の場合は OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、結果を DB に書き込みます。OPENAI_API_KEY が必須（未設定時は ValueError）。

- 開発時の注意
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト等で便利）。
  - Paper Trading と本番 DB は分離されています（Settings.is_paper に依存）。

---

## 運用上のポイント / 実装上の注意

- プロセス優先度:
  - run_monitoring/run_execution は起動直後に set_process_priority("high") を呼びます。プラットフォームや権限によって設定に失敗する場合はログに警告が出ます。

- kill.flag:
  - KillSwitch は data/kill.flag（デフォルト）を作成すると ExecutionEngine に停止シグナルを送る設計です。kill.flag のパスは Settings.kill_flag_path で指定します。

- DB マイグレーション:
  - init_monitoring_db は既存 DB に対して冪等にテーブル作成を行い、足りないカラム（例: latency_ms, peak_value）があれば追加します。

- フェイルセーフ:
  - OpenAI API 呼び出し等は 429 / タイムアウト / 5xx をリトライする実装になっており、最終的に失敗しても致命的に止めずフォールバック（例: スコア 0）します。

- Paper Trading:
  - KABUSYS_ENV=paper_trading を指定すると MockBroker を使用し、実発注は行いません。DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離されます。

---

## ディレクトリ構成

（主要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（Settings）
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (想定)
    - pipeline.py (参照されるモジュール) — データ取得 / get_last_price_date 等
    - stats.py                         — zscore_normalize 等
  - research/
    - factor_research.py              — momentum/volatility/value の計算
    - feature_exploration.py          — forward returns / IC / summary
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (Engine 本体; 起動スクリプトから利用)
    - broker_factory.py               — Broker クライアント生成（mock/prod 切替）
    - broker_api.py                   — Broker API 抽象
    - order_record.py                 — OrderRecord / OrderState
    - order_record 等
  - monitoring/
    - monitoring_db.py                — SQLite 永続化層（system_status / trade_logs / risk_logs / dashboard / positions）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - ai/
    - news_nlp.py                      — ニュース集約 + OpenAI でのセンチメント算出
    - regime_detector.py               — ma200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py     — Paper Trading 検証レポート
    - __init__.py

---

## 追加情報 / FAQ

- Q: .env の読み込み順は？
  - A: OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされません）。プロジェクトルートは .git または pyproject.toml を基準に自動検出します。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: MONITOR_POLL_INTERVAL の値が不正だとどうなる？
  - A: run_monitoring は環境変数 MONITOR_POLL_INTERVAL を読み取り整数に変換します。不正値や 0 以下はデフォルト 60 秒にフォールバックし、警告ログが出ます。

- Q: OpenAI の呼び出しで失敗した場合は？
  - A: news_nlp/regime_detector はリトライやフォールバック（macro_sentiment=0.0 等）を行い、致命的に停止しない設計です。ただし API キーが未設定の場合は ValueError を投げます。

---

この README はコードベースの主要機能と運用手順の概要をまとめたものです。詳細な実装・パラメータ調整や追加の運用手順は各モジュール内の docstring を参照してください。必要であれば README の追記（デプロイ手順、systemd ユニット例、監視運用フロー）も作成します。