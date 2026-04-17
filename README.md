# KabuSys

日本株向けの自動売買（Execution）・監視（Monitoring）・リサーチ・AI 補助ツール群を含むパッケージです。  
このリポジトリは戦略用のファクター計算・ポートフォリオ構築ロジック、発注の実行管理、監視/アラート、Paper Trading 用の検証ツール、OpenAI を用いるニュース NLP / レジーム検出などを含みます。

---

## 主要な特徴（機能一覧）

- Execution（発注エンジン）
  - ブローカークライアントの抽象化（実口座 / Paper Trading の分離）
  - OrderManager / ExecutionEngine による発注フロー管理、リスク制御
  - 再起動時の Reconciler による状態同期（自動復旧）

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス健全性 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込みと LINE 通知
  - Monitoring DB（SQLite）への永続化 + Streamlit ダッシュボード

- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ

- Portfolio（ポートフォリオ構築）
  - 候補選定、ウエイト計算（等分/スコア加重）、セクター制約適用、株数算出（単元丸め・リスクベース）

- AI（OpenAI を利用した機能）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に格納
  - regime_detector: マクロ記事 + ETF MA200 を統合して市場レジーム判定
  - エクスポネンシャルバックオフやレスポンス検証等の堅牢化実装あり

- ツール
  - Paper Trading の検証レポート生成（期間指定可）
  - Streamlit ベースの監視ダッシュボード

---

## 必要条件（推奨）

- Python 3.9+
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- OS: Linux / macOS / Windows（process priority はプラットフォームによる互換性あり）

（requirements.txt がある場合はそれを使用してください）
例:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
なければ以下を個別にインストールしてください:
```
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存関係をインストール（上記参照）

3. data ディレクトリの作成（プロセス PID ファイルや DB を保管）
   ```
   mkdir -p data
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（デフォルト）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
     - JQUANTS_REFRESH_TOKEN: （必須）J-Quants 用トークン
     - KABU_API_PASSWORD: （必須）kabu API パスワード
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH, etc.

5. DB 初期化
   - 監視・Execution 起動時に必要なテーブルは自動で作成されます（init_monitoring_db が呼ばれます）。
   - DuckDB（prices_daily 等のデータ）については適切にテーブルを用意してください（リサーチ機能が参照します）。

---

## 使い方（主要な実行例）

パッケージはモジュール単位で起動できます。プロジェクトルートから実行してください。

- 監視ループを起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存せず）。停止は data/stop_requested.flag を生成することでループが検出して終了します。

- ExecutionEngine（発注エンジン）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
  - 起動時、data/stop_requested.flag が既に存在すると起動せず終了します。停止は同フラグの書き込みまたは kill.flag による停止等で制御します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。オプション `--db PATH` で指定可能。

- Streamlit 監視ダッシュボード（ブラウザで見る）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only モードで SQLite を開きます。MonitoringEngine がデータを書き込んでいることが前提です。

- AI 機能（news_nlp / regime_detector）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数）。
  - 大量コールではレート制限がかかり得ます。実装側でリトライ・バックオフが組み込まれています。

---

## 停止 / フラグ操作

- global 停止フラグ（両スクリプトで使用）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution は停止検出して終了します。

- ExecutionEngine 停止（KillSwitch）
  - KillSwitch は条件を満たすと data/kill.flag を作成します。Execution の起動時に kill.flag をクリアする挙動は Settings.kill_flag_clear_on_start によって制御されます（環境変数 KILL_FLAG_CLEAR_ON_START=1 等）。
  - 手動で kill.flag を削除する場合:
    ```
    rm data/kill.flag
    ```

- PID ファイル
  - ExecutionEngine は data/execution.pid に PID を書きます。SystemMonitor はこの PID の存在/有効性からプロセス健全性を評価します。

---

## 環境変数（代表的な一覧）

- KABUSYS_ENV: execution の実行環境（development | paper_trading | live）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite path（default: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB path（default: data/kabusys.duckdb）
- PID_FILE_PATH: Execution PID file path（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag path（default: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

細かいプロパティは `kabusys.config.Settings` を参照してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env の自動読み込みロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（発注関連の実装）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - data/ (実行時に作られる想定)
    - monitoring.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - paper_trading.db (Paper Trading SQLite)
    - execution.pid, kill.flag, stop_requested.flag

（上記は概要です。細かいモジュールはソースツリーを参照してください）

---

## 実装上の留意点 / 運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CI やテストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の DB テーブルは起動時に冪等で作成・マイグレーションされます（init_monitoring_db）。
- Paper Trading は本番 DB と明確に分離されるよう設計されています（環境変数で PATH を切り替え）。
- OpenAI を使う機能は API 呼び出しの失敗に対してバックオフやフォールバック（スコア 0.0）を行い、致命的失敗にならないよう配慮されていますが、API キーの管理・料金・レート制限には注意してください。
- process priority / cpu affinity 設定はプラットフォーム依存です。権限不足などで設定できない場合は警告が出てスキップされます。

---

## 開発・貢献

- コードのスタイルやテストは各モジュールに合わせて追加してください。  
- テスト時は環境依存を排するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を推奨します。  
- OpenAI への実コールを避けるためテストでは _call_openai_api 等をモックしてください（モジュール内に差し替えポイントがあります）。

---

この README はコードベースの主要な使い方・構成をまとめたものです。詳細は各モジュールの docstring / ソースを参照してください。追加でサンプルの .env.example、requirements.txt、デプロイ手順などを作成することを推奨します。