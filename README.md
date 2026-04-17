# KabuSys

日本株向け自動売買システムの実装スニペット群。戦略（シグナル生成）・ポートフォリオ構築・発注エンジン・監視・研究ユーティリティ・AI（ニュースセンチメント／レジーム判定）等の主要コンポーネントを含みます。

本 README はリポジトリ内のコードを参照して作成しています。各モジュールにはドキュメンテーション文字列が含まれているため、詳細は該当ソースを参照してください。

## プロジェクト概要
- 目的：日本株の自動売買を行うためのモジュール群。戦略ロジックとそれを実行するエンジン、監視・アラート機能、研究用ユーティリティを提供します。
- 主要特徴：
  - ExecutionEngine：ブローカーとのやり取り、注文管理、リスク制御、再起動時のリコンシリエーション。
  - Monitoring：システム稼働監視、注文滞留・約定異常検出、ドローダウン等のリスク監視、LINE通知と kill-flag による停止シグナル出力。
  - Portfolio construction：候補選定・重み計算・ポジションサイジング・セクター制限。
  - Research：DuckDB を用いたファクター計算・特徴量解析ユーティリティ。
  - AI モジュール：OpenAI（gpt-4o-mini 等）を利用したニュースセンチメントスコアリング、マクロニュースを使った市場レジーム判定。
  - Tools：Paper Trading の検証レポート生成や Streamlit ベースの監視ダッシュボード等。

## 機能一覧
- 実行関連
  - run_execution.py：ExecutionEngine を起動し、発注処理を行う（KABUSYS_ENV=paper_trading 時はモックブローカーを使用し paper_trading DB に記録）。
  - reconciler：再起動時の注文・ポジション突合（自動復旧）。
- 監視関連
  - run_monitoring.py：SystemMonitor をポーリングしてシステム状態を記録。
  - MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期実行、アラート送信・KillSwitch 判定。
  - AlertManager：LINE Push による通知（クールダウン機構あり）。
  - streamlit_dashboard.py：監視 DB を可視化する Streamlit アプリ。
- ポートフォリオ構築
  - portfolio_builder：候補選定、等配分/スコア加重配分。
  - position_sizing：株数決定、リスク制約・単元（lot）丸め、aggregate cap スケーリング。
  - risk_adjustment：セクター上限適用・レジーム乗数計算。
- 研究用
  - research/factor_research.py：モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDB）。
  - research/feature_exploration.py：将来リターン計算、IC、統計サマリ。
- AI（OpenAI）
  - ai/news_nlp.py：ニュース記事を集約し OpenAI で銘柄毎のセンチメントを算出して ai_scores テーブルへ保存。
  - ai/regime_detector.py：ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジーム判定を行い DB に保存。
- ユーティリティ
  - config.py：環境変数／.env の読み込みと Settings 抽象化（KABUSYS_ENV: development | paper_trading | live）。
  - utils/process_priority.py：プロセス優先度／CPU affinity 設定ラッパー。
  - monitoring/monitoring_db.py：SQLite による監視ログ永続化層。

## セットアップ手順（開発向け）
以下はローカルで動かすための一般的な手順です（実運用時は要適宜強化）。

1. Python 環境
   - Python 3.10+ を推奨（型注釈に union | を使用）。
   - 仮想環境を作成して有効化：
     - python -m venv .venv
     - source .venv/bin/activate  または Windows では .venv\Scripts\activate

2. 依存パッケージをインストール
   - 必要なパッケージの例（requirements.txt がない場合は手動インストール）:
     - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt / poetry / pipenv 等で依存を管理してください。

3. プロジェクトルートの .env ファイル（任意）
   - config.py は自動的にプロジェクトルート（.git または pyproject.toml がある場所）を探索して `.env` / `.env.local` を読み込みます（OS 環境変数を優先）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（例とデフォルト）:
     - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject  （デフォルト: instant）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY（AI モジュールを使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager）
     - LOG_LEVEL=INFO | DEBUG ...
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
   - 例 (.env):
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...

4. data ディレクトリ
   - スクリプトは default で data/ 以下に DB や PID/flag ファイルを作成します。必要に応じて作成してください（スクリプトは親ディレクトリを作るようになっていますが、手動で用意しておくとよいです）。

## 使い方（主要コマンド例）
- 監視ループを起動（ローカル）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - run_monitoring は Monitoring DB（sqlite）を初期化し、SystemMonitor を定期実行して system_status 等を記録します。
  - 停止: プロセスに KeyboardInterrupt を送るか、プロジェクトルート/data/stop_requested.flag ファイルを作成するとループが検知して終了します。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します。
  - 起動前に data/stop_requested.flag が存在する場合は起動をスキップします（安全措置）。
  - 停止: run_execution は stop flag（data/stop_requested.flag）を監視します。KillSwitch によって data/kill.flag が書き込まれると ExecutionEngine を停止するようトリガされます（KillSwitch は RiskMonitor などから条件で書き込まれます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能（デフォルト: data/paper_trading.db）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開くため read-only URI を使用します。MonitoringEngine が監視データを書き込んでいることが前提です。

- AI（ニューススコア / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None) — OPENAI_API_KEY が必要。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — OPENAI_API_KEY が必要。
  - これらは DuckDB 接続（prices_daily/raw_news 等が事前にロード済み）を受け取ります。

## 停止・フラグファイルの取り扱い
- stop_requested.flag
  - run_monitoring.py と run_execution.py が監視する停止フラグ（location: project_root/data/stop_requested.flag）。
  - 存在するとループ・エンジンは安全に終了します。
- kill.flag
  - KillSwitch が書き込むフラグ（Settings.kill_flag_path、デフォルト data/kill.flag）。
  - ExecutionEngine 側で kill.flag を検知するようになっている設計です（KillSwitch は RiskMonitor 等からの条件で作成する）。
  - KillSwitch は既存ファイルがある場合は再書き込みせず冪等です。clear() により削除可能。

## 設定と動作に関するメモ
- DB
  - monitoring 用 DB（SQLite）は init_monitoring_db() によってテーブル・インデックスを冪等に作成／マイグレーションします。
  - DuckDB は時系列価格や raw_financials などの大規模集計に使用します。パスは DUCKDB_PATH で指定。
- 環境選択
  - Settings.env により is_dev / is_paper / is_live を切り替え、Execution 等の挙動が変わります（paper_trading は専用 DB、MockBroker 等）。
- OpenAI
  - OpenAI を使う機能は API キーが必須。API 呼び出しはリトライ・フォールバック（失敗時は安全側の値）を備えています。
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼び出して優先度を上げようとします（プラットフォーム依存で失敗しても警告にとどまり継続）。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — Settings（環境変数/.env 読み込み）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — マクロ + MA によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ & MonitoringDB ラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注ワークフロー（OrderState 管理）
    - reconciler.py — 再起動時の突合・復旧
    - （その他 broker_factory, order_repository 等のモジュールが想定されます）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ （実行時に作成されることが多い）
    - monitoring.db（デフォルト） / paper_trading.db / kabusys.duckdb
    - execution.pid / stop_requested.flag / kill.flag

（上記はコードベースに現れる主要ファイル・モジュールの抜粋です。実装の詳細は各ファイルの docstring を参照してください。）

## 運用上の注意
- 実運用では API キーやパスワード類を安全に保管してください（環境変数やシークレット管理を使用）。
- paper_trading モードは本番口座とは完全に分離されていますが、設定ミスに備え複数のレイヤで保護（ENV チェック・別 DB パス等）してください。
- OpenAI 呼び出しはコストとレイテンシを伴うため、バッチ化と失敗時フォールバックが組み込まれています。API 制限や料金に注意してください。
- monitoring のログ・アラートは運用オペレーションの早期検知に有用です。閾値やクールダウンなどは運用状況に合わせて調整してください。

---

この README はコードベースの現状を反映しています。追加で以下のような情報が必要であれば教えてください：
- 実際に使用する requirements.txt の候補（依存一覧）
- 各モジュールの詳細な利用例（関数レベルの使い方）
- 運用チェックリスト / デプロイ手順（systemd / docker / k8s）