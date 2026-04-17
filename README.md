# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群を含む Python パッケージです。戦略のファクター計算、ポートフォリオ構築、発注エンジン、実行監視、AI によるニュース解析などのコンポーネントを備えます。

## 主な特徴
- 実行系（ExecutionEngine）
  - ブローカー抽象（本番・モック切替）
  - 注文管理（OrderManager / OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - システム状態（CPU / メモリ / ディスク）とプロセス生存確認
  - 注文滞留・約定異常・ドローダウン監視
  - LINE によるアラート送信（AlertManager）
  - Kill Switch（条件に応じた停止フラグ生成）
  - Streamlit ダッシュボード（監視データ可視化）
- 研究 / リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）等の統計解析
- ポートフォリオ構築
  - 候補選定、重み計算（等金額 / スコア重み）
  - セクター上限・レジーム乗数、リスクベースのポジションサイズ計算
- AI / ニュース解析
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai_scores テーブル）
  - 市場レジーム検出（ETF とマクロニュースの合成）
- ユーティリティ
  - 環境変数の自動読み込み（.env / .env.local）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 必要な依存関係（主なもの）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3 等

（実行環境に合わせて requirements.txt / Poetry 等で管理してください。）

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして、パッケージをインストール
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # または個別に duckdb psutil requests openai streamlit など
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（既存の OS 環境変数は上書きされません）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading 用
   - PAPER_TRADING_SQLITE_PATH — Paper Trading の専用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, CPU_THRESHOLD_PCT, など

3. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 実行方法（主要スクリプト）

- 監視ループ起動（SystemMonitor のポーリング）
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を設定可能。デフォルトは 60 秒。
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 補足:
    - 監視は Settings に関わらず本番用の sqlite_path を使用します（監視ログは共通で保持）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで行えます（このスクリプトはそれを監視して終了します）。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV により動作が切り替わります：
    - paper_trading: MockBrokerClient を使用し、DB は `data/paper_trading.db`（分離）を使用
    - live/development: 本番 DB を使用
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - プロセス起動時に `data/execution.pid` が作成されます（Settings.pid_file_path）。PID の存在チェックでプロセス生存を確認します。
    - `data/stop_requested.flag` が存在すると起動しない / 実行中に検知すると停止します。

- Paper Trading 検証レポート生成
  - usage:
    ```
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB: `data/paper_trading.db`。別パスを指定する場合は `--db` オプションか環境変数 `PAPER_TRADING_SQLITE_PATH` を使用。

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB を読み取り専用で開き、ポートフォリオ / 注文 / システム状態を可視化します。

- AI / レジームスコア・ニューススコア
  - news_nlp.score_news, regime_detector.score_regime などの関数は DuckDB 接続と target_date, OpenAI API キーを渡して呼び出します。
  - API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用します。

---

## 主要な設定・振る舞い（要点）
- 環境自動読み込み
  - プロジェクトルートを .git または pyproject.toml から検出して `.env` と `.env.local` を順次読み込む（OS 環境変数を保護）。
- KABUSYS_ENV
  - development / paper_trading / live のいずれか。無効な値はエラーになります。
  - paper_trading は発注処理を完全に分離した DB と MockBrokerClient で行う設計。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。1 未満や負の値は無効とみなされデフォルト 60 秒にフォールバック。
- Kill / Stop フラグ
  - `data/kill.flag`：KillSwitch により書き込まれることで ExecutionEngine に停止シグナルを送る（Execution 側は Settings.kill_flag_path を参照）。
  - `data/stop_requested.flag`：run_monitoring/run_execution が存在をチェックして即時停止または起動抑止を行う。
- DB（SQLite / DuckDB）
  - 監視ログは SQLite（Settings.sqlite_path）に保存され、init_monitoring_db により必要テーブルが作成されます（マイグレーションを含む）。
  - 分析やファクター系は DuckDB（Settings.duckdb_path）を利用。

---

## 使い方（例）
- 監視ループ（デフォルト間隔 60s）をバックグラウンドで起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring &
  ```
- 実行エンジン（Paper Trading）を起動:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
- Paper Trading レポート（直近の検証）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- Streamlit ダッシュボード（別ターミナル）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Kill flag を手動でクリア／書き込み（運用者向け）
  - クリア:
    ```
    rm -f data/kill.flag
    ```
  - （KillSwitch は自動的に条件を満たすと書き込むため手動で書き込むのは注意が必要です）

---

## ディレクトリ構成（主要ファイル）
下は src/kabusys 以下の主要モジュールのツリー（抜粋）です。

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
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他ブローカー / order_repository 等の実装ファイル)
    - utils/
      - __init__.py
      - process_priority.py
    - research/、data/ 等（データパイプラインや統計ユーティリティが別ディレクトリで提供されます）

---

## 開発者向けノート
- 環境変数のパースは config.py の独自実装を使用しています。`.env` の書式やクォート・エスケープの扱いに注意してください。
- DuckDB クエリは SQL ウィンドウ関数を多用しており、prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。
- OpenAI 絡みの処理は外部 API の不安定性を考慮し、リトライやフェイルセーフ（失敗時スコア 0.0 など）を備えています。
- モジュールのユニットテストを作成する際は、OpenAI 呼び出しや外部 API をモックするように設計されています（内部で _call_openai_api を patch 可能）。

---

もし README に含めたい追加事項（例: CI/CD のセットアップ、詳細な環境変数一覧サンプル、データベーススキーマ／ER 図、運用手順書など）があれば教えてください。必要に応じて追記・整形します。