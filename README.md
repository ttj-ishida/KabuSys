# KabuSys

KabuSys は日本株自動売買のためのライブラリ兼小規模アプリケーション群です。  
主に以下の領域をカバーします。

- 注文実行エンジン（ExecutionEngine）: ブローカーとの発注・状態管理・リコンシリエーション
- 監視（Monitoring）: システム状態・注文・リスクのポーリング監視、LINE 通知、kill フラグ
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター上限等の純粋関数群
- リサーチ: ファクター計算、特徴量探索（IC 等）
- AI ユーティリティ: ニュースの NLP スコアリング、レジーム判定（OpenAI 使用）
- ツール: Paper Trading 検証レポート生成、Streamlit ダッシュボード等

この README はコードベース（src/kabusys 以下）に基づく基本的な説明、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## 主要機能（抜粋）

- Execution
  - ブローカー抽象化（本番/モック切替）
  - OrderManager / OrderRepository による状態管理
  - Reconciler による再起動後の自動同期（OrderSent 照合、ポジション差分検出）
  - RiskManager（設定に基づく発注制限）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留、約定価格の異常検出
  - RiskMonitor: ドローダウン、ポジション数上限監視
  - KillSwitch: 条件に応じてフラグファイルを書き、ExecutionEngine 停止指示
  - AlertManager: LINE Messaging API への一方向プッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視 DB を参照）
- Portfolio
  - 候補選定、等重/スコア重み、リスク・セクター制約、ポジションサイズ計算（lot 単位）
- Research
  - Momentum, Volatility, Value ファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - 将来リターン・IC・ファクター統計
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコア算出、ai_scores 書込
  - regime_detector: ETF MA200 とマクロニュースを合成して市場レジーム判定を作成・保存
- ツール
  - paper_verification_report: Paper Trading DB を解析して運用検証レポートを生成
  - streamlit_dashboard: 監視ダッシュボード

---

## 前提 / 必要環境

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ sqlite3 を使用）
- インターネット接続（OpenAI API を使う場合）

推奨: 仮想環境を作成して依存をインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

（実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を使うのが望ましいです）

---

## 設定（環境変数 / .env）

Settings クラスは .env または環境変数から各種設定を読み込みます。自動ロードの挙動:

- プロジェクトルートは .git または pyproject.toml を基準に探索
- 既存の OS 環境変数 > .env.local（上書き可） > .env（未上書き）
- 自動ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主な環境変数（抜粋）:

- KABUSYS_ENV: 実行環境。allowed: development, paper_trading, live（デフォルト: development）
  - paper_trading のときはモックブローカーを使い、DB を data/paper_trading.db に切り分けます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabu ステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading の SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring のオーバーライド用。デフォルト 60）
- PAPER_FILL_MODE: paper_trading のモック約定挙動（instant|partial|never|reject）

.env のサンプルがある場合は .env.example を参照して作成してください。

---

## セットアップ手順（ローカルで動かす最小手順）

1. リポジトリをクローンし、Python 仮想環境を作成
2. 依存パッケージをインストール（上記参照）
3. data ディレクトリを作成（DB や PID/flag の格納先）
   ```bash
   mkdir -p data
   ```
4. 必要な環境変数を .env に設定（例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```
5. DuckDB / SQLite に必要なスキーマは実行時に自動作成されます（init_monitoring_db は冪等でテーブル／カラム追加を行います）。

注意: package を pip install せずローカル src を使う場合は PYTHONPATH を通すか、プロジェクトルートで次のように実行してください:
```bash
PYTHONPATH=./src python -m kabusys.run_monitoring
```

---

## 使い方（主要コマンド）

基本的に各スクリプトはパッケージモジュールとして実行できます（プロジェクトをパッケージインストールするか PYTHONPATH を設定）。

- 監視ループを起動（SystemMonitor を定期実行）
  ```bash
  # 環境変数でポーリング間隔を上書き可能
  export MONITOR_POLL_INTERVAL=30
  PYTHONPATH=./src python -m kabusys.run_monitoring
  ```

  補足:
  - run_monitoring は Settings にかかわらず本番の sqlite_path を使用して監視 DB を更新します。
  - 起動直後にプロセス優先度を "high" に設定しようとします（psutil による。権限不足時は警告）。

- ExecutionEngine を起動（実際に取引を行うプロセス）
  ```bash
  PYTHONPATH=./src python -m kabusys.run_execution
  ```

  補足:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録されます（本番 DB と分離）。
  - 起動時に Reconciler による同期を行い、Broker とローカル DB の不整合を処理します。
  - ExecutionEngine 起動時に PID ファイルを出力し、KillSwitch は kill.flag の存在で停止を促します。

- Streamlit 監視ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  ダッシュボードは監視 DB を読み取り専用で開き、Positions / Orders / System / Overview を表示します。

- Paper Trading 検証レポート生成ツール
  ```bash
  # デフォルト DB: data/paper_trading.db
  PYTHONPATH=./src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 周り（ニュース NLP / レジーム判定）はライブラリ関数として呼び出します。OpenAI API キーが必要です。
  - ニューススコアリング（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ など）
  - config.py — 環境変数 / Settings 管理。.env 自動ロードロジックを含む。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
- src/kabusys/execution/
  - order_manager.py — 発注・状態遷移の上位 API
  - reconciler.py — 再起動時のリコンシリエーション
  - （その他 Broker 関連、order_repository 等が想定される）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite による監視用永続化層（テーブル作成・CRUD）
  - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限判定
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・aggregate cap 処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計
- src/kabusys/ai/
  - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書込
  - regime_detector.py — MA200 + マクロニュースで市場レジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

コードベースは「ロジックを分離した純粋関数」「DB アクセスを抽象化した層」「モジュール単位での責務分離」に配慮して設計されています。多くのモジュールは DuckDB / SQLite を前提に SQL と Python を組み合わせており、AI 呼び出し（OpenAI）は専用関数でラップしているためテストの差し替えが容易です。

---

## 運用上の注意・設計上のポイント

- run_monitoring/run_execution 起動時にプロセス優先度を "high" に設定しようとします。権限がない環境では警告が出ますが動作は継続します。
- 監視機能は SQLite（monitoring.db）に永続化します。init_monitoring_db はテーブルと簡単なマイグレーション（カラム追加）を行います。
- Paper Trading は本番 DB と完全分離されるよう意図されています（PAPER_TRADING_SQLITE_PATH）。
- AI 呼び出し周りはネットワーク障害・429・5xx 等に対して指数バックオフでのリトライを行い、失敗時はフォールバック（スコア 0.0 等）してシステム全体の可用性を優先します。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。

---

## 例: よくある起動フロー（ローカルデバッグ）

1. 仮想環境を作る、依存を入れる
2. .env を作る（上記の必須項目をセット）
3. 監視を起動（別ターミナル）
   ```bash
   PYTHONPATH=./src python -m kabusys.run_monitoring
   ```
4. 実行エンジンを起動（別ターミナル）
   ```bash
   PYTHONPATH=./src KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
5. 必要に応じて streamlit ダッシュボードを立ち上げる

---

必要に応じて README を拡張して以下を追加すると良いです：

- requirements.txt / poetry/pyproject.toml に依存情報を明記
- .env.example をプロジェクトルートに置く（必須環境変数の説明）
- 起動時の systemd / supervisor 用の unit サンプル
- テスト手順と CI 設定

ご希望があれば、README を .env.example のテンプレートや systemd ユニット例、より詳細なコマンド集に拡張します。どの項目を優先して追記しますか？