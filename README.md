# KabuSys

KabuSys は日本株向け自動売買および監視・研究ツール群をまとめた小規模なプロジェクトです。  
本リポジトリには、取引実行（ExecutionEngine）、監視（MonitoringEngine）、ファクター計算・研究、ニュース NLP（OpenAI を利用したセンチメントスコアリング）、Paper Trading 用ユーティリティなどが含まれます。

---

## プロジェクト概要

主な目的は「自動売買の実行と運用監視、研究のためのユーティリティ提供」です。  
設計方針の抜粋：

- Execution と Monitoring は sqlite / DuckDB を使って永続化（本番 DB と Paper Trading は分離可能）。
- AI（ニュース評価やレジーム判定）は OpenAI API（gpt-4o-mini）を利用する設計。API 呼び出しは失敗に対してフォールバックを備える（フェイルセーフ）。
- 多くのモジュールは副作用を抑え、純粋関数や明示的な DB 接続を受け取る形で実装。
- 環境変数 / .env による設定読み込みをサポート（自動ロード機能あり）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの切替（実口座 / Paper Trading）
  - OrderManager / Reconciler による注文管理と起動時リコンシリエーション
  - RiskManager によるリスク制御（設定に基づく制限）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在・データ鮮度を監視
  - TradeMonitor: 注文滞留（stale order）・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch: 条件成立時に flag ファイルを書き ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）
  - ポートフォリオ構築補助（候補選定、等分配/スコア重み、リスク調整、ポジションサイズ計算）

- AI
  - news_nlp: ニュース記事の銘柄別センチメントスコアを生成して ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースセンチメントを合成して日次の市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

1. Python 環境の準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   プロジェクトに requirements.txt がない場合、少なくとも以下をインストールしてください。
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   （環境に応じて追加依存が必要になる場合があります）

3. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主な環境変数:

   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager 用)
   - OPENAI_API_KEY (AI 機能で必要)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (Paper Trading 用 DB、デフォルト: data/paper_trading.db)
   - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視しきい値）
   - LOG_LEVEL（DEBUG/INFO/...）

4. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要スクリプト）

- 監視ループを起動（SystemMonitor を単独で稼働）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に設定可能（デフォルト 60）
  ```
  python -m kabusys.run_monitoring
  ```
  実行時にプロセス優先度が "high" に設定されます（set_process_priority を使用）。

- ExecutionEngine（取引実行）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に分離して記録します。
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション `--db PATH` で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  （監視 DB は読み取り専用で開かれます。MonitoringEngine を先に起動してください）

- AI 関連
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数 or 引数で提供）。
  - ニュースセンチメント（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は Python API として呼び出せます。例:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```

---

## 監視 / 停止フロー（要点）

- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、条件に応じて KillSwitch により kill.flag を書きます。ExecutionEngine 起動時に kill.flag を検知して安全停止する設計です。
- ExecutionEngine は起動時に PID ファイル（Settings.pid_file_path）を書きます。SystemMonitor はこの PID ファイルの有無とプロセス存在をチェックします（stale PID を検出した場合に削除・ログを残す）。
- AlertManager は LINE の Push API を使って通知します。token / user_id が未設定の場合は送信をスキップします。クールダウン管理あり。

---

## 設計上の注意点 / 動作に関する補足

- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して `.env` / `.env.local` を自動で読み込みします。OS 環境変数は保護され上書きされません。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは broker がモックになり、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離するようになっています。
- OpenAI 呼び出し:
  - rate-limit / network error / 5xx などに対して指数バックオフでリトライする実装を行っていますが、API キー未設定時は明示的なエラー（ValueError）を投げます。
- DuckDB / SQLite:
  - ファクター計算・研究機能は DuckDB のテーブル（prices_daily, raw_financials 等）を前提としています。
  - 監視ログは SQLite（monitoring.db）へ永続化されます。`monitoring_db.init_monitoring_db()` はテーブル作成や簡単なマイグレーションを行います（冪等）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / 設定読み込みロジック（Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）処理
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — monitoring DB（SQLite）層 + MonitoringDB クラス
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - reconciler.py — 起動時リコンシリエーション
    - order_manager.py — 注文の作成/送信/同期など
    - （その他 execution 関連コンポーネントが存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン / IC / summary 等
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （デフォルトの DB 保存先／作成を想定）
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

（上記はリポジトリ内にある主要ファイルの抜粋です。細かい実装は各ファイルの docstring を参照してください）

---

## よくある利用例（簡単なフロー）

1. 環境変数・.env を設定（OpenAI キー・ブローカー設定など）
2. DuckDB に価格データ・財務データを投入（research 用）
3. MonitoringEngine を起動して運用監視を行う
   ```
   python -m kabusys.run_monitoring
   ```
4. ExecutionEngine を起動して取引を行う（paper_trading モードでテスト）
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
5. 運用後、Paper Trading の検証レポートを出す
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
6. Streamlit で監視ダッシュボードを開く
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

---

## 補足 / 貢献

- 各モジュールには docstring が豊富に付与されています。実装の意図や注意点はソース内コメントを参照してください。
- バグ修正や機能拡張、テスト追加は歓迎します。README にない実行時の詳細や追加依存は PR / Issue で共有してください。

---

この README はコードベースの主要点をまとめたものです。詳細な API や内部の振る舞いについてはソースコードの docstring とコメントを参照してください。