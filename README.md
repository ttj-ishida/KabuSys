# KabuSys

日本株の自動売買・リサーチ基盤ライブラリ（プロトタイプ）

このリポジトリは、機械的に銘柄選定 → 発注 → 監視 を行うための内部ライブラリ群を提供します。  
主要な機能はポートフォリオ構築、ポジションサイズ計算、ファクター/特徴量計算、ニュースのLLMベースセンチメント評価、マーケットレジーム判定、発注エンジン（ExecutionEngine）、監視（MonitoringEngine / Streamlit ダッシュボード）などです。

注意: 本 README はコードベース（src/kabusys/*）に基づく説明です。実運用には各種設定・バックテスト・十分な検証が必須です。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートは .git / pyproject.toml を基準）
  - 必須/任意の環境変数を Settings API 経由で取得

- ポートフォリオ構築
  - 候補選定（スコア降順の上位 N 抽出）
  - 等配分・スコア加重配分
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（市況に応じた投下資金倍率）

- ポジションサイジング
  - リスクベース / 重みベース（等・スコア）で発注株数を計算
  - 単元株（lot）丸め、1銘柄上限・全体利用上限・手数料バッファ考慮、スケールダウン処理

- リサーチ（ファクター）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials テーブル参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（LLM）連携
  - ニュースを集約して OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出し ai_scores に書き込み
  - マクロニュース＋ETF（1321）MA200 乖離で市場レジーム（bull/neutral/bear）を判定・記録
  - API 呼び出しはリトライ、失敗フォールバック（フェイルセーフ）設計

- 発注・実行
  - Broker API の Protocol 定義（データモデル・例外）
  - OrderManager（状態遷移・永続化戦略）、Reconciler（再起動時の同期）、ExecutionEngine（シグナルループ + push drain）
  - 発注ガード（Gate1/2/3）や kill.flag による安全停止

- 監視・アラート
  - SQLite ベースの MonitoringDB（system_status / trade_logs / positions / risk_logs / dashboard）
  - System / Trade / Risk 各モニター、AlertManager（LINE push）、KillSwitch
  - Streamlit ダッシュボードで監視情報を可視化

---

## セットアップ手順（ローカル開発向け）

下記は最低限の手順例です。実行環境・Python バージョンはプロジェクト要件に合わせてください（例: Python 3.10+ を想定）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（requirements.txt を用意する想定）
   例:
   ```
   pip install duckdb openai requests psutil streamlit
   ```
   ※ 実際の requirements はプロジェクトに合わせて作成してください。

4. 環境変数の準備
   プロジェクトルートに `.env` を作成すると自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。主な環境変数:

   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能利用時に必須)
   - LINE_CHANNEL_ACCESS_TOKEN (監視アラート用、任意)
   - LINE_USER_ID (監視アラート用、任意)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視DB、デフォルト: data/monitoring.db)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
   - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など（Paper Trading 用）

   サンプル `.env`（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. 監視DB の初期化（SQLite）
   Python スクリプト内で init_monitoring_db を呼ぶか、REPL で:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

6. DuckDB データの準備
   - 各リサーチ関数は DuckDB の特定テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）を前提とします。実データをロードするか、テスト用にダミーデータを用意してください。

---

## 使い方（代表的な例）

- 環境設定の取得（Python）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- ファクター計算（DuckDB 接続が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP によるスコア付け（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026,3,20), api_key="sk-...")
  print("書き込んだ銘柄数:", n_written)
  ```

- レジーム判定（market_regime への書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")
  ```

- Streamlit 監視ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine を使った監視ループ（例）
  ```python
  import sqlite3
  import duckdb
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager, MonitoringDB, init_monitoring_db
  # 接続準備とインスタンス化（省略）
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
  engine.run()  # Ctrl+C で停止
  ```

- ExecutionEngine で発注セッション実行
  ExecutionEngine は BrokerAPI の具体実装（kabu station クライアントなど）、OrderRepository（SQLite 実装）や RiskManager が必要です。テストではモックを渡して _process_signals / _drain_push_queue を直接呼ぶ設計です。

---

## 主要なディレクトリ構成（src/kabusys）

概略（重要なファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数取得・自動 .env 読み込み）
  - portfolio/
    - portfolio_builder.py（候補選定・重み計算）
    - position_sizing.py（株数計算）
    - risk_adjustment.py（セクターキャップ・レジーム乗数）
  - research/
    - factor_research.py（momentum / volatility / value 等）
    - feature_exploration.py（将来リターン・IC・統計）
  - ai/
    - news_nlp.py（ニュースの LLM センチメント → ai_scores）
    - regime_detector.py（マクロ + MA200 で市場レジーム判定）
  - monitoring/
    - monitoring_db.py（SQLite スキーマ + MonitoringDB）
    - system_monitor.py / trade_monitor.py / risk_monitor.py
    - alert_manager.py（LINE push）
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py（データモデル・Protocol・例外）
    - order_manager.py（Order 状態遷移・送信）
    - reconciler.py（起動時リコンシリエーション）
    - execution_engine.py（シグナルループ・push ドレイン）
    - （その他: order_repository, order_record, risk_manager 等が想定される）
  - monitoring, research, portfolio, ai の __init__.py により外部 API を整理してエクスポート

- data/ (想定: データベースファイルや PID / flag を配置)
  - kabusys.duckdb
  - monitoring.db
  - execution.pid
  - kill.flag

---

## 重要な設計上の注意点 / 挙動

- .env 自動読み込み
  - プロジェクトルート（.git / pyproject.toml を探索）を基準に `.env` / `.env.local` を順に読み込みます。
  - 優先順位: OS 環境 > .env.local > .env
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI / 外部API
  - news_nlp, regime_detector は OpenAI API を呼び出します。API キー未設定の場合は例外が上がります（関数毎にチェック）。
  - LLM呼び出しはリトライやパースエラーを考慮したフェイルセーフ実装になっていますが、料金・レート制限・プライバシーには注意してください。

- データの整合性
  - 各リサーチ/AI 関数は DuckDB の特定テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）を想定しています。データスキーマとデータ鮮度を満たすことが前提です。

- 安全停止
  - kill.flag を書くことで ExecutionEngine を停止させられます。KillSwitch が条件判定・書き込みを行います。
  - PID ファイル（デフォルト data/execution.pid）を用いてプロセス健全性を監視します。

---

## 開発・テストに関するヒント

- 各モジュールは純粋関数（副作用を持たない）で実装されている箇所が多く、ユニットテストしやすい設計です。OpenAI 呼び出し箇所は `_call_openai_api` をパッチしてテスト可能です。
- MonitoringDB の init_monitoring_db は冪等で、既存 DB のマイグレーション（列追加）にも対応しています。
- ExecutionEngine / OrderManager はクラッシュ耐性を考慮した2相永続化戦略（OrderSent 永続化 → API 呼び出し → broker_order_id 保存 → OrderAccepted）を採用しています。Reconciler により再起動後の同期を行います。

---

この README はコードベースの主要点をまとめたものです。利用・拡張する際は各モジュールの docstring と実装を参照してください。必要であれば、セットアップ用の requirements.txt、サンプル .env.example、テストデータのダンプスクリプト等を追加することを推奨します。