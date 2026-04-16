# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行/監視ツール群）。  
本リポジトリはトレード実行エンジン、監視基盤、ポートフォリオ構築・リスク調整ロジック、研究用ファクター計算、LLM を使ったニュース NLP / レジーム判定などを含みます。

## 概要
- 実売買用の ExecutionEngine と、稼働監視・アラート・自動停止判定を行う MonitoringEngine を備える。
- Paper Trading モードを用意しており、本番 DB と分離して模擬売買ができる。
- DuckDB を用いた時系列/財務データ処理と、SQLite による監視ログ・発注ログの永続化。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価・市場レジーム判定をサポート（APIキー必須）。
- Streamlit による監視ダッシュボード、検証用レポート生成ツール等を付属。

## 主な機能一覧
- Execution
  - 実際のブローカークライアント（または Paper Trading 用 Mock）を介した発注管理
  - 再起動時のリコンシリエーション（未確定注文の同期、ポジション差分チェック）
  - リスク管理（注文レート制限、最大ポジション比率、ドローダウン判定 等）
- Monitoring
  - CPU / メモリ / ディスク / 実行プロセス生存チェック
  - 注文滞留（stale orders）・約定価格異常検知
  - ダッシュボード集計（dashboard テーブル）
  - Kill Switch：致命的リスク検出時に data/kill.flag を書き込んで ExecutionEngine を停止
  - LINE への通知（AlertManager）
  - Streamlit ダッシュボード（read-only で監視 DB を参照）
- Portfolio（純粋関数群）
  - 候補選定、等金額／スコア加重、ポジションサイズ計算、セクター上限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント生成 → ai_scores テーブルへ書込
  - 市場レジーム判定（ETF MA + マクロニュース LLM 合成）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <your-repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil requests openai streamlit
   - ※ 実際の環境では requirements.txt がある場合はそちらを利用してください。
4. 環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` に設定できます（自動ロードされます）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（デフォルト値・用途）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動、デフォルト "instant"）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視・trade_logs 用 DB）
     - DUCKDB_PATH: data/kabusys.duckdb（時系列・財務データ用）
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（既定 60）
     - LOG_LEVEL: DEBUG/INFO/...
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
5. データディレクトリ作成
   - mkdir -p data

## 使い方（主要な実行コマンド）
- 監視ループ（MonitoringEngine の起動）
  - 実行方法（モジュール）：python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更：MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 動作: process priority を上げ、SQLite（settings.sqlite_path）へ接続して SystemMonitor を定期実行します。停止はプロジェクトルートの data/stop_requested.flag を作成すると監視ループが検知して終了します。

- 実行エンジン（ExecutionEngine）の起動
  - 実行方法（モジュール）：python -m kabusys.run_execution
  - Paper Trading モード：KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 停止: Kill Switch によって data/kill.flag が書かれると実行エンジンが停止を受け付けます。手動で停止させたい場合は data/stop_requested.flag を作成すると run_execution のスレッドループが停止処理を呼びます。

- Paper Trading 検証レポート
  - コマンドライン：python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例：python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- Streamlit ダッシュボード（監視画面）
  - 起動方法：streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を読み取り専用で開いて概要・ポジション・過去発注・最新システムステータス等を表示します。

- AI 機能（ニュース NLP / レジーム判定）
  - これらはプログラム的に呼び出すか、専用の呼び出しラッパーを作成して利用します。OpenAI API キー（OPENAI_API_KEY）が必須です。
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
  - レスポンスは ai_scores / market_regime テーブルへ書き込まれます。

## 停止・フラグファイルについて
- stop_requested.flag
  - run_monitoring.py / run_execution.py が監視している停止フラグ（project_root/data/stop_requested.flag）。存在するとそれぞれ終了処理を行います。
- kill.flag
  - KillSwitch が検出した致命的なリスク時に書き込み、ExecutionEngine に停止要求を出すために使用（ファイル内容は理由テキスト）。既存の場合は再書き込みを行いません。
- execution.pid
  - ExecutionEngine の PID を記録。system_monitor はこの PID を見てプロセスの生存を確認し stale PID を検出できます。

## 環境変数自動ロード
- プロジェクトルートに `.env` / `.env.local` があれば自動的に読み込みます（OS 環境変数より優先度は低い）。  
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン等
  - config.py — Settings クラス（環境変数・.env 管理）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク・プロセス・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション数監視（KillSwitch 連携）
    - kill_switch.py — kill.flag の作成・管理
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, execution_engine.py ...（発注・リコンシリエーション・リスク管理ロジック）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・単元丸め・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラ / バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント集約・書き込み
    - regime_detector.py — MA + LLM を組み合わせた日次レジーム判定
  - data/  （実行時に生成・利用される想定）
    - monitoring.db（デフォルト SQLITE_PATH）
    - kabusys.duckdb（デフォルト DUCKDB_PATH）
    - paper_trading.db（paper_trading 用 DB）
    - execution.pid / kill.flag / stop_requested.flag

（上記は代表的なファイル群であり、実際のリポジトリ内のサブモジュールはさらに存在します）

## 実運用上の留意点
- 本番（live）モードは慎重に。API キーや kabu ステーション等の認証情報の管理を厳重に行ってください。
- Paper Trading を活用して十分な検証を行い、Reconciler / RiskManager / KillSwitch の動作を確認してください。
- OpenAI を用いる機能は外部 API 呼び出しに失敗する可能性があるため、失敗時はフォールバック（スコア=0 等）する設計になっていますが、運用ポリシーを検討してください。
- process priority / CPU affinity 設定は管理者権限や OS 制約により失敗する場合があります（警告ログでスキップされます）。

## 例：簡単な起動手順
1. .env を作成して必要なキーを設定
2. data ディレクトリを作成
3. 監視を開始
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
4. 別端末で実行エンジンを起動（Paper Trading）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. 検証レポート（任意期間）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
6. ダッシュボード（Streamlit）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースから主な設計・運用フローを抜粋してまとめたものです。各モジュールの詳細な仕様や実装は該当ソース内の docstring・コメントを参照してください。必要であればセクションの追記（運用手順、デプロイ例、テスト方法等）を作成します。