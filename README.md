# KabuSys

日本株向けの自動売買 / 研究 / 監視フレームワーク（内部利用向けプロトタイプ）

このリポジトリは、戦略・ポートフォリオ構築、注文実行、監視、研究、AI によるニュース解析などを含むモジュール群で構成されたシステムです。各モジュールはできるだけ副作用を抑え、SQLite / DuckDB を用いたローカル永続化を行います。

注意: この README はソースコード（src/kabusys 以下）に基づいて作成しています。実運用を行う場合は必ずコードレビューと適切なテストを行ってください。

---

## 概要

- 戦略・ポートフォリオ構築（portfolio/*）
  - シグナルから候補選定、重み付け、ポジションサイズ決定、セクター制約などの純粋関数群を提供。
- 注文実行（execution/*）
  - ブローカークライアントと連携して発注管理、注文履歴、リコンシリエーションを行う。
  - `run_execution.py` が Engine を起動するエントリポイント。
- 監視（monitoring/*）
  - システム状態、注文滞留、リスク（ドローダウン / 保有上限）を定期的にチェック。
  - 監視ログは SQLite に永続化され、Streamlit ダッシュボードで可視化可能。
  - `run_monitoring.py` が監視ポーリングのエントリポイント。
- 研究（research/*）
  - DuckDB 上の時系列データからファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）。
- AI（ai/*）
  - OpenAI を用いたニュースのセンチメント評価や市場レジーム判定を実装（gpt-4o-mini 等を想定）。
- ユーティリティ（utils/*）
  - プロセス優先度設定や共通ユーティリティ。
- ツール（tools/*）
  - Paper Trading 検証レポートの生成スクリプト等。

---

## 主な機能一覧

- ExecutionEngine（注文作成・送信・状態管理、リスク管理）
- Reconciler（再起動時の注文・ポジション突合）
- RiskManager / RiskMonitor（ポジション上限・ドローダウン監視）
- MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor の統合）
- Monitoring DB（SQLite）: テーブル system_status, trade_logs, positions, risk_logs, dashboard を管理・マイグレーション対応
- Streamlit ダッシュボードで監視データの可視化
- Paper Trading モード（本番DBと分離される専用SQLiteを使用）
- AI ベースのニュースセンチメント（ai.news_nlp.score_news）
- 市場レジーム判定（ai.regime_detector.score_regime）
- 研究用ファクター計算（research.calc_* 系）

---

## 必要条件 / インストール

- Python 3.10+
- 主な依存パッケージ（一例）:
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai

例（pip）:
```bash
python -m pip install duckdb psutil requests streamlit openai
```

リポジトリに requirements.txt がある場合はそれを使用してください:
```bash
pip install -r requirements.txt
```

---

## 環境設定 (.env)

- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主な環境変数（抜粋）:
- KABUSYS_ENV: 起動環境（`development` / `paper_trading` / `live`）※デフォルト `development`
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- PAPER_FILL_MODE: Paper Trading の約定モード（`instant`|`partial`|`never`|`reject`、デフォルト `instant`）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
- DUCKDB_PATH: DuckDB ファイル（デフォルト `data/kabusys.duckdb`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行管理用ファイルパス

.env の書式はシェルの export を含む形やクォートを含む行に対応しています。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして Python 環境を用意:
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # または必要パッケージ個別インストール
   ```

2. `.env` を作成（`.env.example` を参考に必要なシークレットを設定）:
   - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY（必要な場合）など

3. データディレクトリ作成:
   ```bash
   mkdir -p data
   ```

4. DuckDB / SQLite の初期化は多くのモジュールで自動実行されます（必要テーブルがなければ作成されます）。

---

## 使い方（実行例）

実行ファイルはパッケージのモジュールとして起動できます。開発中は `src` を PYTHONPATH に含めるか、パッケージとしてインストールして実行してください。

- 監視ループ起動（Monitoring）
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可。
  - 実行例（パッケージ化済み / インストール済みの場合）:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - リポジトリ直下で `src` を PYTHONPATH にする場合:
    ```bash
    PYTHONPATH=src python src/kabusys/run_monitoring.py
    ```
  - 停止: `Ctrl+C` またはプロジェクトルートの `data/stop_requested.flag` を作成するとループは安全に終了します。

- ExecutionEngine 起動（注文エンジン）
  - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、記録は paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に行われます（本番 DB と分離）。
  - 実行例:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止: `data/stop_requested.flag` を作成すると Engine に停止シグナルが送られます（または PID ファイルを参照）。

- Streamlit 監視ダッシュボード
  - 起動コマンド:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB を読み取り専用で開くため、MonitoringEngine を先に起動しておくことを推奨します。

- Paper Trading 検証レポート生成
  - usage:
    ```bash
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB は `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定（デフォルト `data/paper_trading.db`）。

- AI モジュール（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または関数引数で指定）。
  - 例（スクリプトから呼び出す）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date.today(), api_key="sk-...")
    ```

---

## 監視 / 制御ファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視している停止フラグ。存在すると安全に停止します。
- data/kill.flag
  - KillSwitch により書き込まれる停止フラグ（主に監視から Execution 停止を促すため）。
- data/execution.pid（デフォルト）
  - ExecutionEngine が PID を書き込むファイル。SystemMonitor は PID を監視してプロセス死活を判定します。

KillSwitch は RiskMonitor 等の結果に基づき `kill.flag` を書き込み、ExecutionEngine の停止をトリガーします。KillSwitch を手動で解除するには `kill.flag` を削除してください（KillSwitch.clear() が提供されています）。

---

## DB スキーマ（監視用主要テーブル）

監視用 SQLite（デフォルト: data/monitoring.db）には init_monitoring_db により以下のテーブルが作成されます（冪等）:

- system_status: CPU/Memory/Disk/プロセス状態 等
- trade_logs: 発注ログ（logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 現在の保有（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベント（DRAWDOWN_ALERT 等）
- dashboard: 集約値（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

必要に応じてマイグレーション（カラム追加）処理が init_monitoring_db 内で行われます。

---

## ディレクトリ構成（src/kabusys 以下の主要ファイル）

概略ツリー:
```
src/kabusys/
├─ __init__.py
├─ config.py                      # 環境変数読み込みと Settings
├─ run_monitoring.py              # Monitoring ポーリングループ起動スクリプト
├─ run_execution.py               # ExecutionEngine 起動スクリプト
├─ utils/
│  ├─ __init__.py
│  └─ process_priority.py         # プロセス優先度・CPU affinity ユーティリティ
├─ monitoring/
│  ├─ __init__.py
│  ├─ monitoring_db.py            # SQLite 永続化層
│  ├─ monitoring_engine.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  ├─ alert_manager.py
│  └─ streamlit_dashboard.py
├─ execution/
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ execution_engine.py
│  ├─ broker_factory.py
│  ├─ reconciler.py
│  └─ ...（他の実装ファイル）
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ tools/
│  ├─ __init__.py
│  └─ paper_verification_report.py
└─ data/                          # 実行時に使用する SQLite/DuckDB/flag/pid 等（.gitignore 推奨）
```

---

## 運用上の注意 / ベストプラクティス

- 本番（live）起動時は `KABUSYS_ENV=live` を設定し、設定や DB の参照先に注意してください。
- Paper Trading: `KABUSYS_ENV=paper_trading` を使用すると Execution は MockBroker を選び paper 専用 DB に書き込みます（本番 DB と分離）。
- OpenAI の呼び出しは外部 API を伴うためレート制限・エラー対策（バックオフ、最大トライ回数）を行っています。API キー管理に注意してください。
- `.env` ファイルにシークレットを平文で置くのは安全性の観点から慎重に。環境固有の機密情報は適切に保護してください。
- 監視データ（SQLite / DuckDB）は定期的なバックアップやサイズ管理を検討してください。

---

## 参考 / 開発時のヒント

- Settings クラス（config.py）を介して環境変数を取得します。必須キーが未設定の場合は ValueError を投げます。
- 多くの機能は外部 DB（DuckDB / SQLite）に依存します。研究ワークフローのテスト時は DuckDB にテスト用テーブルを用意してください。
- 各モジュールは可能な限り純粋関数や副作用を限定した設計（例: portfolio の関数群、research の計算関数）になっています。単体テストが書きやすい構成です。

---

もし README に追記してほしい内容（例: 実運用チェックリスト、詳細な環境変数一覧、API の仕様サマリ、デプロイ手順など）があれば教えてください。必要に応じてサンプル .env.example も作成できます。