# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。ポートフォリオ構築、ポジション算出、リスク調整、リサーチ（ファクター計算）、AI ベースのニュースセンチメント評価、監視・アラート、発注エンジン周りの実装を含みます。

## 概要

KabuSys は以下のような関数/コンポーネントを提供します。

- DuckDB をデータソースとして用いたファクタ / リサーチ機能（prices_daily / raw_financials 等を参照）
- ポートフォリオ候補選定・重み計算・株数決定ロジック（等金額／スコア重み／リスクベース）
- セクター集中制限や市場レジームに基づく資金乗数
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄毎の ai_score 計算）
- マクロニュース + ETF（1321）MA乖離 を用いた市場レジーム判定
- 発注マネージャ / エンジン（OrderManager / ExecutionEngine）およびブローカー API 抽象（Protocol）
- 再起動時のリコンシリエーション（Reconciler）
- 監視（Monitoring）コンポーネント：システム監視、注文監視、リスク監視、アラート（LINE Push）と Streamlit ダッシュボード
- 環境変数・設定管理（自動で .env / .env.local をプロジェクトルートから読み込み）

設計方針として、DB（DuckDB/SQLite）を境界としてビジネスロジックと永続化/外部 API 呼び出しの分離を強く意識しています。多くのユーティリティは「純粋関数」的（副作用なし）に実装されています。

---

## 主な機能一覧

- ポートフォリオ
  - 候補選定: スコア/ランクに基づく選択（select_candidates）
  - 重み計算: 等金額（calc_equal_weights）、スコア加重（calc_score_weights）
  - 位置サイズ計算: risk_based / equal / score による発注株数計算（calc_position_sizes）
  - セクター上限除外（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）

- リサーチ
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算（calc_forward_returns）
  - IC（Information Coefficient）計算・統計サマリ（calc_ic, factor_summary, rank）
  - z-score 正規化ユーティリティ（kabusys.data.stats から提供）

- AI（OpenAI）
  - ニュースを集約して LLM に送り銘柄別センチメントを算出し ai_scores に保存（score_news）
  - マクロニュース + ETF ma200 を組み合わせて市場レジーム判定（score_regime）

- 発注 / 実行
  - Broker API 抽象（Protocol）とデータモデル（OrderRequest / OrderStatus / Position）
  - OrderManager（作成・送信・同期・キャンセル）および ExecutionEngine（シグナルループ・WebSocket プッシュ処理）
  - Reconciler による起動時再同期

- 監視 / アラート
  - MonitoringDB（SQLite） : system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE）
  - MonitoringEngine（ポーリング）および Streamlit ダッシュボード

- 設定管理
  - settings オブジェクト経由で環境変数を型安全に取得
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 必要な環境変数（主要なもの）

※ .env.example を参考に .env を作成してください（プロジェクトは .env 自動読み込みに対応）。

主なキー（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants 用（必須: settings.jquants_refresh_token を参照）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（AlertManager）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH — Paper Trading 関連設定
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行制御 / kill flag

settings モジュール（kabusys.config）で上記の多くにデフォルトやバリデーションが設定されています。

.env 読み込みの挙動:
- 自動読み込み順: OS 環境変数 > .env.local > .env
- .env.local は .env を上書き（override=True）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑制

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作る（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限（本リポジトリで参照されている主な外部ライブラリ）:
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     - pip install duckdb openai requests psutil streamlit

   ※ 実際のプロジェクトでは requirements.txt / poetry 等で管理してください。

4. 環境変数の準備
   - プロジェクトルートに .env（および必要なら .env.local）を配置
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

5. 監視 DB の初期化（SQLite）
   - Python REPL やスクリプトで:
     from sqlite3 import connect
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = connect("data/monitoring.db")
     init_monitoring_db(conn)
   - これで monitoring DB のテーブルが作成されます。

6. DuckDB（data/kabusys.duckdb）について
   - リサーチ機能は prices_daily / raw_financials / raw_news / news_symbols / signals / portfolio_targets / ai_scores / market_regime 等のテーブルを参照します。実行前に必要なスキーマ・データを準備してください（ETL パイプライン等で投入）。

---

## 使い方（代表的な例）

- OpenAI を用いたニューススコアリング（ai/news_nlp.py）
  - 例（Python）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
    print(f"written scores: {written}")

- 市場レジーム判定（ai/regime_detector.py）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- Streamlit ダッシュボード（監視）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 監視エンジン（単発実行）
  - MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor / AlertManager / KillSwitch を組み合わせて使用します。テスト目的で各 monitor の check_once() を直接呼んで結果を得ることも可能です。

- ポートフォリオロジック（純粋関数）
  - 候補選定:
    from kabusys.portfolio import select_candidates, calc_equal_weights
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_equal_weights(candidates)

- ExecutionEngine / OrderManager
  - 実運用では BrokerAPI の実装（kabu station クライアント等）、OrderRepository（SQLite）等を渡して ExecutionEngine.run_session() を呼びます。テストではモックのブローカー/リポジトリを渡して _process_signals / _drain_push_queue を個別に検証できます。

---

## 設定（settings）についての注意点

- settings オブジェクト（kabusys.config.settings）を import して利用します。プロパティで必要な env 値の取得やバリデーションが行われます（例: paper_fill_mode の検証、KABUSYS_ENV の有効値チェックなど）。
- 自動 .env 読み込みはプロジェクトのルート判定に __file__ 起点の親ディレクトリを使用しており、.git または pyproject.toml を検知してルートを決定します。配布後でも CWD に依存せず動作するよう設計されています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env 自動読み込み）
  - portfolio/
    - __init__.py
    - portfolio_builder.py — select_candidates, calc_equal_weights, calc_score_weights
    - risk_adjustment.py — apply_sector_cap, calc_regime_multiplier
    - position_sizing.py — calc_position_sizes
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - ai/
    - __init__.py
    - news_nlp.py — score_news（OpenAI を用いた銘柄別ニュース評価）
    - regime_detector.py — score_regime（ETF とマクロニュースの組合せ）
  - monitoring/
    - __init__.py
    - monitoring_db.py — MonitoringDB, init_monitoring_db
    - system_monitor.py — SystemMonitor
    - trade_monitor.py — TradeMonitor
    - risk_monitor.py — RiskMonitor
    - kill_switch.py — KillSwitch（flag file ベース）
    - alert_manager.py — AlertManager（LINE Push）
    - monitoring_engine.py — MonitoringEngine（ポーリング）
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - broker_api.py — Broker API 抽象、データモデル、例外
    - order_manager.py — OrderManager（作成・送信・同期・キャンセル）
    - execution_engine.py — ExecutionEngine（シグナル処理／WebSocket ドレイン）
    - reconciler.py — 再起動時リコンシリエーション
    - （その他 order_repository / order_record 等はこのコードベースで参照される想定）
  - monitoring/、ai/、portfolio/、research/ に分割して責務を分離

---

## 運用上の注意

- AI（OpenAI）呼び出しは外部 API に依存します。API エラーはリトライ戦略やフォールバック（0.0）でフェイルセーフに扱う実装になっていますが、API キーの管理やレート制限に注意してください。
- ExecutionEngine は kill.flag（ファイル）による外部停止シグナルと PID ファイルでの単一実行管理を行います。運用時は PID / flag の取り扱いに注意してください。
- DuckDB・SQLite のスキーマ整合性は重要です。リサーチ / AI / Execution が期待するテーブルとカラムが存在することを事前に確認してください。
- テスト時は環境変数自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制できます。また OpenAI 呼び出し部分は関数差し替え（mock）で容易にテスト可能です（コード内に注釈あり）。

---

## 参考（よく使う API）

- kabusys.config.settings — 設定値取得（例: settings.duckdb_path, settings.kill_flag_path）
- kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns
- kabusys.ai.score_news（ニュースセンチメント） / kabusys.ai.regime_detector.score_regime
- kabusys.monitoring.init_monitoring_db / MonitoringDB / MonitoringEngine / Streamlit ダッシュボード
- kabusys.execution.OrderManager / ExecutionEngine / Reconciler

---

必要であれば、README に含めるコマンド例、各テーブルの詳細スキーマ（DuckDB 用）、または ExecutionEngine の接続例（モック込みサンプル）を追加で作成できます。どの情報を追加したいか教えてください。