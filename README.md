# KabuSys

日本株自動売買システムのリポジトリ（抜粋）。この README はソースコード（src/kabusys 以下）を元に作成した概要・セットアップ・使い方・ディレクトリ構成の説明です。

注意: この README はコードベースの要点をまとめたもので、実運用に当たっては .env / シークレット管理やブローカー API の仕様、法令順守などを必ず確認してください。

---

## プロジェクト概要

KabuSys は、日本株の自動売買を想定したモジュール群です。主な役割は以下の通りです。

- シグナルに基づく発注（ExecutionEngine / OrderManager）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- 研究用ファクター計算（DuckDB を用いたファクター計算）
- AI を使ったニュースセンチメント・レジーム判定（OpenAI）
- Paper Trading 向けの検証レポート出力ツール
- 監視用ダッシュボード（Streamlit）

設計上の特徴：
- DuckDB / SQLite によるデータ永続化（prices_daily / raw_financials / monitoring DB 等）
- Paper Trading と Live を明確に分離（環境変数で切替）
- 外部 API（OpenAI, kabuステーション など）アクセスをモジュールで抽象化
- フェイルセーフ（API 失敗時のフォールバック、冪等性を考慮した DB 書き込み）

---

## 機能一覧（主な機能）

- Execution
  - 発注の作成・送信・状態同期（OrderManager / Reconciler）
  - リスク管理（RiskManager）
  - 起動時の再同期（Reconciler）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / プロセス）
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視（Kill Switch による停止トリガー）
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード表示
- Portfolio construction
  - 候補選定、重み計算（等配分・スコア加重）
  - セクター制限、レジーム乗数適用
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で完結）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - マクロ + MA200 での市場レジーム判定（OpenAI＋DuckDB）
- ユーティリティ
  - process priority / CPU affinity 設定（psutil）
  - .env 自動読み込み（プロジェクトルート .env / .env.local を参照）

---

## 前提 / 必要条件

- Python 3.10+
- パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai（OpenAI クライアント）
- ブローカー API クライアント等は実装やモック次第（paper_trading 環境では MockBrokerClient を使用）

インストール例（仮）:
pip install duckdb psutil requests streamlit openai

プロジェクトを editable インストールする場合:
pip install -e .  （setup があれば）

---

## 環境変数（主なもの）

Settings クラスで参照される主な環境変数（デフォルト値を含む）:

- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト: 60）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（AI 関連モジュールで使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

.env 自動読み込み:
- プロジェクトルートに対して .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（ローカル開発向け）

1. Python をインストール（3.10 以上推奨）。

2. 依存ライブラリをインストール:
   pip install duckdb psutil requests streamlit openai

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを使用）

3. プロジェクトルートに data ディレクトリを作成:
   mkdir -p data

4. 環境変数を設定（例: .env ファイルを作成）
   例 (.env):
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   OPENAI_API_KEY=your_openai_key
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

5. 初回 DB 初期化:
   - run_monitoring や run_execution を起動すると、init_monitoring_db により monitoring DB のテーブルが作成されます。
   - DuckDB にも価格等のテーブルが必要です（prices_daily 等）。研究機能を使う場合は適切にデータをロードしてください。

---

## 使い方（主要スクリプト・コマンド）

ソースは `src/kabusys` にあるため、パッケージとして実行できます。

1. 監視プロセスの起動（SystemMonitor のポーリングループ）
   - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
   - 実行コマンド例:
     python -m kabusys.run_monitoring
   - 停止:
     - プロセスを Ctrl+C で止めるか、プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが終了します。

2. ExecutionEngine（発注エンジン）の起動
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
   - 実行コマンド例:
     python -m kabusys.run_execution
   - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
   - 停止:
     - data/stop_requested.flag を作成するとエンジンが停止処理を行います。
     - Kill Switch 経由で強制停止したい場合は monitoring が条件を満たすと data/kill.flag が書き込まれます（ExecutionEngine は kill.flag を見て停止判定を行います）。

3. Streamlit ダッシュボード（監視）
   - 起動例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で監視 DB を開きます。MonitoringEngine がデータを書き込んでいることが前提です。

4. Paper Trading 検証レポートの生成
   - コマンド:
     python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     --db <path> または環境変数 PAPER_TRADING_SQLITE_PATH

5. AI 関連（ニューススコア / レジーム判定）
   - OpenAI API キーが必要（env OPENAI_API_KEY）。
   - ニューススコア例（呼び出しは Python から関数を呼ぶ形）:
     from kabusys.ai.news_nlp import score_news
     score_news(conn, target_date, api_key="...")
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, target_date, api_key="...")

6. 停止フラグ / PID
   - 監視スクリプトは data/stop_requested.flag を監視して安全終了します。
   - ExecutionEngine が起動すると data/execution.pid に PID を書く実装になっています（PID の stale 検出ロジックあり）。

---

## よく使うファイル / 動作のポイント

- src/kabusys/config.py
  - .env 自動読み込みの実装、Settings クラス。必須環境変数をチェック。
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔設定。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意。
- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト。paper_trading 環境時は paper_sqlite_path を使用。
- src/kabusys/monitoring/
  - MonitoringDB（SQLite のスキーマ初期化 / CRUD）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine
- src/kabusys/portfolio/
  - portfolio_builder, position_sizing, risk_adjustment — ポートフォリオ構築ロジック
- src/kabusys/research/
  - ファクター計算・統計解析
- src/kabusys/ai/
  - news_nlp.py, regime_detector.py — OpenAI を用いた処理

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/  (ランタイムで作られるディレクトリ。デフォルト DB 等を格納)
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB データベース)

（上記はコードベースから抽出した主要ファイル一覧です）

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API キー等）は環境変数または安全なシークレットストアで管理してください。リポジトリにコミットしないでください。
- 本番運用では KABUSYS_ENV=live に設定し、paper_trading 用 DB と明確に切り分けてください。
- OpenAI API 呼び出しにはレート制限やコストが伴います。batch サイズやリトライポリシーはコードで制御されていますが、十分にテストしてから運用してください。
- monitoring は process の稼働・データ鮮度を確認して kill.flag を書くことで ExecutionEngine を安全に停止できます。kill.flag は意図せず書かれないよう監視設定を確認してください。
- psutil を使ったプロセス優先度設定は権限によって失敗する場合があります（ログに警告が出ます）。

---

## トラブルシュート（簡易）

- DB の初期テーブルが作成されない:
  - run_monitoring/run_execution を起動すると init_monitoring_db が実行されます。data ディレクトリのパーミッションや SQLite ファイルパスを確認してください。
- Streamlit が DB を開けない:
  - read-only 接続で URI を組み立てているため、ファイルが存在するか、パスが正しいか確認してください。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY を確認し、ネットワーク接続や API 制限を確認してください。ログのリトライ警告を参照。

---

必要であれば、README に次のような追加情報を盛れます：
- .env.example のサンプル
- 完全な依存パッケージ一覧 (requirements.txt)
- CI / テストの実行方法（ユニットテスト、モック戦略）
- 実運用でのデプロイ手順（systemd/コンテナ化など）

要望があれば上記のいずれか（.env.example、requirements.txt、systemd unit ファイルの例など）を追記します。