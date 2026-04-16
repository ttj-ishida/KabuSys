# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ概要ドキュメントです。  
この README はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買/リサーチ/監視基盤です。  
主に次の役割を持つコンポーネントで構成されています。

- 実行エンジン（ExecutionEngine）: ブローカー API 経由で発注・注文管理を行う
- 監視（Monitoring）: システムの稼働状況・注文状況・リスクを監視しログ化・アラート送信
- ポートフォリオ構成（Portfolio）: 候補選定、重み付け、ポジションサイズ計算
- リサーチ（Research）: DuckDB を使ったファクター計算・特徴量解析
- AI モジュール（AI）: ニュースの NLP 解析や市場レジーム判定（OpenAI API 利用）
- ツール: Paper Trading の検証レポート生成や Streamlit ダッシュボードなど

設計方針として、DB（SQLite / DuckDB）をローカルに持ち、外部 API 呼び出しは明示的かつオプションにしています。Paper Trading モードでは本番 DB と明確に分離されます。

---

## 主な機能（機能一覧）

- Execution
  - ブローカーとの注文送信、注文状態同期、リコンサイル（起動時の自動復旧）
  - Paper Trading モード（モックブローカー、専用 SQLite）
- Monitoring
  - CPU / メモリ / ディスク / プロセス状態の定期ログ記録
  - 注文滞留・約定価格異常の監視
  - ドローダウン・ポジション数上限の監視と Kill Switch（自動停止）機能
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボードで監視情報を可視化
- Portfolio
  - 候補選定（スコア順）、等金額/スコア加重、リスクに基づくポジションサイズ計算
  - セクター上限の適用、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - ニュースのセンチメント解析（OpenAI）→ ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA を合成した市場レジーム判定（OpenAI）
- ツール
  - Paper Trading 検証レポート生成（コマンドライン）
  - Streamlit ダッシュボード起動スクリプト

---

## 依存関係（主な Python パッケージ）

以下のパッケージが使用されています（抜粋）:

- Python 3.8+
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボード使用時)
- sqlite3（標準ライブラリ）

プロジェクトには requirements.txt がない場合がありますので、上記を pip でインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール:
   ```
   pip install -r requirements.txt   # もし requirements.txt があれば
   # あるいは個別インストール
   pip install duckdb psutil openai requests streamlit
   ```

4. データディレクトリを作成（必要に応じて）:
   ```
   mkdir -p data
   ```

5. 環境変数を設定:
   - プロジェクトルートに `.env` / `.env.local` を配置できます（README 下部の「環境変数」を参照）。
   - 自動で `.env` を読み込む仕組みがあります（プロジェクトルートが .git または pyproject.toml を含む場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）

Settings クラスで参照される環境変数（代表）:

- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（AlertManager を使う場合）
- LINE_USER_ID: LINE 宛先ユーザ ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のモック約定挙動（"instant" / "partial" / "never" / "reject"）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: プロセス管理・Kill Switch 関連

.env のサンプル（最低限）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意: Settings._load_env_file は `.env` と `.env.local` を自動読込します。OS 環境変数は上書きされません（`.env.local` は上書き可）。

---

## 使い方（実行方法）

各スクリプトはパッケージモジュールとして起動できます。プロジェクトルートで仮想環境を有効にしたうえで実行してください。

- ExecutionEngine（本番 / Paper Trading）
  - 本番（KABUSYS_ENV=live または development の場合、本番 DB を利用）
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading（環境分離された専用 SQLite を使用）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 実行時、プロセス優先度を "high" に設定します。起動前に `data/stop_requested.flag` が存在すると起動をスキップします。

- Monitoring（SystemMonitor のポーリング）
  - デフォルト 60 秒間隔（環境変数 MONITOR_POLL_INTERVAL で変更可）
    ```
    python -m kabusys.run_monitoring
    ```
  - 停止は `data/stop_requested.flag` を作成すると、次のポーリングで検知して終了します。

- Streamlit ダッシュボード（監視可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視用 SQLite を読み取り専用で参照します（MonitoringEngine が稼働中であることが望ましい）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数か引数で渡す）。
  - 例（プログラム上から呼び出す）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - 実行は DuckDB 接続が必要です（prices_daily / raw_news テーブルを参照）。

---

## 停止 / 強制停止の手順

- 両方のランナー（run_monitoring, run_execution）はプロジェクトルートの data/stop_requested.flag を監視しています。停止したい場合はこのファイルを作成してください（中身は任意）。次のポーリングで検出して正常終了します。
  ```
  touch data/stop_requested.flag
  ```

- KillSwitch（自動停止トリガー）は条件（例: ドローダウン超過）成立時に `data/kill.flag`（または設定された `KILL_FLAG_PATH`）を書き込みます。ExecutionEngine 側ではこのフラグを検出して安全に停止します。起動時にフラグをクリアする設定（KILL_FLAG_CLEAR_ON_START）があります。

---

## 開発時の注意点

- Paper Trading モードは本番データベースと完全に分離された SQLite を使用するため、実験や検証に適しています。
- Settings モジュールはプロジェクトルートを .git または pyproject.toml で検出し、自動的に `.env` / `.env.local` を読み込みます。テスト時に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 周りはレート制限やネットワーク障害に備えてリトライ・フェイルセーフ実装がありますが、API キーとコスト管理には注意してください。
- psutil を利用してプロセス優先度や CPU affinity を操作します。権限不足により設定が失敗する場合は警告を出して処理を継続します。

---

## ディレクトリ構成（主要ファイル／モジュールの説明）

```
src/kabusys/
├── __init__.py                 # パッケージ定義、バージョン
├── config.py                   # 環境変数 / 設定読み込みロジック（Settings）
├── run_execution.py            # ExecutionEngine 起動スクリプト
├── run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
|
├── execution/
│   ├── execution_engine.py     # (実装省略一覧) 実行エンジン本体
│   ├── order_manager.py        # OrderManager: 注文の送信/状態管理
│   ├── order_repository.py     # OrderRepository: SQLite ベースの永続化
│   ├── reconciler.py          # Reconciler: 起動時自動復旧 / ポジション照合
│   └── ...                    # ブローカー関連 API / ファクトリ等
|
├── monitoring/
│   ├── monitoring_db.py        # MonitoringDB: SQLite テーブル作成・読み書き
│   ├── system_monitor.py       # SystemMonitor: CPU/メモリ/データ鮮度監視
│   ├── trade_monitor.py        # TradeMonitor: 滞留注文・約定異常検出
│   ├── risk_monitor.py         # RiskMonitor: ドローダウン等の監視
│   ├── kill_switch.py          # KillSwitch: kill.flag 書き込み / 管理
│   ├── alert_manager.py        # AlertManager: LINE push 通知
│   ├── monitoring_engine.py    # MonitoringEngine: 各 Monitor を束ねる
│   └── streamlit_dashboard.py  # Streamlit ダッシュボード起動スクリプト
|
├── portfolio/
│   ├── portfolio_builder.py    # 候補選定・重み付け
│   ├── position_sizing.py      # 株数決定・スケーリング
│   └── risk_adjustment.py      # セクター制限・レジーム乗数
|
├── research/
│   ├── factor_research.py      # Momentum / Volatility / Value 等
│   ├── feature_exploration.py  # 将来リターン、IC、統計サマリ
│   └── __init__.py
|
├── ai/
│   ├── news_nlp.py             # ニュース NLP（OpenAI）→ ai_scores 書き込み
│   └── regime_detector.py      # 市場レジーム判定（ETF MA + マクロ NLP）
|
├── tools/
│   └── paper_verification_report.py  # Paper Trading 検証レポート生成 CLI
|
└── utils/
    └── process_priority.py     # プロセス優先度 / CPU affinity 設定ユーティリティ
```

各モジュールはコード内に詳細な docstring と設計方針が記述されています。詳細な挙動（DB スキーマ、アラート条件、リトライ戦略など）は各モジュールの docstring を参照してください。

---

## よくある運用フロー（例）

1. DuckDB & SQLite の初期化（必要に応じて prices_daily / raw_news 等のデータ投入）
2. 設定（.env）を整える（API キー、DB パス、KABUSYS_ENV）
3. Monitoring を起動して安定稼働を確認:
   ```
   python -m kabusys.run_monitoring
   ```
4. ExecutionEngine を起動（paper_trading で検証する場合は KABUSYS_ENV=paper_trading）:
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
5. 必要に応じて Streamlit ダッシュボードやツールで状況確認／レポート生成

---

## 補足 / 注意点

- データベースのマイグレーション処理（monitoring_db.init_monitoring_db）は冪等に設計されていますが、運用環境でのバックアップを推奨します。
- OpenAI の使用はコストとレート制限に注意してください。AI モジュールにはリトライ・バックオフロジックが組み込まれていますが、冪等性や部分失敗時のデータ保護設計（例: ai_scores の部分書き換え）に配慮しています。
- 実行プロセスの優先度変更や CPU affinity 操作には権限が必要な場合があります。失敗時は警告が出て継続します。

---

この README はコードベースの主要ポイントをまとめたものです。より詳細な API 仕様やデータスキーマ、設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）が別途ある場合は併せて参照してください。問題や不明点があれば該当モジュールの docstring を確認するか、開発チームに問い合わせてください。