# KabuSys

日本株向け自動売買システムのサブセット実装（モニタリング・注文実行・ポートフォリオ構築・リサーチ・AI 補助など）。本リポジトリは主要コンポーネント群をモジュール化しており、実運用／Paper Trading／研究用途に応じたモード切替を想定しています。

以下はこのコードベースに基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買/リサーチ基盤です。本コードベースには次のような責務を持つコンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: ブローカーとのやりとり、オーダー状態管理、リスク制御、リコンシリエーション。
- Monitoring（監視）: システム稼働・データ鮮度・滞留注文・約定異常・ドローダウン等を定期チェックしログ・アラートを出す。
- Portfolio Construction: 候補選定、重み計算、ポジションサイズ計算、セクター制約やレジーム調整。
- Research: DuckDB を使ったファクター計算、将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ。
- AI（OpenAI）連携: ニュース記事ベースのセンチメント算出や市場レジーム判定（gpt-4o-mini を利用）。
- ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボードなど。

設計上、
- DuckDB は時系列／ファクターデータ向け（デフォルト: `data/kabusys.duckdb`）、
- SQLite は監視ログ/オーダーログ等の永続化（デフォルト: `data/monitoring.db` / Paper Trading 用: `data/paper_trading.db`）、
- .env による環境変数管理をサポートします。

---

## 主な機能一覧

- SystemMonitor: CPU/MEM/DISK モニタリング、Execution プロセスの生存確認、データ鮮度チェック
- TradeMonitor: 滞留注文（stale orders）検出、約定価格異常検出
- RiskMonitor: ドローダウン／ポジション上限監視、ダッシュボード更新、リスクログ記録
- KillSwitch: 一定条件でフラグファイル（data/kill.flag）を書き、ExecutionEngine 停止を促す
- AlertManager: LINE Messaging API による一方向通知（クールダウン管理）
- MonitoringEngine: 上記モニタを束ねてポーリング実行
- ExecutionEngine まわり: ブローカー抽象化、OrderManager、Reconciler（再起動後の同期）
- Portfolio: 候補選定、重み付け、ポジション決定（lot丸め・aggregate cap 等）
- Research: モメンタム/ボラティリティ/バリュー等のファクター計算、特徴探索・IC 計算
- AI: ニュースのセンチメントスコア化（ai_scores へ保存）、市場レジーム判定（market_regime へ保存）
- ツール:
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`
  - Streamlit ダッシュボード: `kabusys.monitoring.streamlit_dashboard`

---

## セットアップ手順（開発環境向け）

※ プロダクションでのデプロイ手順は運用環境に依存します。ここではローカルで実行するための最低限の手順を示します。

1. Python バージョン
   - 推奨: Python 3.10 以上

2. リポジトリをクローン（例）
   - git clone <repo-url>
   - ソースは `src/` 配下に配置されている前提です。実行時はプロジェクトルートをカレントにするか、PYTHONPATH に `src` を設定してください。
     例: `export PYTHONPATH=$(pwd)/src`

3. 依存パッケージをインストール（最小）
   - pip install duckdb psutil requests streamlit openai
   - sqlite3 は標準ライブラリに含まれます。

   （requirements.txt がある場合はそれを利用してください）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数 / .env
   - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい。

   代表的な環境変数（例・デフォルト）:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN（必須 if 使う場合）
   - KABU_API_PASSWORD（kabuステーション API パスワード）
   - OPENAI_API_KEY（AI 機能利用時に必要）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - PID_FILE_PATH（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE（paper_trading の fill モード: instant|partial|never|reject）
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）, run_monitoring で使用、デフォルト 60）

6. DB 初期化
   - 多くのモジュールは起動時に必要なテーブルを作成（冪等）します。明示的な初期化は不要ですが、Monitoring を使う場合は `init_monitoring_db()` が呼ばれます。

---

## 使い方（主要な起動方法・コマンド）

※ 実行はプロジェクトルートから、または PYTHONPATH を `src` に設定して行ってください。

1. Monitoring（ポーリング）を起動
   - コマンド:
     - python -m kabusys.run_monitoring
   - 動作:
     - プロセス優先度を high に設定
     - 設定から sqlite/duckdb に接続して SystemMonitor をポーリング
     - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）

2. ExecutionEngine（注文実行）を起動
   - コマンド:
     - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`）に記録して本番 DB と完全分離
     - リスク管理やリコンシリエーションを行い、セッションを実行

3. Paper Trading 検証レポート
   - コマンド:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db path/to/paper_trading.db
   - 出力:
     - システム稼働率、注文成功率、送信率、レイテンシ（P95）等を集計してレポート表示

4. Streamlit 監視ダッシュボード（ローカル閲覧）
   - コマンド:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 概要:
     - data/monitoring.db を read-only で開き、ダッシュボード表示（Overview / Positions / Orders / System）

5. AI 関連（スコアリング / レジーム判定）
   - 関数呼び出し（スクリプトから利用）:
     - kabusys.ai.score_news（ニュース NLP によるスコア算出、OpenAI API キーが必要）
     - kabusys.ai.regime_detector.score_regime（市場レジームを計算して DB に書き込む）
   - 環境変数:
     - OPENAI_API_KEY を設定

---

## 主要な設定（Settings クラスに定義されているもの）

- JQUANTS_REFRESH_TOKEN（必須 when used）
- KABU_API_PASSWORD（必須 when using kabu API）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant / partial / never / reject）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（閾値）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

デフォルト値・バリデーションは `src/kabusys/config.py` を参照してください。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / .env の読み込み・Settings 定義
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを OpenAI でセンチメントスコア化し ai_scores に書込む
  - regime_detector.py — ETF MA とマクロセンチメントを合成して market_regime を生成
- monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル初期化・読み書き）
  - system_monitor.py — CPU/MEM/DISK/データ鮮度/プロセス監視
  - trade_monitor.py — 滞留注文 / 約定異常価格のチェック
  - risk_monitor.py — ドローダウン、ポジション上限監視（dashboard 更新・risk_logs 書込）
  - kill_switch.py — kill.flag の作成／削除
  - alert_manager.py — LINE Push による通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの監視画面
- execution/
  - order_manager.py — オーダー作成／送信／キャンセルの外向け API
  - reconciler.py — 起動時リコンシリエーション（注文・ポジションの突合）
  - （その他 broker 関連やリポジトリ等が存在する想定）
- portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 発注株数計算・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — プラットフォームを抽象化したプロセス優先度／CPU affinity 設定ユーティリティ

その他（参照のみ）
- data/ — デフォルトの DB ファイル・PID・フラグファイル等を置くディレクトリ（手動作成推奨）

---

## 運用上の注意・ベストプラクティス

- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と明確に分離されるよう設計されています。Paper 用 DB は `PAPER_TRADING_SQLITE_PATH` を使ってください。
- OpenAI や外部 API 呼び出しは失敗時にフェイルセーフ（スコアを 0.0 とする等）になっており、リトライ・バックオフが実装されていますが、API キー管理・レート制限には注意してください。
- Monitoring は MONITOR_POLL_INTERVAL で制御可能。短くしすぎると負荷やレート制限に影響します。
- process priority / CPU affinity の設定は psutil を利用して行います。権限がない場合は警告が出てスキップされます。
- データ鮮度チェック・レジーム判定・アラートは運用ポリシーに合わせて閾値やクールダウンを調整してください。
- .env 自動ロードはプロジェクトルート（.git や pyproject.toml があるディレクトリ）を基準に行われます。テストや CI から自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 参考コマンドまとめ

- 監視の起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

もし README に追加したい実行例、.env.example のテンプレート、またはデプロイ手順（systemd / docker / k8s など）について要望があれば、用途に合わせて追記します。