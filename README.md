# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアコンポーネント群を含みます。  
設計は運用（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI（News NLP / Regime Detector）といった責務に分離されており、Paper Trading と本番（Live）を分離して検証・運用できるようになっています。

---

## 概要

- 設計方針は「安全」「フェイルセーフ」「ルックアヘッドバイアス排除」。  
- 実取引（kabuステーション等）とPaper Trading（モックブローカー）を環境変数で切り替え可能。Paper Trading は本番DBと完全に分離して記録します。  
- DuckDB / SQLite を併用して時系列データ・監視ログ・取引ログを保持。  
- LINE によるアラート送信、Streamlit ベースの簡易ダッシュボード、OpenAI を用いたニュース NLP / レジーム判定などの補助機能を備えます。

---

## 主な機能一覧

- Execution（ExecutionEngine）
  - 注文発行・状態管理（OrderManager / OrderRepository）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
  - Paper Trading モード（MockBrokerClient）をサポート（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文検出、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視・ダッシュボード更新
  - KillSwitch：一定条件で data/kill.flag を書いて ExecutionEngine を停止
  - AlertManager：LINE による通知とクールダウン管理
  - Streamlit ダッシュボード（監視用）
- Portfolio（銘柄選定・配分・サイズ決定）
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（単元丸め・aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp：ニュースを OpenAI に投げて銘柄ごとの sentiment / ai_score を算出し ai_scores に書き込み
  - regime_detector：ETF 1321 の MA とマクロニュースの LLM センチメントを合成して market_regime を判定・保存
- ツール
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ 等）

---

## 必須・推奨環境

- Python 3.9+（コードは typing の構文やモジュールを利用）
- 必要な Python パッケージ（代表的なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - (必要に応じて) pytest / unittest 等

（プロジェクトに requirements.txt があればそれを使用してください。なければ上に列挙したパッケージをインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# または requirements.txt があれば: pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをチェックアウトして Python 仮想環境を作成・有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. プロジェクトルートに `data/` ディレクトリを作る（DB・PID・フラグファイルを置くため）。
   ```bash
   mkdir -p data
   ```
4. 環境変数を設定する。`.env`（および `.env.local`）を作成することで自動的に読み込まれます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 主要な環境変数（最低限設定が必要なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必要な場合）
     - KABU_API_PASSWORD — kabuステーション API パスワード（実取引時必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合
     - その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, LOG_LEVEL など
   - 例（.env の内容の例、値は適宜置き換えてください）:
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```
5. （Paper Trading の場合）`KABUSYS_ENV=paper_trading` を設定すると、MockBroker を使用し `PAPER_TRADING_SQLITE_PATH` に結果が記録されます。

---

## 実行方法（代表例）

- 監視ループを起動（Monitoring）
  ```bash
  # モジュールとして実行
  python -m kabusys.run_monitoring
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔: 60 秒
  - run_monitoring は常に本番用の sqlite_path を使用して監視テーブルを記録します（環境に依らず本番 DB を参照する仕様）。

- 実行エンジンを起動（Execution）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/execution.pid（デフォルト）に PID を書き、停止時は stop フラグや kill.flag に反応します。

- Streamlit ダッシュボード（監視用）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 運用上の注意

- stop 制御:
  - プロジェクトルートの `data/stop_requested.flag` を作ると run_monitoring / run_execution が検出して終了処理を行います。
  - `KillSwitch` は `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります（リスク条件に応じて監視から自動生成）。
- PID / フラグファイルの場所は Settings でカスタマイズ可能（環境変数 PID_FILE_PATH / KILL_FLAG_PATH）。
- Paper Trading は本番 DB と分離して記録されるため、検証中に本番データを汚さない設計です（settings.is_paper による分岐）。
- OpenAI 連携機能（news_nlp / regime_detector）を使う場合は API キー（OPENAI_API_KEY）が必須です。APIエラー時はフェイルセーフ（0.0 にフォールバック等）する設計です。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- MONITOR_POLL_INTERVAL (監視ループの間隔（秒）、デフォルト: 60)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

---

## 主要ディレクトリ構成

（src/kabusys 以下の主要ファイル・ディレクトリと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定の読み込み・検証（.env 自動ロード機能含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Paper Trading 切替あり）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores へ書き込む
    - regime_detector.py — MA と LLM を合成して market_regime を求める
  - monitoring/
    - monitoring_db.py — 監視ログ用 SQLite テーブル初期化とアクセサ
    - system_monitor.py — CPU/mem/disk/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルベースの停止シグナル管理
    - alert_manager.py — LINE へのプッシュ通知管理
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - reconciler.py — 起動時の注文・ポジション再同期ロジック
    - order_manager.py — 注文発行と状態遷移 API
    - order_repository.py — SQLite ベースの注文永続化（ファイル内に存在）
    - ...（Broker 関連・ExecutionEngine 等の実装がある前提）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等額 / スコア加重）
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 株数算出・単元丸め・aggregate cap
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - data/（実行時に使用されるファイル）
    - monitoring.db — 監視ログ（SQLite）
    - paper_trading.db — Paper Trading 用 SQLite（Paperモード時）
    - kabusys.duckdb — 時系列・リサーチ用 DuckDB
    - execution.pid, stop_requested.flag, kill.flag などの制御ファイル
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発・テストに関するヒント

- Settings（config.py）は `.env` / `.env.local` を自動的にプロジェクトルートから読み込みます（CWD に依存せず __file__ を基準にプロジェクトルートを探します）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 多くの関数は DuckDB / SQLite 接続を引数で受け取る純粋関数設計で、単体テストが容易です。OpenAI や外部 API 呼び出しは呼び出し箇所を分離しているためモック可能です（例: news_nlp._call_openai_api を patch）。
- データ鮮度チェック・レジーム判定・ニュース NLP の実行はルックアヘッドバイアス対策として日付参照方法に注意しています（target_date を明示的に渡す等）。

---

この README はコードベースの要点をまとめたものです。より詳細な設計意図（例: PortfolioConstruction.md、StrategyModel.md）や実運用手順は別途ドキュメントを参照してください。README の内容やサンプル .env などの追記希望があれば教えてください。