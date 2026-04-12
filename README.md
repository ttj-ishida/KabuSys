# KabuSys

日本株自動売買システムの一部コードベース（抜粋）の README。  
このドキュメントはプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件 / インストール
- 環境変数 / .env の取り扱い
- セットアップ手順
- 使い方（実行例）
- 主要設定項目（よく使う環境変数）
- ディレクトリ構成（主要ファイルの説明）
- 開発・検証用ツール

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム用のライブラリ/ツール群です。  
このリポジトリには主に以下の機能群が含まれます。

- 注文・発注の管理（OrderManager / ExecutionEngine）
- モニタリング（System / Trade / Risk の監視、アラート、kill switch）
- ポートフォリオ構築（候補選定・重み計算・ロット丸め・リスク調整）
- 研究/リサーチ用モジュール（ファクター計算、将来リターン、IC など）
- AI を用いたニュースセンチメント（OpenAI API 経由）
- DuckDB/SQLite を用いたデータ操作、Streamlit ダッシュボード
- 各種ユーティリティ（プロセス優先度設定、.env ローダー等）

設計方針の一例:
- DuckDB を使って時系列ファクターを高速に計算
- Paper Trading と Live の DB を明確に分離
- 外部 API 呼び出しは安全にリトライやフォールバックを行う（フェイルセーフ）
- ルックアヘッドバイアスを避ける（date.now などの扱いに注意）

---

## 機能一覧

- Execution
  - ExecutionEngine（実行セッションの起動）
  - OrderManager（注文ライフサイクル管理）
  - Reconciler（再起動時の注文・ポジション整合）
  - Broker クライアント切替（paper_trading 時にモック使用）

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存/データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン、ポジション上限）
  - MonitoringDB（SQLite ベースの永続層）
  - AlertManager（LINE Push で通知）
  - KillSwitch（flag ファイルを用いた停止シグナル）
  - Streamlit ダッシュボード（監視データ可視化）

- Portfolio
  - 候補選定 (select_candidates)
  - 重み計算（等金額 / スコア加重）
  - ポジション数決定（リスクベース / 重みベース）
  - セクター集中制限、レジーム乗数

- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman）などの統計分析

- AI
  - ニュース NLP（OpenAI を用いた銘柄別センチメント計算）
  - 市場レジーム判定（MA200 とマクロニュースセンチメント合成）

- Tools
  - paper_verification_report（Paper Trading の検証レポート生成）

---

## 必要条件 / インストール

推奨: Python 3.10+

主な依存ライブラリ（抜粋）
- duckdb
- psutil
- requests
- openai
- streamlit  （ダッシュボードを使う場合）
- その他、プロジェクト固有のライブラリがある場合は pyproject.toml を参照してください。

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # このリポジトリに requirements.txt がある前提
# または個別:
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数 / .env の取り扱い

- 設定は環境変数かプロジェクトルートの `.env` / `.env.local` から読み込まれます。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須変数が未設定の場合は Settings クラスのプロパティで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

よく使う環境変数（主なもの）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading でのモック成行/部分約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス PID ファイル / Kill flag ファイルパス

簡単な .env 例:
```env
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
```

注意: Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env を自動読み込みします。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークディレクトリに移動
2. Python 仮想環境作成 & 依存インストール
3. 必要な環境変数を設定（`.env` に記述する方法が推奨）
4. データディレクトリ（`data/`）を作成し、DuckDB / SQLite ファイルを配置または初期化
   - Monitoring は init_monitoring_db() により必要テーブルを自動作成します
5. （Paper Trading を使う場合）PAPER_TRADING_SQLITE_PATH が指す DB を用意するか初回実行で生成されます

---

## 使い方（実行例）

基本的に Python モジュールを直接実行する形です。ログは INFO レベルで出力されます。

- ExecutionEngine を起動（本番/ペーパー切替は KABUSYS_ENV）:
  ```bash
  # 本番なら: export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```
  - paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に分離して記録されます。
  - 起動時にプロセス優先度を "high" にセットします（set_process_priority 実行）。

- Monitoring（ポーリング）を起動:
  ```bash
  # MONITOR_POLL_INTERVAL を秒で上書き可能
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は本番 sqlite_path を常に使用（環境に依らず）。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）。
  - PID ファイル / kill.flag と連携して ExecutionEngine の監視／停止制御を行います。

- Streamlit ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視 SQLite を読み取り専用で開きます。MonitoringEngine が先に動いている必要があります。

- Paper Trading 検証レポート（ツール）:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI（ニュース NLP / レジーム判定）:
  - OpenAI API キーが必須（OPENAI_API_KEY）。
  - プログラム的に呼び出す:
    - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
    - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 内部で gpt-4o-mini を利用する設計（モデル名はモジュールにハードコード）。

---

## 主要設定項目（補足）

- KABUSYS_ENV:
  - development（デフォルト）
  - paper_trading（MockBroker + 専用 DB）
  - live（本番）
- PAPER_FILL_MODE（paper_trading 用）
  - instant / partial / never / reject（不正値は ValueError）
- MONITOR_POLL_INTERVAL:
  - 1 以上の秒数。0 以下や不正値はデフォルト(60s)にフォールバックする。
- PID_FILE_PATH, KILL_FLAG_PATH:
  - ExecutionEngine / Monitoring がプロセス状態と停止フラグを共有するために使用。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主なモジュールと簡単な説明です。

- kabusys/
  - __init__.py
    - パッケージ情報（バージョン、エクスポート）
  - config.py
    - Settings クラス: 環境変数 / .env 読み込み、各種設定プロパティ
    - 自動 .env ロードの実装（プロジェクトルート検出）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（process priority 設定、DB 接続、エンジン起動）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py
      - psutil を使ってプロセス優先度 / CPU affinity を設定するユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite による永続層、テーブル初期化、CRUD 的メソッド（MonitoringDB）
    - system_monitor.py, trade_monitor.py, risk_monitor.py
      - 各種監視コンポーネント（check_once メソッドを持つ）
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン（run / run_once）
    - kill_switch.py
      - kill.flag を書いて ExecutionEngine 停止を指示するユーティリティ
    - alert_manager.py
      - LINE Push による通知送信
    - streamlit_dashboard.py
      - Streamlit を使った監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, order_record.py, broker_factory.py, execution_engine.py
      - 注文・リコンシリエーション・ブローカー抽象化に関する実装（主要ロジック）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - ポートフォリオ構築・位置サイズ計算・リスク調整（純粋関数群）
  - research/
    - factor_research.py, feature_exploration.py
      - DuckDB を使ったファクター計算、将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py
      - ニュースを集約して OpenAI に投げ、銘柄別にセンチメントを計算して ai_scores に書き込む
    - regime_detector.py
      - マクロニュース + ETF MA200 乖離を合成して日次レジームを決定して DB に書き込む
  - tools/
    - paper_verification_report.py
      - Paper Trading DB を解析し稼働率・注文成功率・レイテンシ等のレポートを生成する CLI ツール

（なお data/ 以下に DB ファイルや PID / flag ファイルを置く設計になっています。）

---

## 開発・検証用メモ

- MonitoringEngine.run_once() / MonitoringEngine.run() により単発実行 / ループ実行が可能。テスト時は run_once を使うと良いです。
- MonitoringDB.init_monitoring_db() は冪等で、既存 DB の簡易マイグレーション（カラム追加）も行います。
- OpenAI API 呼び出し部分はリトライ・レスポンスのバリデーション・JSON 修復ロジックを備えていますが、API キー・レート制限には注意してください。
- Paper Trading は実装上、本番 DB と厳密に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

以上がこのコードベースの README.md 風ドキュメントです。  
必要であれば README に以下を追加できます:
- 詳しい環境変数一覧（すべての Settings プロパティ）
- CI / テスト実行方法（ユニットテスト・モックの使い方）
- データベーススキーマ (DuckDB の prices_daily / raw_financials 等)
- 開発フロー（ブランチ運用やデプロイ手順）

どの追加情報を優先的に盛り込むか教えてください。