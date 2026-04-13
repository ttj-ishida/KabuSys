# KabuSys

日本株自動売買システムの一部コンポーネント群。  
このリポジトリには、戦略／ポートフォリオ構築、実行エンジン起動スクリプト、監視・アラート、研究用ユーティリティ、そして AI（ニュース NLP / レジーム判定）連携モジュールが含まれます。

以下はコードベースの主要ドキュメント（README.md）です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（実行方法）
- 環境変数（主なもの）
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買アプリケーションのモジュール群です。  
主に以下の役割を持つコンポーネントを含みます。

- 注文実行エンジン（ExecutionEngine）の起動・運用支援
- 監視（System / Trade / Risk）とアラート（LINE 連携）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算、リスク調整）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP を用いた銘柄センチメント scoring（OpenAI）
- Paper Trading（検証用 DB による実行分離）と検証レポート生成

設計上の方針の一例：
- データベースに SQLite（監視等）および DuckDB（時系列/研究データ）を採用
- Paper Trading は本番 DB と完全分離（別 SQLite ファイル）
- OpenAI 等外部 API 呼び出し時はリトライ・フォールバックを実装してフェイルセーフを考慮

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper DB に記録）
  - プロセス優先度設定、DB 初期化、リコンシリエーション、リスク管理等を組み合わせてセッションを実行

- run_monitoring.py
  - SystemMonitor のポーリングループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは monitoring DB（デフォルト: data/monitoring.db）へ永続化

- monitoring package
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine
  - SQLite を用いた監視ログの永続化（init_monitoring_db によりテーブル作成）
  - Streamlit ダッシュボード（監視データの閲覧）

- portfolio package
  - 候補選定、等金額 or スコア加重、リスク調整（セクター上限・レジーム乗数）、発注株数計算（単元丸め・aggregate cap）

- research package
  - ファクター計算（momentum, volatility, value）および特徴量探索（forward returns, IC 等）
  - DuckDB 接続を受け取り SQL + Python で計算

- ai package
  - news_nlp: raw_news を OpenAI に送って銘柄ごとの sentiment / ai_score を作成・保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 評価を組み合わせて市場レジームを判定

- tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを標準出力に出す

---

## セットアップ手順

前提：Python 3.10+ を想定（typing の一部表記など）。環境に合わせて調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（requirements.txt があればそれを使用してください）。
   代表的な依存：
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. データディレクトリ作成（デフォルト）
   ```
   mkdir -p data
   ```
   スクリプト実行時に必要ファイル（PID ファイルや kill.flag）のディレクトリも自動作成されますが、事前に作っておくと権限エラーを防げます。

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただし OS 環境変数が優先、.env.local は .env を上書き）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方

以下は代表的な実行方法とオプションの例です。

### 実行エンジンを起動（本番 / paper_trading）

- 通常（環境変数で設定された環境に従う）
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading（KABUSYS_ENV=paper_trading）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - paper_trading の場合、settings.paper_sqlite_path（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離して実行されます。
  - PAPER_FILL_MODE（instant|partial|never|reject）で MockBroker の約定挙動を変更できます。

### 監視ループを起動

- デフォルトポーリング（60 秒）
  ```
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔を変更（環境変数）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

注意: Monitoring はコード内の仕様により「KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します（監視は本番 DB を参照する想定）。

### Streamlit ダッシュボード

- モニタリング DB の状態をブラウザで確認
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  DB が読み取り専用で開かれます（存在しない場合はエラー表示）。

### Paper Trading 検証レポート

- デフォルト DB（data/paper_trading.db）からレポートを生成
  ```
  python -m kabusys.tools.paper_verification_report
  ```

- 期間指定・DB 指定
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

### AI モジュール（ニューススコア・レジーム判定）

- OpenAI API を使う機能は環境変数 `OPENAI_API_KEY`（または関数引数）を参照します。未設定時は該当処理が例外になるので注意してください。
- ニュース NLP（ai.score_news）は DuckDB 接続を受け取り、指定日でスコアを生成して ai_scores に書き込みます（実行方法はユーティリティやバッチ処理から呼び出す想定）。

---

## 主な環境変数

- KABUSYS_ENV
  - 有効値: `development`, `paper_trading`, `live`
  - デフォルト: `development`
  - `paper_trading` の場合は注文実行がモック＆DB 分離されます

- MONITOR_POLL_INTERVAL
  - 監視ポーリング間隔（秒）
  - デフォルト: 60
  - 1 未満や負数は無効扱いされデフォルトにフォールバック

- SQLITE_PATH
  - 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - Monitoring は本番 sqlite_path を使用する設計（KABUSYS_ENV にかかわらず）

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- OPENAI_API_KEY
  - OpenAI 呼び出しに必要（ai/news_nlp.py, ai/regime_detector.py 等）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API の認証トークン（必須プロパティ参照あり）

- KABU_API_PASSWORD
  - kabuステーション API のパスワード（必須プロパティ参照あり）

- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - ExecutionEngine の PID ファイルや kill.flag のパスや起動時のクリア設定

- PAPER_FILL_MODE
  - Paper Trading の約定モード: `instant|partial|never|reject`（デフォルト `instant`）

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - `1` を設定すると .env 自動読み込みをスキップ

注意: Settings クラスは自動で .env / .env.local をプロジェクトルートから読み込む（.git または pyproject.toml を起点に検索）。環境変数のロード順は OS 環境 > .env.local > .env（ただし OS 環境は保護されるため .env.local でも上書きされない）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールとファイルの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 読み込み / Settings
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py  — SQLite テーブル初期化 / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 ExecutionEngine 関連モジュール — BrokerFactory 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - utils/
    - __init__.py
    - process_priority.py

data/ 以下（実行時に使用／作成される想定）
- data/kabusys.duckdb (デフォルト)
- data/monitoring.db (監視ログ)
- data/paper_trading.db (paper_trading 用)
- data/execution.pid (ExecutionEngine の PID ファイル)
- data/kill.flag (KillSwitch により作られる停止フラグ)

---

## 注意点 / 運用上のポイント

- 監視（Monitoring）は監視専用の SQLite を使って永続化します。スクリプトは起動時に必要テーブルを自動作成（init_monitoring_db）します。
- Paper Trading 実行は本番 DB と完全分離されるため、検証実験が本番データに影響を与えません。
- OpenAI API を利用する機能は API キー必須です。API 呼び出し時のレート制限や 5xx 等はリトライして安全側にフォールバックしますが、コストやレートには注意してください。
- KillSwitch は監視コンポーネントから条件を満たした際に data/kill.flag を書き込み、ExecutionEngine 側で検知して安全に停止させるための仕組みです。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定するとエンジン起動時にフラグをクリアできます。
- プロセス優先度や CPU affinity の設定は utils/process_priority.py で行われます。権限不足等で失敗してもログ出力してスキップします。

---

## サンプル .env（最小例）

以下は動作に必要なキーの最低限の例（実際は各種トークンやパスを適切に設定してください）。

```
# .env
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

この README はコードベースに含まれるモジュールを参照して作成しています。実際の運用やデプロイ時はセキュリティ（API キーの管理、DB アクセス権限）や監視方法、ログの管理ポリシーを必ず整備してください。必要ならば各モジュール（ExecutionEngine、Broker 接続層、DB マイグレーション等）の詳細ドキュメントも作成できます。