# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。本リポジトリは主に次の機能を提供します:

- 実行エンジン（ExecutionEngine）を介した発注・リスク管理
- 監視（MonitoringEngine）によるシステム状態 / 注文状態 / リスク監視とアラート
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索
- ニュースを LLM（OpenAI）で評価して銘柄ごとのスコアを生成する AI モジュール
- Paper Trading 用の検証レポート出力ツール
- Streamlit ベースの監視ダッシュボード

以下に使い方・セットアップ方法・主要なモジュール構成を記します。

注意: 本 README は src/kabusys 以下のコード構成に基づき作成しています。

---

## 主要機能（機能一覧）

- Execution（発注）関連
  - OrderManager / OrderRepository / Reconciler による注文ライフサイクル管理・再同期
  - ブローカークライアントの抽象化（実運用/モックを切り替え可能）
  - Paper Trading モードでは実口座と完全分離された SQLite（デフォルト: data/paper_trading.db）を使用

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク使用率、実行プロセスの有無、データ鮮度を監視
  - TradeMonitor: 注文滞留・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新、リスクイベント記録
  - KillSwitch: 閾値超過時に flag ファイルを書いて ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Messaging API による通知送信（クールダウン管理）

- Research / Portfolio
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - feature_exploration: 前方リターン計算・IC（Information Coefficient）・統計サマリー
  - portfolio: 候補選定・等配分/スコア配分・リスク調整・ポジションサイズ計算

- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄別センチメント（ai_scores）を記録
  - regime_detector: ma200 とマクロセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成する CLI ツール
  - streamlit_dashboard: 監視 DB を読み取る簡易ダッシュボード（Streamlit）

---

## セットアップ手順

前提
- Python 3.10+ を想定（Union 型の | などを使用）
- SQLite は標準ライブラリで利用可能
- 必要な OS パッケージはプラットフォーム依存（psutil によるプロセス優先度設定など）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （requirements.txt がない場合は上記を個別にインストールしてください）

3. data ディレクトリを作成
   - mkdir -p data

4. 環境変数（.env）を用意
   プロジェクトルートに .env（または .env.local）を作成すると自動でロードされます（デフォルト挙動）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な環境変数（例）:
   - KABUSYS_ENV=development | paper_trading | live
     - paper_trading: 実ブローカーを使わず paper 用 DB に書き込む
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...  （AI モジュールを使う場合必須）
   - PAPER_FILL_MODE=instant | partial | never | reject  (default: instant)
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - MONITOR_POLL_INTERVAL=60  （監視ループのポーリング間隔秒。0以下は無効）

   注意: Settings クラスは必須のキー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）をチェックします。未設定の場合は ValueError が発生します。

---

## 実行方法（使い方）

プロジェクトをパッケージとして実行できるように設計されています（src 配下を PYTHONPATH に含めるか、パッケージ化してください）。例えばリポジトリルートから以下のように実行できます。

1. 監視プロセス（MonitoringEngine）の起動
   - python -m kabusys.run_monitoring
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定できます（デフォルト 60 秒）。
     - 監視は常に Settings.sqlite_path（本番 DB）を使用します（paper_trading 環境でも同様）。

2. 実行エンジン（ExecutionEngine）の起動
   - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録します。
     - 起動時に data/stop_requested.flag が存在すると起動を中止します。
     - 実行中は data/execution.pid に PID が書き込まれ、停止指示は data/kill.flag を書くことで発行できます（KillSwitch を通した停止）。

3. Streamlit ダッシュボード（監視データの可視化）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     - 監視 DB の読み取り専用 URI を使用して接続します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - もしくは DB 指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI / レジーム判定（プログラム経由）
   - モジュール関数を直接呼び出して利用します（例: kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime）。
   - 直接 CLI エントリは提供されていないため、スクリプト／REPL から呼び出してください。OPENAI_API_KEY が必要です。

例（簡易的な実行例 - REPL）:
   python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime, os; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), os.environ.get('OPENAI_API_KEY')))"

（上記は例示です。DuckDB のテーブル構成や raw_news の存在が前提になります）

---

## 環境変数と設定（要点）

- 自動 .env ロード:
  - プロジェクトルートが自動検出されると .env と .env.local がロードされます（既存 OS 環境変数は保護されます）。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 重要な設定項目（Settings クラスより）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能利用時に必須）
  - KABUSYS_ENV: development / paper_trading / live
    - is_paper フラグで paper_trading モードを切り替えます
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定振る舞い）
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - LOG_LEVEL（DEBUG/INFO/...）
  - PID_FILE_PATH / KILL_FLAG_PATH
  - CPU / MEMORY / DISK の閾値（監視）

---

## 停止・制御ファイル

- 停止フラグ:
  - data/stop_requested.flag — run_monitoring.py / run_execution.py がループ内で存在をチェックして停止動作を行います（主に開発向け）。
- 強制停止（Kill Switch）:
  - data/kill.flag — KillSwitch が作成するファイル。ExecutionEngine 停止のトリガーとして利用されます。KillSwitch.clear() で削除可能です。
- PID ファイル:
  - data/execution.pid — ExecutionEngine 実行中に書き込まれる PID。SystemMonitor はこの PID を参照してプロセスが存続しているかチェックします。

---

## ディレクトリ構成（主要ファイルと説明）

リポジトリの主要なソース配置は src/kabusys 以下です。抜粋と簡単な説明:

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 用分離あり）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite による監視ログの永続化（テーブル初期化・CRUD）
  - monitoring_engine.py — System/Trade/Risk Monitor を束ねるポーリングエンジン
  - system_monitor.py — CPU/MEM/ディスク / データ鮮度 / 実行プロセス監視
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション数の監視とダッシュボード更新
  - kill_switch.py — 条件に応じた kill.flag 書き込み / 管理
  - alert_manager.py — LINE への通知送信（クールダウン）
  - streamlit_dashboard.py — Streamlit ベースの簡易ダッシュボード

- src/kabusys/execution/
  - order_manager.py — 注文作成 / 送信 / 同期などの外向き API
  - reconciler.py — 起動時の注文・ポジション再同期ロジック
  - （その他: broker_factory, execution_engine, order_repository 等が存在）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重みづけ
  - position_sizing.py — 株数計算・単元丸め・集計キャップ
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum/Volatility/Value のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py — raw_news を OpenAI に投げ銘柄別スコア生成（ai_scores への書き込み）
  - regime_detector.py — ma200 とマクロセンチメントを合成して market_regime テーブルへ書き込み

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI

- src/kabusys/utils/
  - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意点

- データベース分離
  - paper_trading モードでは paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番の monitoring DB と書き込みを分離します。設定ミスに注意してください。

- 環境変数の自動ロード
  - config.py はプロジェクトルートの .env/.env.local を自動で読み込みます。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってロードを抑止できます。

- OpenAI の使用
  - news_nlp / regime_detector は OpenAI API を呼び出します。API キー（OPENAI_API_KEY）と利用制限に注意してください。API 呼び出しはリトライ/フォールバックロジックを持ちますが、失敗時は「スコア無し」やデフォルト値で継続する設計です。

- プロセス優先度設定
  - run_* スクリプトは起動時に set_process_priority("high") を試みます。この操作には権限が必要な場合があるため、PermissionError 相当のケースでは警告が出てスキップされます。

- ロギング
  - デフォルトは INFO レベルです。LOG_LEVEL 環境変数で変更できます。

---

## トラブルシューティング（簡易）

- monitoring が起動しない / DB が作成されない
  - .env のパス設定（SQLITE_PATH / DUCKDB_PATH）を確認。data ディレクトリの書き込み権限を確認してください。

- Execution 起動時にすぐ終了する
  - data/stop_requested.flag が存在しないか確認。PID ファイルや kill.flag の存在も確認してください。

- AI 関連で例外が出る
  - OPENAI_API_KEY の有無、ネットワーク、API レスポンスの仕様変更に注意。ログに詳細が出力されます。

---

この README はコード内の docstring とモジュール設計に基づく簡易ガイドです。より詳細な設計（例えば PortfolioConstruction.md, StrategyModel.md 等）が別途存在することを想定しています。必要であれば、各モジュールの API サンプルやユースケース別の運用手順（デプロイ方法、サービス化、監視ポリシー）を追記できます。