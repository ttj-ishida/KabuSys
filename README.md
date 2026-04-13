# KabuSys

KabuSys は日本株の自動売買・解析・監視を目的とした Python ベースのプロジェクトです。本リポジトリには、発注実行エンジン、監視（Monitoring）機能、ポートフォリオ構築ロジック、研究用ファクター計算、AI を使ったニュースセンチメント評価、ツール類（検証レポート生成や Streamlit ダッシュボード）などが含まれます。

---

## プロジェクト概要

主なコンポーネント:

- ExecutionEngine: ブローカークライアントと連携して注文を作成・送信・管理する実行エンジン。再起動時のリコンシリエーション機能あり。
- Monitoring: システム状態・注文状態・リスク（ドローダウン・ポジション上限）を定期的にチェックしてログ保存・アラート送信・Kill Switch を実行可能。
- Portfolio Construction: シグナルから候補銘柄選定、重み付け、ポジションサイジング（単元株丸め、リスク制限）を実行する純粋関数群。
- Research: DuckDB 上の時系列データを用いたファクター計算（モメンタム・バリュー・ボラティリティ）や特徴量解析ユーティリティ。
- AI モジュール: OpenAI を用いてニュースのセンチメントを銘柄ごとに算出する news_nlp と、市場レジーム判定を行う regime_detector。
- Tools: Paper Trading 検証レポート生成や Streamlit ダッシュボードなど運用補助ツール。
- Utils: プロセス優先度設定やその他ユーティリティ。

設計のポイント:
- DuckDB + SQLite をデータ基盤に採用（研究用・監視用で分離）。
- 本番/ペーパー取引環境の明確な切り分け（KABUSYS_ENV）。
- 外部 API（OpenAI 等）呼び出しはフェイルセーフ（失敗時はフォールバック）で設計。
- 主要ロジックは副作用の少ない純粋関数で実装（テストしやすい）。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じてペーパー取引/本番を切替え）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス生存、データ鮮度の監視
  - TradeMonitor: 注文滞留（stale orders）や約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ化
  - KillSwitch: 条件に応じて kill.flag 書き込みで ExecutionEngine 停止要求を発行
  - AlertManager: LINE Messaging API を使った通知（クールダウン管理）
  - Streamlit ダッシュボード: 監視データの可視化
- Execution / 注文管理
  - OrderManager / OrderRepository / Reconciler: 注文状態遷移、ブローカー同期、自動リコンシリエーション
- ポートフォリオ構築
  - 候補選定、等配分 / スコア配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出（単元丸め・aggregate cap）
- Research
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュースセンチメント集約・スコアリング（バッチ処理・JSON 検証・リトライ）
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）
- ツール
  - paper_verification_report: ペーパー取引 DB から検証レポートを生成

---

## セットアップ手順

前提
- Python 3.9+（推奨）
- git

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 依存パッケージをインストール
   必要な主要パッケージ（抜粋）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - (その他：テストや環境により必要なパッケージがある場合があります)
   
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   プロジェクトに requirements.txt があればそちらを使用してください:
   ```
   pip install -r requirements.txt
   ```

4. 環境変数（.env）を用意
   プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`で無効化可）。

   最低限設定すべき主なキー（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...         # AI モジュールを使う場合
   - KABUSYS_ENV=development|paper_trading|live
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  # paper_trading 用
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE=instant|partial|never|reject

   注意: 本番運用時は機密情報（API トークン等）を適切に管理してください。

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

6. データベース初期化
   監視用 DB（SQLite）は run_execution / run_monitoring が起動時に `init_monitoring_db` を呼んで冪等的に初期化します。DuckDB は研究データを用意してください。

---

## 使い方

起動時の基本コマンド例を示します。

- ExecutionEngine を起動
  - デフォルト（development / live の切替は KABUSYS_ENV で）
  ```
  python -m kabusys.run_execution
  ```
  - Paper Trading（モックブローカーを使い、data/paper_trading.db に記録）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  設定: paper_trading 時は `PAPER_TRADING_SQLITE_PATH` で SQLite パスを指定できます。

- Monitoring（SystemMonitor の単体ポーリング）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔変更:
  ```
  export MONITOR_POLL_INTERVAL=30   # 秒
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（ニューススコアリング / レジーム判定）
  これらはプログラムから関数を呼び出します。環境変数 `OPENAI_API_KEY` を必ず設定してください。
  例（Python REPL で）:
  ```py
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,10), api_key=None)  # api_key None は OPENAI_API_KEY を参照
  ```

- その他
  - 設定の切り替えは `KABUSYS_ENV`（development / paper_trading / live）で行います。
  - `PAPER_FILL_MODE` によりペーパー取引の約定振る舞いを指定できます（instant / partial / never / reject）。

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API パスワード（実運用時）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール）
- SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒。デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行制御用ファイルパス

---

## ディレクトリ構成（主要ファイル）

```
src/
  kabusys/
    __init__.py                 # パッケージ定義・バージョン
    config.py                   # 環境変数 / 設定管理（.env 自動ロード等）
    run_execution.py            # ExecutionEngine 起動スクリプト
    run_monitoring.py           # SystemMonitor ポーリング起動スクリプト

    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      execution_engine.py
      broker_factory.py
      broker_api.py
      order_record.py
      ...                      # 発注・状態管理関連

    monitoring/
      monitoring_db.py          # SQLite スキーマ定義 + CRUD
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
      __init__.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py
      regime_detector.py
      __init__.py

    tools/
      paper_verification_report.py
      __init__.py

    data/
      pipeline.py                # DuckDB データアクセス（get_last_price_date 等）

    utils/
      process_priority.py        # プロセス優先度・CPU affinity 設定ユーティリティ
```

各モジュールは README 内の機能一覧で簡単に説明した通りの役割を持ち、監視データは SQLite（monitoring.db）へ永続化されます。研究用データ・時系列は DuckDB（kabusys.duckdb）で管理します。

---

## 運用上の注意事項

- 本番環境ではシークレット（API キー等）を安全に管理してください（.env を踏み台にしない、CI/Secrets 管理を利用する等）。
- run_execution は ExecutionEngine 起動時に PID ファイルを書きます。monitoring は PID ファイルの存在・稼働をチェックします。
- AI モジュールは API 呼び出しでコストが発生します。バッチサイズ・リトライ設定は定数で制御されています。
- DuckDB / SQLite のファイルパスや読み書き権限に注意してください。Streamlit は DB を読み取り専用で開くことを推奨しています。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば .env 自動読み込みを抑止できます（テスト等で便利）。

---

## 開発・貢献

- コードはモジュール毎にテスト可能な純粋関数・クラス設計を意識しています。ユニットテスト・モックを用いたテストを推奨します（外部 API 呼び出しは差し替え可能な設計）。
- PR や Issue は歓迎します。機能追加や改良の提案をしてください。

---

README に記載のある起動方法・環境変数・ファイルパスなどはコードベース（特に `kabusys/config.py`, `run_execution.py`, `run_monitoring.py`, `monitoring/*`）を参照して詳細を確認してください。必要であれば .env.example のサンプル作成や、requirements.txt の整備、運用手順書（Runbook）の作成も支援できます。