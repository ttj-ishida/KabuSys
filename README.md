# KabuSys

軽量な日本株自動売買システムのコアライブラリ群と運用用スクリプト群です。本リポジトリには取引エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

注意: 提供されたソースはフレームワーク／ライブラリ群と実行スクリプト群です。実運用に使用する場合は各 BrokerClient 実装、認証情報、バックテストや安全性確認を必ず行ってください。

## 目次
- プロジェクト概要
- 主な機能一覧
- 要件・依存パッケージ
- セットアップ手順
- 実行方法（使い方）
- 環境変数（主要）
- 停止 / フラグ制御
- 主要モジュールの説明
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向け自動売買システムの核となるモジュール群です。主な責務は以下の通りです。

- ExecutionEngine：シグナルに基づく発注の管理と注文状態追跡、リコンシリエーション
- MonitoringEngine：システムの健康状態・注文の滞留・リスク指標のポーリング監視、アラート送信
- Portfolio：候補選定、重み計算、ポジションサイズ計算、セクター制約など
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：ニュースを用いたセンチメントスコアリング（OpenAI）と市場レジーム判定
- Tools：運用支援スクリプト（Paper Trading 検証レポート生成など）
- ユーティリティ：プロセス優先度設定、.env の読み込み等

---

## 主な機能一覧
- 実行エンジン（本番 / Paper Trading 切替）とブローカーファクトリ
- 起動時リコンシリエーション（未同期な注文やポジション差分の検出）
- 監視：
  - システム資源（CPU/Mem/Disk）監視、Execution プロセス生存確認
  - 注文滞留（stale orders）・約定異常価格検知
  - ドローダウン・ポジション上限監視と Kill Switch（停止フラグ書き込み）
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築ユーティリティ：
  - 候補選定（スコア順）、等金額／スコア加重配分、リスクベース給付、セクターキャップ、レジーム乗数
- Research：
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC 計算、統計サマリ
- AI：
  - raw_news を OpenAI に問い合わせて銘柄毎のセンチメント（ai_scores）を書き込み
  - ETF ベースの MA とマクロニュースを組み合わせた市場レジーム判定
- 運用ツール：
  - Paper Trading の検証レポート生成スクリプト

---

## 要件・依存パッケージ
推奨 Python バージョン: 3.10 以上（`|` 型アノテーション等を使用）

主な外部依存:
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボード用)
- （標準ライブラリ）sqlite3, logging, threading, datetime, pathlib など

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai requests streamlit
```

プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を利用してください。

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. 環境変数 / .env の準備
   - `src/kabusys/config.py` は自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 代表的な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用）
     - KABU_API_PASSWORD（kabu API 用）
     - OPENAI_API_KEY（AI モジュール実行時に必要）
   - DB パスや挙動を変更する主要変数は下記の「環境変数（主要）」を参照。
4. `data/` ディレクトリを作っておく（PID・flag・DB のデフォルトパスが data 以下です）。
   ```
   mkdir -p data
   ```

---

## 実行方法（使い方）

基本的にプロジェクトルートから `PYTHONPATH=src` を指定してモジュールを実行します。パッケージとしてインストール済みであれば `python -m kabusys.run_execution` 形式で実行できます。

- ExecutionEngine 起動（本番／paper_trading 切替）
  ```
  # 本番モード（デフォルト KABUSYS_ENV=development だが production/live 切替は env で制御）
  PYTHONPATH=src python -m kabusys.run_execution

  # Paper Trading モード（MockBrokerClient を使用し DB を data/paper_trading.db に分離）
  export KABUSYS_ENV=paper_trading
  PYTHONPATH=src python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング）
  ```
  # デフォルトポーリング間隔 60 秒。環境変数で上書き可能
  export MONITOR_POLL_INTERVAL=30
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード（読み取り専用で監視 DB を開く）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  # DB 指定
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ニューススコア・レジーム判定）
  - ai モジュールは DuckDB 接続と OpenAI API キーを必要とします。関数を直接呼ぶ形で使用してください（例: `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime`）。
  - 例（スクリプト等から）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026, 4, 1), api_key="sk-xxxx")
    ```

---

## 環境変数（主要）
（省略時は README に記載のデフォルト値が使われます）

- KABUSYS_ENV: 起動環境。valid: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite DB（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイルパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring が使用するポーリング間隔（秒、デフォルト 60）

その他、Monitoring のしきい値等は Settings で取得可能：
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

---

## 停止 / フラグ制御
運用中の停止・強制停止はフラグファイルにより行います。

- data/stop_requested.flag:
  - run_execution.py / run_monitoring.py はこのファイルを検出するとループを終了します（スクリプト側でチェック）。
- data/kill.flag:
  - KillSwitch クラスは条件を満たしたときに `KILL_FLAG_PATH` に理由を書き込みます（ExecutionEngine は起動時にこのフラグを検査／必要に応じて削除します）。
- PID ファイル:
  - ExecutionEngine は設定された PID ファイルに自プロセス PID を書きます。SystemMonitor は PID ファイルを参照してプロセス存否をチェックします。

---

## 主要モジュール説明（概要）
- kabusys.config
  - .env 自動読み込み（.env / .env.local）、Settings クラスで環境変数のラップ。
- kabusys.execution
  - order_manager, order_repository, reconciler, execution_engine 等（注文管理と復旧ロジック）。
- kabusys.monitoring
  - system_monitor, trade_monitor, risk_monitor, monitoring_db（監視ログの永続化）、alert_manager（LINE 通知）、monitoring_engine。
- kabusys.portfolio
  - portfolio_builder（候補選定・重み算出）、position_sizing（株数計算）、risk_adjustment（セクター制約・レジーム）。
- kabusys.research
  - factor_research（momentum/volatility/value）、feature_exploration（IC/forward returns 等）。
- kabusys.ai
  - news_nlp（ニュース集計→OpenAI→ai_scores 書き込み）、regime_detector（MA とマクロニュースを合成してレジーム判定）。
- kabusys.utils
  - process_priority（プロセス優先度設定、CPU affinity）

---

## ディレクトリ構成
（主要ファイルを抜粋した概観）

src/
  kabusys/
    __init__.py
    config.py
    run_execution.py
    run_monitoring.py
    tools/
      __init__.py
      paper_verification_report.py
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
      __init__.py
      news_nlp.py
      regime_detector.py
    monitoring/
      __init__.py
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      (他、broker_factory 等)
    utils/
      __init__.py
      process_priority.py
    portfolio/ (上記)
    research/ (上記)
data/
  (デフォルトの DB / PID / flag を置く場所: monitoring.db, kabusys.duckdb, paper_trading.db, execution.pid, kill.flag, stop_requested.flag)

---

## 運用上の注意
- Paper Trading モードでは本番 DB と書き込みを分離します（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能を使う場合は OpenAI API キーの管理に十分注意してください。API 呼び出しは課金対象になります。
- プロセス優先度設定や CPU affinity 設定は OS 権限によって失敗する可能性があり、その場合は警告ログでスキップされます。
- monitoring_db.init_monitoring_db は起動時に冪等的にテーブルを作成／簡易マイグレーションを行います。
- データ鮮度や PID ファイルの検査は SystemMonitor が行います。PID ファイルの不整合は自動的に修正（削除）され、risk_logs に記録されます。
- Streamlit で DB を開く際、監視 DB を読み取り専用で開くことをお勧めします（streamlit ダッシュボードのヘッダー引数参照）。

---

README に記載してほしい追加の情報（例: broker 実装の使い方、設定例の .env.example、実行の Docker 化手順など）があれば教えてください。必要に応じてサンプル .env や起動スクリプトの例を作成します。