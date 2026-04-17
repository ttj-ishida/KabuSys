# KabuSys

KabuSys は日本株の自動売買 / 研究 / 監視を行うための小規模なシステム群です。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築やファクター計算、LLM を用いたニュース／レジーム判定ユーティリティなどが含まれます。

---

## 主な概要

- 発注ロジックや注文状態管理（OrderManager / Reconciler）
- Paper Trading と Live 運用の切り替え（環境変数 KABUSYS_ENV）
- 監視（System / Trade / Risk）と kill-switch（フラグファイル）による自動停止
- DuckDB を使った研究（ファクター計算・将来リターン・IC 計算など）
- OpenAI（gpt-4o-mini）を用いたニュース NLP と市場レジーム判定
- Streamlit ベースの監視ダッシュボード
- Paper Trading の検証レポート生成ツール

---

## 機能一覧

- Execution
  - ExecutionEngine による注文発行・リスク制御・リコンシリエーション
  - Paper Trading モード（ブローカーをモック、paper_trading 用 DB を使用）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、注文プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: リスクトリガー発生時に停止フラグを書き込み
  - AlertManager: LINE Push による通知（任意）
  - Streamlit ダッシュボード（read-only）
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・特徴量サマリー
  - 候補選定・重み計算・ポジションサイズ算出・セクター上限適用等
- AI
  - ニュース記事をまとめて LLM に送信し銘柄別センチメントを ai_scores に格納
  - マクロニュース + ETF MA200 を合成して日次レジーム判定（bull / neutral / bear）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提 / 依存パッケージ（代表）

最低限以下を用意してください。

- Python 3.10+
- pip install で以下など
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
（実際の requirements.txt はプロジェクトに合わせて用意してください）

例:
```
pip install duckdb psutil openai requests streamlit
```

---

## 環境変数（主なもの）

プロジェクトは .env / .env.local を自動でロードします（ルートに .git または pyproject.toml がある場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（例）:

- KABUSYS_ENV: 運用モード（`development` / `paper_trading` / `live`）。デフォルト：`development`
  - `paper_trading` の場合、Execution は MockBrokerClient を使用し、データは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込まれます（本番 DB と分離）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai/news_nlp.py, ai/regime_detector.py）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）
- PAPER_FILL_MODE: Paper Trading の約定モード（`instant` / `partial` / `never` / `reject`、デフォルト: `instant`）
- LOG_LEVEL: ログレベル（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルト `data/execution.pid` / `data/kill.flag`

.env の自動読み込みは OS 環境変数より優先度が低く、.env.local は .env を上書きできます。

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai requests streamlit
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

5. .env を作成して必須の環境変数を設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）

6. DuckDB/SQLite の初期データは、各スクリプト実行時に必要なテーブルの初期化（監視 DB など）を行います。Research 用の prices_daily / raw_financials 等は別途データロードが必要です（DuckDB に投入）。

---

## 実行方法（主要コンポーネント）

- ExecutionEngine（本番／paper_trading に対応）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録します。
  - 起動前に `data/stop_requested.flag` が存在すると起動を回避します。
  - 実行中は PID ファイル（デフォルト `data/execution.pid`）が書き込まれます。

- Monitoring（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく `SQLITE_PATH`（デフォルト `data/monitoring.db`）を使用します。
  - 監視ループを停止させるには `data/stop_requested.flag` を作成してください（監視ループ側で検出して終了）。

- Streamlit ダッシュボード（read-only）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only の SQLite URI で開くため、監視 DB が存在しない場合はエラー表示します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` で別パス指定可。
  - 稼働率、注文成功率、P95 レイテンシ等を集計して PASS / FAIL を表示します。

- AI 関連（ライブラリ関数）
  - ニュースセンチメント: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を必要とします。

---

## 停止フラグ / キルフラグの動作

- data/stop_requested.flag
  - run_monitoring / run_execution のループを終了させるためのシンプルな停止フラグ（存在を検出して終了）。

- data/kill.flag
  - KillSwitch（監視側）が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 起動時に `Settings.kill_flag_clear_on_start` が `1` の場合は起動時に自動でクリアできます（設定で制御）。

---

## 設定と挙動の注意点

- Process priority / CPU affinity
  - 起動スクリプトは最初に `set_process_priority("high")` を呼びます。psutil による操作で権限が必要な場合があります。失敗しても警告を出してスキップします。
- Monitoring DB 初期化
  - `init_monitoring_db()` により監視用のテーブル・インデックスを冪等に作成します。既存スキーマに対するマイグレーション（カラム追加）も行います。
- Paper Trading の DB 分離
  - `KABUSYS_ENV=paper_trading` のときは `paper_sqlite_path` を使用し、本番の monitoring DB と独立させます。
- OpenAI / API呼び出し
  - LLM 呼び出しはリトライやバックオフを実装していますが、API キー未設定時は ValueError を投げます。
  - AI 関連処理は外部 API を使うため、利用時はコストとレート制限に注意してください。

---

## 主要ディレクトリ構成とファイル説明

（src/kabusys 配下の主なファイルと簡単な説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込みロジック（Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体でのポーリング起動スクリプト
- src/kabusys/execution/
  - order_manager.py — 発注 API の上位ラッパ（OrderManager）
  - reconciler.py — 再起動時のリコンシリエーション（ブローカー照合）
  - その他（broker_factory, execution_engine, order_repository, risk_manager 等）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ層（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限の監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各 Monitor を束ねる
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・集約キャップ処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py — ファクター計算（Momentum, Volatility, Value）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM で評価して ai_scores に保存
  - regime_detector.py — ETF MA200 + マクロセンチメントでレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

---

## トラブルシューティング（よくある注意点）

- psutil による優先度設定で AccessDenied が出る場合は権限を高める（sudo 等）か、警告を許容してください。
- DuckDB / SQLite のテーブルは Research 用データが必要です。prices_daily / raw_financials 等が揃っていないと研究系 API はデータ不足になります。
- OpenAI 呼び出しで rate limit / timeout が発生した場合、モジュールはリトライを試みますが、最終的にスコア取得に失敗すると該当部分はスキップされます（フェイルセーフ設計）。
- monitoring / execution のループを停止したい場合は `data/stop_requested.flag` を作成するか、Execution 側は kill.flag に依存して停止処理を行います。

---

## 補足

- この README はコード内の docstring / コメントをもとに要点をまとめたもので、実運用前には環境変数の管理、権限、外部 API のコストやレート管理、データのバックアップ設計などを十分に検討してください。
- テストや CI、requirements.txt、データロードスクリプトは別途用意してください（本リポジトリに含まれていない場合があります）。

---

必要であれば、.env のテンプレート例、起動スクリプトの systemd ユニット例、または具体的な DuckDB データ投入手順（prices_daily 等）を追記します。どれを優先して欲しいか教えてください。