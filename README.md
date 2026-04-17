# KabuSys

軽量な日本株自動売買システム（ライブラリ＋実行スクリプト群）のリポジトリ。  
バックテスト・リサーチ用の DuckDB 集計、実際の発注を担う ExecutionEngine、監視コンポーネント、LLM を使ったニュースセンチメント/レジーム判定などを含みます。

---

## 概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- Execution: ブローカーとの発注・注文状態管理・再同期（Reconciler）
- Monitoring: システム状態・注文滞留・リスク監視と通知（LINE）・監視DB（SQLite）
- Portfolio: 銘柄選定、重み計算、ポジションサイジング、セクター調整
- Research: DuckDB を使ったファクター計算・特徴量解析ツール
- AI: OpenAI を利用したニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- Tools: 検証レポート生成や Streamlit によるダッシュボード

設計方針の一部:
- DuckDB/SQLite をローカル DB として利用（価格・ファイナンスデータ、監視ログ、paper trading 用 DB）
- 環境変数（.env / .env.local）からの設定読み込み（自動ロード）
- paper_trading 環境では発注をモックし、本番 DB と分離

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker（paper DB に記録）
  - PID ファイル管理・停止フラグ検出
  - リスク管理・オーダー管理と Reconciler による復旧

- Monitoring（run_monitoring.py / MonitoringEngine）
  - CPU/メモリ/ディスクの監視、データ鮮度チェック、プロセス死活監視
  - trade_logs / risk_logs / dashboard などの永続化（SQLite）
  - KillSwitch による停止フラグ作成
  - AlertManager による LINE 通知（クールダウン付き）

- AI モジュール
  - news_nlp.score_news: raw_news を LLM に送って銘柄ごとにスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: MA200 乖離＋マクロニュースの LLM センチメントで市場レジーム判定

- Research
  - calc_momentum / calc_value / calc_volatility 等のファクター計算（DuckDB 接続で SQL 実行）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）など

- Tools
  - paper_verification_report: Paper Trading の検証レポート出力
  - streamlit_dashboard: 監視ダッシュボード（Streamlit）

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt がない場合の例）
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   注: sqlite3 は標準ライブラリに含まれます。

4. データディレクトリを作成
   ```
   mkdir -p data
   ```

5. 環境変数を設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   例 (.env):
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し paper_sqlite_path に書き込む
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- OPENAI_API_KEY: OpenAI 呼出し用（AI モジュールで利用）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60 秒）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用（未設定なら送信をスキップ）

---

## 使い方（起動・操作手順）

- 監視ループ起動（Monitoring）
  - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - stop 用フラグ: `data/stop_requested.flag` が存在すると監視ループは終了します（スクリプト内で参照）。

- 実行エンジン起動（ExecutionEngine）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - `KABUSYS_ENV=paper_trading` を指定すると MockBroker を使用し `data/paper_trading.db` へ書き込みます。
  - ExecutionEngine は `data/execution.pid` を作成し、停止は `data/stop_requested.flag` の作成で行えます。KillSwitch は `data/kill.flag` を生成して停止指示を送ります。

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション `--db` で DB パスを指定可能（デフォルト: data/paper_trading.db）。

- AI 関連（プログラム的呼出し）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（kabusys.data で作る接続）を引数に受けます。API キーが必要です。

---

## 重要なファイル・フラグ

- data/stop_requested.flag: run_execution/run_monitoring が監視している停止フラグ（存在すると停止/起動回避）
- data/kill.flag: KillSwitch が書き込む停止指示（ExecutionEngine に送る）
- data/execution.pid: ExecutionEngine の PID（SystemMonitor がプロセス死活を検知）
- DB:
  - data/monitoring.db: 監視ログ（MonitoringDB）
  - data/paper_trading.db: Paper Trading（分離された SQLite）
  - data/kabusys.duckdb: DuckDB（価格・財務・raw_news 等の分析用）

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み / Settings
  - run_monitoring.py              — SystemMonitor ポーリングループ起動
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ / MonitoringDB クラス
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常の監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag 書込ユーティリティ
    - alert_manager.py             — LINE 通知
    - monitoring_engine.py         — 各モニタの orchestration
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...                          — ブローカーファクトリ、engine など（発注関連）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み付け
    - position_sizing.py           — 株数決定・スケール調整
    - risk_adjustment.py           — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py           — momentum/value/volatility 計算
    - feature_exploration.py       — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/                          — （実行時に使用する DB・フラグ等を置く想定）
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意

- paper_trading 環境は本番 DB と完全分離されます。安全にローカル検証できます。
- OpenAI 呼び出しには API キーが必要です。失敗時はフェイルセーフ（0 やスキップ）して動作を継続する設計になっていますが、API キーの設定漏れは確認してください。
- プロセス優先度設定や CPU affinity は権限により失敗する場合があります（ログに警告が残ります）。
- monitoring_db のスキーマは init_monitoring_db() で冪等に構築・マイグレーションされます。既存 DB に対するカラム追加等の処理も組み込まれています。
- データ鮮度チェックや PID ファイル検出は time zone / UTC を意識した実装になっています。config.Settings で KABUSYS_ENV を適切に設定してください。

---

必要であれば、README に追記する内容（サンプル .env、デプロイ手順、systemd 管理スクリプトの例、ユニットテスト実行方法など）を教えてください。