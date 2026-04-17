# KabuSys

KabuSys は日本株自動売買・リサーチ・監視を目的とした小規模なシステムです。本リポジトリは戦略構築（ファクター計算・特徴量探索）、ポートフォリオ構築、実行エンジン、監視機能、AI を利用したニュース評価等のコンポーネントを含みます。

---

## 概要

- 設計方針：
  - DuckDB / SQLite を用いたローカルデータ処理（prices_daily / raw_financials / raw_news 等）。
  - ExecutionEngine はブローカー API（本番）またはモック（Paper Trading）を切り替え可能。
  - 監視は別プロセスで行い、異常検知時に flag ファイルを書き込んで実行エンジンを安全に停止させる。
  - LLM（OpenAI）を使ったニュースセンチメント評価（AI モジュール）はフェイルセーフ設計：API 失敗時はスコアゼロなどで継続。
  - 自動的に .env ファイルを読み込む仕組み（プロジェクトルートを検出）を持つが、無効化も可能。

---

## 機能一覧

- Execution
  - 実行エンジン起動スクリプト（run_execution.py）
  - ブローカー抽象化（本番 / Mock 切替）
  - リコンシリエーション（起動時の注文同期とポジション照合）
  - リスクマネジメント（最大ポジション比率、利用率、ドローダウン等）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格の異常検知
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 異常時に data/kill.flag を書き込むことで ExecutionEngine を停止
  - AlertManager: LINE によるプッシュ通知（オプション）
  - Streamlit ベースの監視ダッシュボード

- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、特徴量統計
  - 候補選定、等重／スコア重み、セクター制限、ポジションサイズ決定ロジック

- AI
  - news_nlp: raw_news を LLM でセンチメント評価 → ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## 必要要件

以下は主要な Python パッケージの例です（プロジェクトに requirements.txt がある場合はそちらを使用してください）。

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai (AI モジュール利用時)
- その他（標準ライブラリ）

インストール例:
```
pip install duckdb psutil requests streamlit openai
```

---

## セットアップ手順

1. リポジトリをクローンしワークディレクトリへ移動
2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール（上記参照）
4. .env の準備
   - プロジェクトルートに `.env.example` を用意している場合はそれを参考に `.env` を作成してください。
   - 自動ロード: デフォルトでプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. 必須環境変数（利用する機能に応じて設定）
   - JQUANTS_REFRESH_TOKEN（J-Quants API を使う場合）
   - KABU_API_PASSWORD（kabu API）
   - OPENAI_API_KEY（AI モジュール利用時）
   - その他：KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など（下の設定参照）

6. data ディレクトリ作成（PID / flag / DB のデフォルト場所）
   ```
   mkdir -p data
   ```

---

## 環境変数（主要）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants 使用時）
- KABU_API_PASSWORD: 必須（kabu API 使用時）
- OPENAI_API_KEY: LLM 利用時に必須（news_nlp, regime_detector）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: Monitoring DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル / kill.flag のパス（デフォルト data 内）

注意: Settings クラス内で未設定の必須項目は例外になります。

---

## 使い方（代表的なコマンド）

- 監視プロセス起動（SystemMonitor をループで実行）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path を使用（環境に関係なく monitoring DB は本番パス）

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と分離されます。
  - 実行時に data/execution.pid が作成され、監視側はこれを参照してプロセス生存をチェックします。
  - 停止させるには data/stop_requested.flag（あるいは kill.flag 経由）を作ることで安全停止します。

- Streamlit ダッシュボード起動（監視 DB を read-only で開く）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # or with date range
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング（プログラム的呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、target_date のニュースウィンドウを評価して ai_scores テーブルへ書き込みます。
    - OPENAI_API_KEY が必要（引数で明示的に渡すことも可）。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 実行時の挙動・運用留意点

- プロセス優先度:
  - run_monitoring / run_execution 起動時に set_process_priority("high") が呼ばれ、可能ならプロセス優先度を上げます（psutil 経由）。権限不足や未対応 OS の場合は警告を出してスキップします。

- ファイルフラグ:
  - data/stop_requested.flag: 複数スクリプトで停止検知に使われています（run_monitoring, run_execution）。
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine 停止を指示します（監視→実行の安全停止シグナル）。

- DB 初期化:
  - init_monitoring_db(conn) は冪等で monitoring 用テーブルを作成し、既存 DB の簡易マイグレーション（カラム追加）を行います。起動時に呼ばれるため手動での初期化は不要です。

- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると paper_sqlite_path に記録され、実際の本番 sqlite_path とは分離されます（安全のため）。

- API 呼び出し:
  - OpenAI 呼び出しはリトライ・バックオフやレスポンス検証を実装していますが、API キー管理や料金に関する注意は運用者側で行ってください。

---

## ディレクトリ構成（抜粋・説明）

- src/kabusys/
  - __init__.py — パッケージエクスポート（version 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替有）
  - data/ (リポジトリルートに想定)
    - monitoring.db, paper_trading.db, kabusys.duckdb, *.pid, *.flag などを配置
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ層（init + MonitoringDB API）
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ実装
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - alert_manager.py — LINE 通知
    - kill_switch.py — flag 書き込みロジック
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory など（発注・同期・リスク管理等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - position_sizing.py — 株数計算・上限・丸め
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB 利用）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — raw_news の LLM によるスコアリングと ai_scores への書込み
    - regime_detector.py — MA200 とマクロニュースを合成して市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力ツール
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルのみ抜粋しています。詳細は src/kabusys ディレクトリを参照してください。）

---

## 開発・運用上のヒント

- テスト / CI:
  - Settings の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。テスト時に環境汚染を防ぐのに便利です。

- ログ:
  - 各スクリプトは logging.basicConfig(level=logging.INFO) などで基本的なログ出力を行います。詳細なデバッグには LOG_LEVEL を DEBUG に設定してください。

- DB のバックアップ:
  - DuckDB / SQLite はローカルファイルです。運用時は定期的なバックアップを推奨します。

- 安全停止:
  - 強制的にプロセスを kill するよりも、監視が書き込む kill.flag / stop_requested.flag を使った優雅な停止手順を推奨します。

---

## よく使うコマンドまとめ

- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（Paper Trading）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に記載のない内部仕様や API の詳細はソースコードの docstring を参照してください。必要であれば README に追加したい運用手順や FAQ を教えてください。