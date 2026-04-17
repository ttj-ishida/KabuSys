# KabuSys

日本株自動売買システム（ライブラリ＋実行ユーティリティ群）

このリポジトリは、システム監視、ExecutionEngine（発注エンジン）、ポートフォリオ構築、ファクター研究、ニュースNLP（OpenAI）などを含む日本株自動売買システムのコアモジュール群です。モジュールはテスト可能な純粋関数と I/O 層（SQLite / DuckDB / Broker API / OpenAI）を分離して設計されています。

## 主な特徴（機能一覧）

- 実行エンジン起動スクリプト（run_execution）
  - 本番 / paper_trading（モックブローカー）を環境変数で切り替え
  - 起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）、OrderManager、OrderRepository 組み合わせによる発注管理

- 監視サブシステム（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス健全性 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件を満たすと stop フラグを書き込み実行エンジン停止を要求
  - AlertManager: LINE Push による通知（クールダウン付き）
  - MonitoringEngine: すべての Monitor を束ねてポーリング実行
  - SQLite ベースの永続化層（monitoring_db）

- 研究・データ処理（research）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリ

- ポートフォリオ構築（portfolio）
  - 候補選定、等重 / スコア重み付け、セクター制約、ポジションサイズ計算（丸め・lot 単位対応）

- AI（OpenAI）統合（ai）
  - news_nlp: ニュース記事の銘柄別センチメントを OpenAI で評価して ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースを合わせて市場レジーム判定し DB に保存

- ツール
  - paper_verification_report: Paper Trading 用検証レポート生成（稼働率・注文成功率・レイテンシ等）
  - streamlit_dashboard: 監視ダッシュボード（streamlit）

## 要件（Dependencies）

- Python 3.10+（型ヒントに | を使用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（組み込み）、標準ライブラリ

（実際の環境では requirements.txt を用意して pip install -r でインストールしてください。なければ上記パッケージを個別にインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存関係をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install duckdb psutil requests openai streamlit
   ```

3. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（OS の環境変数が優先）。
   - 重要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN — J-Quants API
     - KABU_API_PASSWORD — kabuステーション API
     - OPENAI_API_KEY — OpenAI Key（ai モジュール利用時）
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — Paper Trading の約定動作（instant, partial, never, reject）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（paper_trading 環境で利用）

   例（.env）
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=INFO
   ```

5. 初期 DB 作成
   - Monitoring 用 DB（デフォルト: data/monitoring.db）は実行スクリプトが自動で初期化します（init_monitoring_db を呼ぶ）。

## 使い方（主要な実行コマンド）

モジュールはパッケージとして実行できます（python -m kabusys.<module>）。

- 監視ループを起動（SystemMonitor 単体のポーリングランナー）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能。例: `export MONITOR_POLL_INTERVAL=30`
  - 監視プロセスは data/stop_requested.flag を検知するとループを終了します。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境に依存せず）。

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。本番環境は別の SQLite を使用。
  - data/execution.pid に PID を書き、停止は data/stop_requested.flag で指示できます。

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - デフォルトは data/monitoring.db。監視が走っていないと読み込みエラーになります（read-only URI 経由で接続）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI / レジーム判定・ニューススコアリング（ライブラリ呼び出し）
  - Python から直接関数を呼び出して利用します（OpenAI API Key 必須）。
    例:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - 同様に regime_detector.score_regime を使って市場レジームを計算できます。

- ライブラリ的利用（研究・ポートフォリオ等）
  - factor_research.calc_momentum / calc_volatility / calc_value
  - research.calc_forward_returns / calc_ic / factor_summary
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier

## 停止・フラグファイルについて

- data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（作成で停止、削除で再起動）
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止シグナルを送信するためのフラグ（KillSwitch は監視結果に基づき書き込む）
- data/execution.pid: ExecutionEngine の PID 保存場所（Settings.pid_file_path で上書き可）

## 主要な設定項目（Settings）

Settings クラス（kabusys.config）で環境変数から設定を取得します。主な設定:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY（ai モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（monitoring, default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading DB, default: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live
- PAPER_FILL_MODE: instant | partial | never | reject

Settings は .env(.local) の自動読み込みに対応（プロジェクトルートの検出：.git または pyproject.toml を基準）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## ディレクトリ構成（抜粋）

（ファイルは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings 管理
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねるランナー
  - streamlit_dashboard.py — Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 発注の上位 API（OrderState 管理）
  - reconciler.py — 起動時自動復旧 / リコンシリエーション
  - (その他ブローカー関連・order_repository 等)

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・スケーリング・丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュースNLPスコアリング（OpenAI）
  - regime_detector.py — マクロ + MA を使ったレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ヘルパー

## 運用上の注意点

- Paper Trading と本番 DB は意図的に分離されています（Settings.is_paper 判定で paper_sqlite_path を使用）。
- OpenAI 呼び出しは外部 API であり、キー管理・レート制限・エラーハンドリングを適切に行ってください。news_nlp と regime_detector はリトライロジックやフェイルセーフを実装していますが、運用時には API 使用量やコストに注意してください。
- モジュールはルックアヘッドバイアスを防ぐため、target_date に対するデータ取得時に未来データを参照しない設計になっています（research, ai モジュール等）。
- プロセス優先度設定や CPU affinity の変更には権限が必要になる場合があります（psutil に依存）。権限不足時には警告が出てスキップされます。

---

さらに詳しい使用法や内部設計（PortfolioConstruction.md / StrategyModel.md 等）は別ドキュメントで管理されている想定です。必要であれば README を拡張して具体的な設定例、運用手順、API 契約仕様を追記します。