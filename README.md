# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群抜粋）。  
この README はコードベースから抽出した概要・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株の自動売買エンジンとその運用を支える監視・リサーチ・AI 支援モジュール群を含むソフトウェア群です。主な役割は以下の通りです。

- Execution: ブローカークライアント経由での発注管理、リスク管理、再同期（リコンシリエーション）
- Monitoring: システム状態、注文滞留、ドローダウン等の監視・ログ化・アラート送信（LINE）
- Portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限 等のポートフォリオ構築ユーティリティ
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI: OpenAI（gpt-4o-mini）を用いたニュースのセンチメント評価や市場レジーム判定
- Tools: Paper Trading の検証レポート生成等の運用ツール

設計上のポイント:
- 環境（development / paper_trading / live）に応じた挙動切替
- 実行時の DB は明示（DuckDB と SQLite を併用）
- Paper Trading は本番 DB と分離（別 SQLite）
- 安全なフェイルセーフ（API失敗時のフォールバック、部分失敗時に既存データを保護）

---

## 主な機能一覧

- SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度の監視とログ化
- TradeMonitor: 滞留注文検知、約定異常価格の検出
- RiskMonitor / KillSwitch: ドローダウンやポジション上限の監視 → 必要に応じて停止フラグを書き込み
- MonitoringEngine: 上記モニタをまとめて定期実行、LINE への通知（AlertManager）
- ExecutionEngine 周辺: ブローカー抽象化、OrderManager、Reconciler（再同期）
- Portfolio ライブラリ: 候補選定、等重・スコア加重、リスクベースのポジションサイジング、セクターキャップ、レジーム乗数
- Research ツール: モメンタム / ボラティリティ / バリュー 等のファクター計算、IC 計算や統計サマリ
- AI モジュール: ニュースセンチメント計算（ai.news_nlp.score_news）・レジーム判定（ai.regime_detector.score_regime）
- 運用ツール: Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
- Streamlit ダッシュボード: 監視 DB を可視化するダッシュボードスクリプト

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業用ディレクトリへ移動します。
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成して有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（プロジェクトに requirements.txt がある想定）。
   - pip install -r requirements.txt
   - 必須ライブラリ（主に使用されるもの）: duckdb, psutil, openai, requests, streamlit

4. 環境変数を設定するか、プロジェクトルートに `.env` / `.env.local` を用意します。  
   自動ロードはデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

   代表的な環境変数:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
   - KABU_API_PASSWORD: 必須（kabuステーション API）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の専用 DB）
   - SQLITE_PATH: data/monitoring.db（監視用 SQLite）
   - DUCKDB_PATH: data/kabusys.duckdb（研究用データ格納）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
   - PID / flag 関連のパスは Settings で上書き可能（PID_FILE_PATH, KILL_FLAG_PATH 等）

5. データディレクトリを作る:
   - mkdir -p data

6. （任意）パッケージを開発モードでインストールするとモジュールを -m で起動しやすくなります:
   - pip install -e .

---

## 使い方（主要スクリプト）

※ 以下はプロジェクトルートから実行する前提です。`src` 配下を Python パスに含めるか、pip install -e でインストールしてください。

1. 監視ループを起動（SystemMonitor をポーリングして SQLite にログを保存）
   - 環境変数でポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30
   - 実行:
     - python -m kabusys.run_monitoring
     - または: PYTHONPATH=src python src/kabusys/run_monitoring.py
   - 備考:
     - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV に依存しない）。
     - 停止はプロジェクトルートの data/stop_requested.flag を作成することでループが検知して終了します。

2. ExecutionEngine を起動（注文エンジン）
   - Paper Trading モード例:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 本番モード例:
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   - 備考:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は data/paper_trading.db（設定で上書き可）に分離して記録します。
     - 起動時 / 実行中に data/stop_requested.flag を作成すると起動を抑止または実行中エンジンを停止します。
     - 実行中は data/execution.pid に PID を書き込みます（stale PID 検出ロジックあり）。

3. Streamlit ダッシュボード（監視 DB の可視化）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 備考:
     - 読み取り専用で DB を開くため、MonitoringEngine が監視 DB を作成/更新していることが前提です。

4. Paper Trading 検証レポート生成
   - 実行例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - または明示的 DB 指定:
       python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   - 出力: 標準出力に検証結果（稼働率、成功率、レイテンシ等）を表示します。

5. AIモジュール（プログラムから呼び出し）
   - ニュースセンチメント作成:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
   - レジーム判定:
     - from kabusys.ai import regime_detector
     - regime_detector.score_regime(conn, target_date, api_key="...")

6. フラグ制御（オペレーション）
   - Execution を強制停止させたい/キル条件を作る: data/kill.flag を作成（KillSwitch による判定・説明が書き込まれます）
   - kill.flag をクリアする: KillSwitch.clear() を利用するか手動でファイル削除

---

## 設定の自動ロード（.env）

- プロジェクトルートにある `.env` と `.env.local` が自動でロードされます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- .env のパースは export プレフィックスやシングル/ダブルクォート、コメント（#）を考慮した実装です。

---

## 注意事項 / トラブルシューティング

- プロセス優先度 / CPU affinity の設定は psutil を使用します。権限不足や未対応 OS の場合はログに WARN を出してスキップします。
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）が必須。API エラー・タイムアウトはリトライやフォールバックを行う設計ですが、キーが未設定だと例外を投げます。
- DuckDB/SQLite のパスは Settings によりデフォルト設定があります。実運用では永続ストレージのパスを明示してください。
- Paper Trading は本番 DB と分離しているため、本番データと混ざる心配はありません（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定の集中管理
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py  — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py         — ニュースを LLM でスコアリング
  - regime_detector.py  — マクロ＋ETF 指標で市場レジーム判定
- monitoring/
  - monitoring_db.py    — SQLite 用永続化層（テーブル初期化・読み書き）
  - system_monitor.py   — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py    — 注文滞留・約定価格異常チェック
  - risk_monitor.py     — ドローダウン・ポジション上限監視
  - kill_switch.py      — 停止フラグ管理
  - alert_manager.py    — LINE 通知ユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — ストリームリットダッシュボード
- execution/
  - order_manager.py
  - reconciler.py
  - （その他ブローカー・エンジン周りのモジュール）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py  — Paper Trading 向け検証レポート
- utils/
  - process_priority.py  — プロセス優先度 / CPU affinity 設定

data/（実行時に使うディレクトリ、デフォルト）
- monitoring.db (SQLite) — 監視ログ
- paper_trading.db (SQLite) — Paper Trading 用 DB
- kabusys.duckdb (DuckDB) — 価格・財務データなどのリサーチ DB
- stop_requested.flag, kill.flag, execution.pid  — 実行制御用フラグ / PID

---

## 開発者向け補足

- DuckDB 接続を引数として受け取り純粋関数として動作するモジュールが多く、テストしやすい設計です。
- モジュール間の外部 API 呼び出しは抽象化され（BrokerAPIProtocol 等）、Unit Test ではモック挿入が可能です。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等で、既存カラムの追加処理も内包しています。

---

この README はコード一覧からの抜粋に基づくドキュメントです。実運用やデプロイ時は各種環境変数・認証情報の安全管理、永続ストレージの設定、監視・ログの外部集約等を必ず検討してください。必要であれば各モジュールの API 仕様（関数引数・戻り値）や実行例をさらに詳細に追記します。