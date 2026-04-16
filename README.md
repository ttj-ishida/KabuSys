# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行スクリプト群）。  
このリポジトリはトレード実行、監視、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント／レジーム判定）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群から構成されています。

- 実行エンジン（ExecutionEngine）: ブローカーと連携して発注・状態管理を行う。
- 監視（Monitoring）: システム状態、注文滞留、ドローダウン等を定期的にチェックしログ化／アラート送出／キルスイッチ制御を行う。
- ポートフォリオ構築: シグナルから候補選定、重み付け、ポジションサイズ決定を行う純粋関数群。
- リサーチ: DuckDB を用いたファクター計算・特徴量解析ツール。
- AI モジュール: OpenAI を使ったニュースセンチメントスコアリング、マクロセンチメントを統合した市場レジーム判定。
- 各種ツール: Paper Trading 検証レポート、Streamlit ダッシュボード等。

設計上の特徴:
- DB は SQLite（監視用）/ DuckDB（時系列データ・リサーチ）を利用。
- Paper Trading 実行時は本番 DB と分離（専用 SQLite を使用）。
- 環境変数は .env / .env.local から自動読み込み（必要に応じて無効化可）。

---

## 主な機能一覧

- 実行関連
  - 発注の作成・同期・再照合（Reconciler）機能
  - リスク管理（RiskManager）および OrderManager による状態遷移制御
  - ExecutionEngine の起動スクリプト（run_execution）

- 監視関連
  - SystemMonitor: CPU/メモリ/Disk、プロセス状態、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み、LINE へのプッシュ通知
  - MonitoringEngine と run_monitoring スクリプト

- ポートフォリオ構築
  - 候補選定、等配分・スコア加重、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元株丸め・集約キャップ）

- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計要約

- AI（OpenAI）
  - ニュースのセンチメント化（gpt-4o-mini を想定）および ai_scores テーブルへの書き込み
  - マクロニュースと ma200 乖離を組み合わせた市場レジーム判定（score_regime）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard.py）

---

## 必要条件（概略）

- Python 3.9+
- SQLite（組み込み）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit

インストール例:
```bash
pip install duckdb psutil openai requests streamlit
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt   # もし用意されていれば
   # または個別インストール
   pip install duckdb psutil openai requests streamlit
   ```
4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 自動ロードはデフォルトで有効：OS環境変数 > .env.local > .env の順で読み込まれます。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - PAPER_FILL_MODE（paper_trading 時のモック約定挙動: instant | partial | never | reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（monitoring 用 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB パス、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト: 60）

5. データディレクトリ
   - デフォルトで `data/` を使用します。PID ファイルやフラグファイルもここに置かれます。
   - 例: `data/execution.pid`, `data/kill.flag`, `data/stop_requested.flag`

---

## 使い方

主要な起動やツールの実行例を示します。

- 監視ループ起動（ポーリング）
  ```bash
  # 環境変数 MONITOR_POLL_INTERVAL による間隔変更可（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 実行中、data/stop_requested.flag が作成されると安全にループ終了します。
  - 監視はどの KABUSYS_ENV でも本番 sqlite_path を参照して監視 DB を初期化します。

- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
  - 起動前に `data/kill.flag` が存在するとエンジンは起動しません。
  - 実行中に `data/stop_requested.flag` が作成されるとエンジンは停止を試みます。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（プログラムから）
  - ニューススコア算出:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 4, 10), api_key="YOUR_OPENAI_KEY")
    ```

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を有効にする）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings クラス参照）

Settings の自動ロード:
- .env と .env.local をプロジェクトルートから読み込みます（OS 環境変数は上書きされません）。
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止・制御の仕組み

- モニタリング / 実行スクリプトはプロジェクト直下の `data/stop_requested.flag` を参照します。これが存在するとポーリング・スレッドは安全に終了します。
- 実行停止（強制停止）は `KillSwitch` が `data/kill.flag` を書き込み、ExecutionEngine が起動時にこれを検知して起動を抑制あるいは実行中に停止します。
- 実行エンジンは PID ファイル（デフォルト `data/execution.pid`）を書き、SystemMonitor はその PID の生存チェックを行います。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュールです（部分抜粋）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
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
    - order_repository.py (等、発注関連)
    - execution_engine.py (エンジン本体)
    - broker_factory.py
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
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - data/                           — 実行時に使用される DB / flag / pid 等（リポジトリでは未追跡かも）

（実際のファイル一覧はリポジトリを参照してください）

---

## 開発上の注意点 / 設計上のポイント

- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成・カラム追加を行います。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 呼び出しはリトライ・バックオフやレスポンス検証を入れてあり、失敗時は安全側（スコア 0.0）で継続します。
- 外部プロセス優先度設定（set_process_priority）を起動時に呼び出しています。権限不足で失敗する可能性があるため警告を出してスキップします。
- .env のパースはシェル風クォートやコメントをかなり厳密に処理します。フォーマットに従って設定してください。

---

## 既知の制限・TODO（抜粋）

- 単元株（lot）や銘柄ごとの手数料マップは将来的に拡張予定。
- position sizing の一部価格欠損時のフォールバックロジックは改良余地あり。
- OpenAI SDK の将来的な仕様変更に対してはエラーハンドリングを維持する必要あり。

---

## サポート / 貢献

- バグ報告やプルリク歓迎です。まず Issue を立ててください。
- 大きな設計変更やデータベーススキーマの変更は事前に議論をお願いします。

---

README の内容はコードベースの主要部分に基づいてまとめています。実行やデプロイ時は必ず .env（または環境変数）で必要なキーやパスが設定されていることを確認してください。