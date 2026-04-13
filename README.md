# KabuSys

KabuSys は日本株向け自動売買システムのコアライブラリ群です。  
このリポジトリには、実行エンジン、監視（Monitoring）、ポートフォリオ構築、調査・リサーチ、AI を使ったニューススコアリングなどの主要コンポーネントが含まれます。

以下はローカル開発 / 運用のための README（日本語）です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成
- 環境変数（主なもの）
- 注意点 / トラブルシューティング

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 株価データ（DuckDB）に基づくファクター計算・リサーチ
- シグナルからのポートフォリオ構築（候補選定・重み計算・ポジション決定）
- 発注管理・ExecutionEngine（ブローカー API 経由の発注・リコンシリエーション）
- 監視サブシステム（システム状態、滞留注文、リスクアラート、Kill Switch）
- Paper Trading 用の分離された DB モード
- AI（OpenAI）を利用したニュースセンチメント集計・市場レジーム判定
- Streamlit ベースの監視ダッシュボード

設計方針の一例：
- 多くの内部ロジックは純粋関数（副作用を持たない）として実装され、テストしやすい
- DB（監視ログ）は SQLite、分析は DuckDB を利用
- Paper Trading は本番 DB と完全に分離して動作する

---

## 機能一覧

- Execution（起動スクリプト: run_execution.py）
  - 実際のブローカーまたはモック（paper_trading）を使った発注実行
  - OrderManager、RiskManager、Reconciler 等による堅牢な発注ライフサイクル
- Monitoring（起動スクリプト: run_monitoring.py）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視・ダッシュボード更新
  - KillSwitch: 条件により ExecutionEngine 停止用フラグファイル生成
  - AlertManager: LINE に一方向通知（クールダウン管理付き）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio
  - 候補選定（スコア順）、等分配/スコア加重配分、リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ決定（単元株丸め・最大投下額スケール・aggregate cap）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント（銘柄別） -> ai_scores へ書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースセンチメント合成によるレジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

※ Python 3.10+ を想定（型注釈で | を使用）。環境に合わせて調整してください。

1. Python 環境を用意
   - 推奨: venv や poetry を使用して仮想環境を作成

2. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がない場合、以下の主要パッケージをインストールしてください（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     ```
     python -m pip install duckdb psutil requests openai streamlit
     ```

3. データディレクトリ作成
   - デフォルトのデータパスは `data/` 下です。必要に応じて作成してください。
     ```
     mkdir -p data
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（OS 環境変数を上書きしない挙動）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主な環境変数については下段「環境変数」を参照してください。

5. DB の初期化
   - run_monitoring.py / run_execution.py は起動時に監視用の SQLite テーブルを冪等に作成します。まずは監視プロセスを起動するだけで初期化されます。

---

## 使い方（起動・操作例）

- 監視ループを起動（Production 用の sqlite_path を使用）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書きできます（デフォルト 60）。
  - スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil 経由）。権限エラーは警告として扱われます。

- ExecutionEngine を起動（本番 / paper_trading を切替）
  ```
  # 本番（デフォルト: KABUSYS_ENV=development だが production にする等は環境で設定）
  python -m kabusys.run_execution

  # Paper Trading モード（MockBrokerを使用・データは data/paper_trading.db に記録）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - Paper Trading の DB は `PAPER_TRADING_SQLITE_PATH` で上書き可能。
  - Paper Trading の約定挙動は `PAPER_FILL_MODE`（instant/partial/never/reject）で制御。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` で読み取り専用 DB パスを指定可能（デフォルト: data/monitoring.db）。

- AI 関連（OpenAI API を使う処理）
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key 引数を渡してください。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要ディレクトリ / ファイル構成

src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ（主要なファイル）
- monitoring/
  - monitoring_db.py — SQLite テーブル定義と簡易 CRUD（init_monitoring_db、MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度・PID チェック
  - trade_monitor.py — 滞留注文・約定異常判定
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — フラグファイルによる Execution 停止シグナル
  - alert_manager.py — LINE Push 通知ラッパ
  - monitoring_engine.py — 各 Monitor を束ねる実行ロジック
  - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
- execution/
  - order_manager.py, order_repository.py, reconciler.py, ... — 発注管理 / リコンシリエーション関連
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラ/バリュー計算（DuckDB 経由）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ等
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI を利用）
  - regime_detector.py — マクロセンチメント + MA200 によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 環境変数（主なもの）

- KABUSYS_ENV
  - 有効値: development, paper_trading, live
  - デフォルト: development
  - paper_trading のとき Execution は MockBroker を使い、別 SQLite（paper_sqlite_path）へ書き込む

- SQLITE_PATH
  - 監視 DB パス（SQLite）
  - デフォルト: data/monitoring.db

- DUCKDB_PATH
  - DuckDB ファイルパス（分析用）
  - デフォルト: data/kabusys.duckdb

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）

- MONITOR_POLL_INTERVAL
  - Monitoring のポーリング間隔（秒）。デフォルト 60 秒。1 未満の値は無効。

- PID_FILE_PATH
  - ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）

- KILL_FLAG_PATH
  - KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
  - Execution 停止のトリガとして書き込まれる

- PAPER_FILL_MODE
  - Paper Trading の約定挙動: instant / partial / never / reject（デフォルト: instant）

- OPENAI_API_KEY
  - OpenAI を使う AI 機能の API キー

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - AlertManager（LINE）で通知を送るための設定。未設定時は送信をスキップ（ログのみ）

- LOG_LEVEL
  - ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

---

## 注意点・トラブルシューティング

- DB 初期化
  - monitoring のテーブル作成は run_monitoring と run_execution の起動時に自動で行われます（冪等）。手動で初期化したい場合は MonitoringDB.init_monitoring_db を呼び出してください。

- Paper Trading
  - paper_trading モードでは本番 DB と完全分離して動作します（paper_sqlite_path を使用）。必ず環境変数で切り替えを確認してください。

- OpenAI API
  - news_nlp / regime_detector は API 呼び出しに失敗した場合はフォールバック（スコア 0.0 等）する設計ですが、APIキー未設定だとエラーを投げる箇所があります。事前に OPENAI_API_KEY をセットしてください。

- プロセス優先度 / CPU affinity
  - 起動時にプロセス優先度を上げようとしますが、権限不足や未対応 OS の場合は警告を出してスキップします（psutil に依存）。

- kill.flag の取り扱い
  - KillSwitch はファイル存在で停止を指示します。ExecutionEngine の起動時には `kill_flag_clear_on_start` 設定で開始時にクリアする挙動が制御できます。

- Streamlit
  - Streamlit は DB を読み取り専用（URI に ?mode=ro を付与）で開きます。監視プロセスが DB を保持している場合でも読み取り可能なことが多いですが、環境により接続エラーが発生することがあります。

- ロギング
  - 多くのスクリプトは logging.basicConfig(level=logging.INFO) で起動します。詳細ログが必要な場合は LOG_LEVEL=DEBUG を設定してください。

---

もし README に追加してほしい詳細（例えば開発時のテスト実行方法、具体的な OrderRepository スキーマ、外部ブローカープラグイン実装方法など）があれば教えてください。必要に応じてサンプル .env.example も作成します。