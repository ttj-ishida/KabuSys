# KabuSys

日本株自動売買システム（プロトタイプ）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は戦略（シグナル）→ ポートフォリオ構築 → 注文管理 → 実行 → 監視／アラートまでの一連のワークフローを提供することです。  
本コードベースは以下の主要コンポーネントを含みます。

- Execution: 注文の生成・送信・リコンシリエーション（実ブローカー／モック両対応）
- Monitoring: システム稼働・注文滞留・リスク監視、LINEによる通知、Streamlit ダッシュボード
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限・レジーム係数
- Research: ファクター（Momentum/Value/Volatility）計算、特徴量探索（IC 等）
- AI: ニュースを LLM（OpenAI）でスコアリング、マクロセンチメントと ma200 によるレジーム判定
- Tools: Paper Trading の検証レポート生成スクリプトなど

設計上の特徴:
- DuckDB / SQLite をデータ層に使用（DuckDB: 時系列/ファクター集計、SQLite: 監視ログ／注文ログ）
- 環境分離: `KABUSYS_ENV=paper_trading` で paper trading 用 DB を使用（本番 DB と分離）
- フェイルセーフ/冪等性に配慮した実装（DB マイグレーション、部分失敗時のデータ保護など）

---

## 機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパートレードの切替
  - Broker クライアントの抽象化（実ブローカー or Mock）
  - リスク管理・オーダーマネージャ・リコンシリエーション
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システムメトリクス（CPU/MEM/DISK）、プロセス生存チェック、データ鮮度監視
  - 注文滞留・約定異常の検出
  - ドローダウン／ポジション上限の検出と kill.flag による停止シグナル
  - LINE 通知（AlertManager）、Streamlit ダッシュボード
- Portfolio モジュール
  - 候補選定（スコア順）、等重・スコア加重、リスクベースの株数算出
  - セクターキャップ、レジーム乗数
- Research モジュール
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB 上で完結）
  - 将来リターン、IC、統計サマリ
- AI モジュール
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価 → ai_scores に保存
  - マクロニュース + ETF ma200 乖離から market_regime を算出して永続化
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report.py）
  - Streamlit ベースの監視ダッシュボード

---

## 動作環境 / 依存

- Python 3.9+（型アノテーションの一部で 3.10 以降を想定している箇所があります。実行環境に合わせて適宜調整してください）
- 必要なパッケージ（主要なもの）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI モジュール利用時)
  - sqlite3（標準ライブラリ）
- 環境変数や .env を利用して設定を読み込む仕組みを備えています（自動ロード: project root の .env / .env.local）。

推奨: 仮想環境（venv / conda）を利用してください。

---

## セットアップ手順（素早く始める）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （requirements.txt がなければ下記を個別にインストール）
   ```
   pip install duckdb psutil requests streamlit openai
   ```

4. データディレクトリの作成
   ```
   mkdir -p data
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 主要な環境変数（例）:
     ```
     KABUSYS_ENV=development            # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant
     ```
   - 自動ロードは Settings モジュールでプロジェクトルートの .env / .env.local から行います（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

6. DB の初期化
   - 監視用 SQLite（monitoring.db）は起動スクリプトが必要テーブルを自動で作成します。手動で作る必要はありません。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番 or paper）
  ```
  # デフォルト: KABUSYS_ENV=development
  python -m kabusys.run_execution

  # Paper Trading
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  備考:
  - paper_trading 時は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録します（本番 DB と分離）。
  - 起動時にプロセス優先度を High に設定します（権限がない場合は警告）。

- Monitoring（ポーリング）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視は .sqlite monitoring DB に状態を記録します（Monitoring は環境にかかわらず production sqlite_path を使用します）。

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db PATH` で DB パスを明示可能（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）。

- AI モジュール（プログラム内から利用）
  - ニューススコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
    print("written:", written)
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
    ```

---

## 主要設定（環境変数）

Settings クラスで扱う主な環境変数（抜粋）:

- 一般
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- API / 認証
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY

- データベース
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (monitoring, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper trading, default: data/paper_trading.db)
  - PAPER_FILL_MODE: instant | partial | never | reject

- 監視 / 実行制御
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1 で実行時に kill.flag をクリア)
  - MONITOR_POLL_INTERVAL (run_monitoring 用、秒、default 60)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

必要な必須キー（起動時に未設定だと例外となるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
（用途によっては OPENAI_API_KEY や LINE トークンも必須となる処理が存在します）

---

## 注意事項 / 実装上のポイント

- Paper Trading と本番は DB を分離しているため、誤って本番データを書き換えるリスクを低減しています。
- Monitoring の初期化関数 `init_monitoring_db` は冪等で、既存 DB に対するマイグレーション（カラム追加）も行います。
- LLM（OpenAI）を利用する処理は外部 API に依存するため、API キーの管理やリトライ制御が実装されていますが、API 利用料やレート制限に注意してください。
- run_execution/run_monitoring 起動時に可能な限りプロセス優先度を高めます（プラットフォーム依存、権限がない場合は警告）。
- kill.flag による停止は冪等で、既にファイルが存在する場合は再書き込みしません。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - ... (注文・ブローカ関連)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/ (想定データ格納先)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

（実際のファイル一覧はリポジトリの内容を参照してください）

---

## 開発・デバッグに関するヒント

- Settings はプロジェクトルートの `.env` / `.env.local` を自動読み込みします。テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB のクエリは大量データで高速なので、ファクター計算やリサーチ処理は DuckDB 上で行います。ローカルでデータを準備して検証してください。
- Streamlit ダッシュボードは監視 DB を read-only で開くため、運用環境の DB を壊す心配なく閲覧できます。

---

これで基本的な README になります。リポジトリに合わせて README に追加したい項目（例: ライセンス、contributing、より詳細な設定例やスクリーンショット等）があれば教えてください。必要に応じて .env.example のテンプレートや簡易起動スクリプトも作成できます。