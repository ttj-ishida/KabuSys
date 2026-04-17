# KabuSys — README

## プロジェクト概要
KabuSys は日本株の自動売買／研究／監視を目的とした軽量なシステムです。  
主要機能は注文発行・リコンシリエーション、ポートフォリオ構築、ファクター計算、ニュース NLU によるセンチメント評価、監視・アラート、Paper Trading 向けの検証ツールなどを含みます。

設計方針の要点：
- DuckDB / SQLite を用いたローカルデータ処理（外部取引所へは明示的に接続）
- 環境ごとに挙動を切り替え（development / paper_trading / live）
- 監視コンポーネントは独立してポーリング実行・ログ蓄積
- LLM（OpenAI）を取り込んだニュース解析とレジーム判定（API キー必須）

---

## 機能一覧
- Execution（発注エンジン）
  - Broker クライアント抽象化（本番・モックを切替）
  - OrderManager による状態管理、リスク制御、Reconciler による起動時の自動復旧
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文、約定異常価格検知
  - RiskMonitor: ドローダウン／ポジション数監視とリスクログ記録
  - AlertManager: LINE Push による通知（オプション）
  - KillSwitch: 条件に応じて停止フラグを書き込み ExecutionEngine を停止
  - Streamlit ベースの監視ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア配分、リスク調整（セクター上限、レジーム乗数）、株数算出（単元丸め）
- Research（研究）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースの銘柄別センチメントスコア生成（ai_scores への書き込み）
  - マクロニュース + ETF MA200 による日次レジーム判定（market_regime への永続化）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 要件（推奨）
- Python 3.10+
- DuckDB
- psutil
- requests
- openai（OpenAI SDK）
- streamlit（ダッシュボード使用時）
（実際の環境では requirements.txt を用意し、pip install -r requirements.txt を推奨）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   ※ requirements.txt がない場合は以下を最低限インストールしてください：
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（既存の OS 環境変数は保護）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数例（.env）:
   ```
   KABUSYS_ENV=development             # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...                  # AI 機能を使う場合必須
   LINE_CHANNEL_ACCESS_TOKEN=...       # 通知を使う場合
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant             # instant | partial | never | reject
   MONITOR_POLL_INTERVAL=60            # 監視ポーリング間隔（秒）
   ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 実行方法（主なスクリプト）

- 監視ループを起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しません）。
  - 停止方法: プロジェクトの data/stop_requested.flag を作成するとループが終了します。

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と分離）。
  - 起動時に data/execution.pid を生成し、停止時に削除されます。
  - 外部停止シグナル: data/stop_requested.flag を作成すると起動中のエンジンを停止します。
  - Execution 起動時に kill.flag（Settings.kill_flag_path）が存在する場合は起動を行いません。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パス: `data/paper_trading.db`
  - オプション `--db PATH` で別の DB を指定可能。

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を read-only で開き、Overview / Positions / Orders / System タブを提供します。

---

## 主要な設定と環境変数の効果（抜粋）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading 時は発注処理がモック化され、paper_trading 専用 SQLite に記録されます。
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: Paper Trading のモック執行挙動（instant / partial / never / reject）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY: news_nlp / regime_detector で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）で必要
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス管理に使用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（Settings）

---

## 停止・管理
- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクトルートの data/stop_requested.flag の存在を監視します。ファイル作成で安全に停止できます。
- kill.flag
  - KillSwitch が条件を満たすと `data/kill.flag`（Settings.kill_flag_path）を書き込み、ExecutionEngine の起動防止や停止トリガーになります。`KillSwitch.clear()` で削除可能。
- PID ファイル
  - Execution は data/execution.pid を作成します。SystemMonitor は stale PID を検出するとファイルを削除してアラート記録します。

---

## 使い方（例）
- Paper Trading で発注ロジックの統合テストを行いたい
  1. .env に `KABUSYS_ENV=paper_trading` と `PAPER_TRADING_SQLITE_PATH` を設定
  2. `python -m kabusys.run_execution` を起動（モックブローカーで発注が記録される）
  3. `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db` で検証

- 監視を常時稼働させたい
  1. 必要な環境変数（DBパス等）を設定
  2. `python -m kabusys.run_monitoring` をデーモン / systemd / supervisor などで実行
  3. 問題があれば LINE に通知される（設定済みの場合）

- ニュース NLP によるスコア取得
  - `kabusys.ai.score_news(conn, target_date, api_key=...)` を呼ぶ（OpenAI API キー必須）

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
- src/kabusys/execution/
  - execution_engine.py (実装あり) — 実行エンジン本体（エンジン設定・セッション管理）
  - order_manager.py — 注文状態管理
  - reconciler.py — 起動時リコンシリエーション
  - order_repository.py, order_record.py, broker_* — ブローカー抽象 / 実装
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・CRUD（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — システム状態監視
  - trade_monitor.py — 注文関連監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止条件判定 & フラグ書き込み
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を統合するランナー
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- src/kabusys/research/
  - factor_research.py, feature_exploration.py — ファクター計算 / 分析ユーティリティ
- src/kabusys/ai/
  - news_nlp.py — ニュース NLP（OpenAI 呼び出し、スコア保存）
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力ツール
- data/
  - monitoring.db (既定) / paper_trading.db / kabusys.duckdb / kill.flag / stop_requested.flag / execution.pid など（実行時に生成）

---

## 注意事項 / ヒント
- Settings はプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込みます。パッケージ配布後も CWD に依存しない設計です。
- OpenAI や LINE などの外部 API はそれぞれのクレデンシャル（API キー）を正しく設定する必要があります。AI 機能はキー未設定時に例外やフォールバックを行う箇所がありますが、期待通りの結果を得るにはキーをセットしてください。
- process priority / CPU affinity の設定は psutil を使います。権限やプラットフォームにより設定に失敗する場合があり、ログに警告が出ますが実行自体は継続します。
- DuckDB / SQLite のファイルはデフォルトで `data/` 配下に置かれます。バックアップや排他アクセスに注意してください（Streamlit は read-only URI を使用可能）。

---

必要があれば、README に以下を追加できます：
- requirements.txt の候補一覧
- systemd / supervisor 用のサービス定義例
- テストの実行方法（ユニットテストが追加されている場合）
- 各モジュール（ExecutionEngine, Broker 実装など）の詳細設計ドキュメントリンク

必要な追記や日本語表現の修正があれば教えてください。