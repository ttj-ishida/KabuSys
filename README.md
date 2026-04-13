# KabuSys

日本株自動売買システムのサンプル実装（KabuSys）。  
このリポジトリは、シグナル → ポートフォリオ構築 → 発注 → 監視／アラートまでを含む一連のコンポーネント群を含みます。Production / Paper Trading / Development といった複数環境に対応し、モジュール化された純粋関数群や永続化層（SQLite / DuckDB）を備えています。

## 概要
- DuckDB を用いたファクター計算・リサーチ機能
- 発注ロジック（ExecutionEngine）とブローカー抽象化（実ブローカー / Mock）
- 監視サブシステム（System / Trade / Risk）と LINE によるアラート送信
- Paper Trading 用の分離された SQLite DB と検証レポート生成ツール
- ニュースを LLM（OpenAI）でスコアリングし AI スコアを DuckDB に保存するモジュール
- プロセス優先度や CPU affinity 設定ユーティリティ

## 主な機能一覧
- Execution
  - ブローカークライアント（本番 / モック）を切り替え可能
  - 注文状態管理（OrderManager, OrderRepository）
  - 起動時リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン／ポジション上限監視と kill.flag の生成
  - AlertManager: LINE Push でアラート送信（クールダウン付き）
  - Streamlit ダッシュボードで可視化
- Portfolio
  - 候補選定、重み計算、ポジションサイズ算出、セクターキャップ適用
- Research / AI
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン / IC / 統計サマリー
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング
  - regime_detector: マクロ＋ETF MA を用いた市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## 動作要件（想定）
- Python 3.9+
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで利用）

※ 実際の requirements.txt / pyproject.toml に従ってインストールしてください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```
2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```
3. 依存パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそれに従ってください。例:
     ```
     pip install -r requirements.txt
     ```
     または最低限:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
4. 環境変数設定（.env をプロジェクトルートに配置）
   - 自動ロード機能が有効（デフォルト）なら .env / .env.local をプロジェクトルートに置くだけで読み込まれます。
   - 主要な環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=... (通知を有効にする場合)
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60（秒／監視ループ）
   - .env の書式は shell 形式（export 対応、コメント行可）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

## 実行方法（主要コマンド）
- ExecutionEngine（本番／paper_trading 切替は KABUSYS_ENV で制御）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。

- Monitoring（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に関わらず）。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を read-only で開きます。MonitoringEngine を先に起動してデータがあることを確認してください。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。--db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。

- AI/Regime スコアリング（プログラムから呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーを引数または環境変数 OPENAI_API_KEY で供給する必要があります。

## 設定（Settings の主要項目）
Settings クラス（kabusys.config.Settings）で管理。主なプロパティ：
- jquants_refresh_token（必須）
- kabu_api_password（必須）
- kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id（通知用）
- duckdb_path（デフォルト data/kabusys.duckdb）
- sqlite_path（デフォルト data/monitoring.db）
- paper_sqlite_path（デフォルト data/paper_trading.db）
- paper_fill_mode（instant|partial|never|reject、デフォルト instant）
- pid_file_path / kill_flag_path（デフォルト data/*.pid, data/kill.flag）
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- KABUSYS_ENV: development | paper_trading | live（必須値チェックあり）

.env.example を参考に必要な値を用意してください。

## 注意点 / 運用メモ
- Paper Trading は本番 DB と分離されます（paper_sqlite_path を使用）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します（監視は本番対象を想定）。
- ExecutionEngine 起動時は PID ファイルを生成し、SystemMonitor は PID ファイルの存在と process の存否をチェックします。stale PID が検出されると削除されリスクログが残ります。
- KillSwitch はリスク基準（ドローダウン・ポジション上限）で kill.flag を書き込み、ExecutionEngine 側が停止を確認する仕組みになっています。flag は冪等的に書き込まれます。
- Process 優先度変更や CPU affinity 設定は psutil で行います。権限不足で失敗する場合はログに警告が出てスキップされます。
- OpenAI API 呼び出しはリトライロジックを実装（RateLimit / Network / 5xx に対する指数バックオフ）しています。API キーが無いと呼び出しはエラーになります。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/.env ロードと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込む
    - regime_detector.py — マクロ + ETF MA を合成して市場レジーム判定
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - execution/
    - order_manager.py — Order 管理 API
    - reconciler.py — 再起動時のリコンシリエーション
    - （その他ブローカー・エンジン実装がここに含まれます）
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化とラッパー（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成/消去
    - alert_manager.py — LINE API 送信ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (推奨配置、実行時に生成)
    - kabusys.duckdb (DuckDB)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)

## 開発者向け
- モジュール単位でユニットテストを書くことで、ファイナンシャルロジック（純粋関数群）を容易に検証できます。research / portfolio / position_sizing 等は外部依存が少なくユニットテストに適しています。
- OpenAI 呼び出しはテストでモック化しやすいように内部呼び出し関数を分離しています（_call_openai_api を patch する等）。
- SQLite / DuckDB の接続を渡す設計なのでインメモリ DB を使った単体テストが可能です。

## ライセンス／著作権
- このリポジトリはサンプル実装です。実運用する場合は自己責任で十分な検証とリスク管理を行ってください。

---

不明点や README に追加したい実行例（systemd ユニット、Dockerfile、CI 設定など）があれば教えてください。必要に応じて追記します。