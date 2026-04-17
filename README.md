# KabuSys

日本株向けの自動売買 / 研究 / モニタリング用ライブラリ群と起動スクリプト群です。  
本リポジトリは、注文実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ユーティリティ、リサーチ・AI 支援モジュール等を含みます。

README には以下を記載します：
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・ツールの起動方法）
- ディレクトリ構成（主要ファイルの説明）
- 主要環境変数一覧（デフォルト / 備考）

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 注文の作成・送信・状態管理を行う ExecutionEngine（ブローカ抽象化を含む）
- システム稼働状況・注文・リスク監視を行う Monitoring 系（ログ永続化・アラート送信）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限など）
- リサーチ向けファクター計算（Momentum / Volatility / Value 等）
- ニュース NLP による銘柄単位のセンチメントスコア算出（OpenAI を利用）
- Paper Trading 用検証レポート生成ツールや Streamlit ダッシュボード

設計の特徴：
- DuckDB/SQLite をデータ層に利用（ローカルファイル）
- 明示的な環境切替（development / paper_trading / live）
- AI 呼び出しは失敗時に安全にフォールバックする実装（フェイルセーフ）
- .env ファイル自動読み込み機構（ただし無効化可能）

---

## 機能一覧（抜粋）

- Execution
  - 注文作成・送信・同期・再構築（Reconciler）
  - RiskManager（最大保有比率、利用率、ドローダウン等）
  - Paper Trading モード（MockBroker を使用し、本番 DB と分離）
- Monitoring
  - SystemMonitor：CPU/Mem/Disk、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文検出、価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限の検出とログ出力
  - KillSwitch：重大リスク時に flag ファイルを書き ExecutionEngine を停止
  - AlertManager：LINE Push による通知（クールダウン機能付き）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定、スコア重み付け、等金額配分、ポジションサイジング（lot 単位、集約キャップ等）
  - セクターキャップ、レジーム乗数
- Research / AI
  - DuckDB を用いたファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算
  - ニュース NLP による銘柄別スコアリング（OpenAI）
  - 市場レジーム判定（ETF の MA200 とマクロニュースの組合せ）

---

## セットアップ手順

前提：
- Python 3.9+（推奨）
- SQLite は Python 標準に同梱
- Git でソースをチェックアウトしていること

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または Windows では .venv\Scripts\activate

2. 依存パッケージの導入（主要パッケージ）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt が無い場合は上記を個別にインストールしてください）

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

4. 環境変数 / .env
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（注：OS 環境変数が優先されます）。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 必須の環境変数（最小構成）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（使用する場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実運用時）
   - OPENAI_API_KEY: OpenAI を利用する機能（news_nlp / regime_detector）を使う場合
   - KABUSYS_ENV: environment（development / paper_trading / live） — デフォルトは development

   よく使う変数のデフォルト（参考）：
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE=instant

---

## 主要スクリプトの使い方

以下はプロジェクトルートから実行する想定です。

1. 監視ループ（Monitoring）の起動
   - 目的: SystemMonitor（system_status 等）の定期ポーリングを実行
   - 実行:
     - python src/kabusys/run_monitoring.py
   - 設定:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
     - 監視は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します
   - 停止:
     - プロジェクトルートの data/stop_requested.flag を作成するとループは終了します（または Ctrl+C）

2. 注文実行エンジン（Execution）の起動
   - 目的: ExecutionEngine を起動して発注ループを開始
   - 実行:
     - python src/kabusys/run_execution.py
   - 設定:
     - KABUSYS_ENV=paper_trading を設定すると、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します
     - PID ファイル: data/execution.pid（デフォルト）を生成／参照します
   - 停止:
     - data/stop_requested.flag を作るとエンジンを停止します
     - また KillSwitch によって data/kill.flag が書き込まれると起動済みのエンジンに停止シグナルを送ります（現実装はファイル存在判定で停止）

3. Paper Trading 検証レポート（ツール）
   - 目的: Paper Trading DB（data/paper_trading.db）から期間指定で検証レポートを生成
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - --db オプションで DB パスを直接指定可能
   - レポートでは稼働率（uptime）、注文成功率、送信率、P95レイテンシ等を出力します

4. Streamlit ダッシュボード
   - 目的: 監視 DB を可視化
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 注意:
     - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してください。

5. AI 機能（ニュース NLP / レジーム判定）
   - 要件: OPENAI_API_KEY（環境変数または関数引数）
   - 関連関数:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 挙動:
     - OpenAI 呼び出し時はレート制限・ネットワーク障害等を考慮した指数バックオフでリトライし、最終的に失敗してもシステムは動作継続するようになっています（元データの消失を防ぐための設計）

---

## フラグ・ファイルについて（運用）

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループを優雅に終了させるためのファイル。作成されていると起動時にチェックされ、既にある場合は起動を行わない挙動も含む。

- data/kill.flag
  - KillSwitch（監視側）が発動した際に作成されるファイル。ExecutionEngine に対する緊急停止信号として使用します。
  - KillSwitch は drawdown 超過やポジション上限超過を検出した場合に理由を書き込みます。

- data/execution.pid
  - ExecutionEngine 起動時に PID を書き込むファイル。SystemMonitor はこのファイルを見て Execution プロセスの存否をチェックします。stale（古い）PID を検出するとファイルを削除してリスクイベントをログします。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV
  - 値: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用（必須にする処理がある箇所あり）
- KABU_API_PASSWORD
  - kabuステーション API 用（本番時）
- OPENAI_API_KEY
  - OpenAI を利用する場合に必須
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- MONITOR_POLL_INTERVAL (default: 60) — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動

注: Settings クラスは .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下のおもなモジュールと役割の一覧です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定読み込み（.env 自動ロード・Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- src/kabusys/execution/
  - order_manager.py — 注文作成・状態遷移の外向 API
  - reconciler.py — 起動時リコンシリエーション（ブローカー照合）
  - その他（broker_factory 等） — ブローカ抽象化・注文リポジトリ等（省略）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化（schema 定義・CRUD）
  - system_monitor.py — CPU/Mem/Disk、プロセス、生データ鮮度チェック
  - trade_monitor.py — 滞留注文・価格異常検出
  - risk_monitor.py — ドローダウン・ポジション上限検出
  - kill_switch.py — フラグファイルによる停止制御
  - alert_manager.py — LINE Push による通知
  - monitoring_engine.py — 各 Monitor の統合（テスト用 run_once / 本番用 run）
  - streamlit_dashboard.py — Streamlit を用いた可視化フロントエンド

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数計算・Aggregate cap 調整
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
  - __init__.py — エクスポート

- src/kabusys/ai/
  - news_nlp.py — raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロセンチメント）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading DB から検証レポート生成ツール

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意・ベストプラクティス

- 本番（live）実行時は KABUSYS_ENV=live を必ず設定し、KABU_API_PASSWORD 等の機密情報は環境変数で管理してください。
- Paper Trading は本番 DB と分離されますが、各 DB ファイルのパスを必ず確認してください（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API を使用する際は、レート制限や費用に注意してください。スコア生成はバッチで行われ、失敗時はフォールバック動作がありますが、API キーの漏洩は重大なので慎重に管理してください。
- データ鮮度チェックなどは DuckDB の prices_daily テーブルを参照します。データの投入フローが別にある場合は、監視側とデータ投入側で日付の整合性を確保してください。
- PID / flag 管理はファイルベースです。自動化ツール（systemd 等）と併用する場合はファイルの扱いに注意してください（権限や作成タイミングなど）。

---

## よくある操作コマンドまとめ

- 監視開始（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
- Execution 起動（Live）
  - KABUSYS_ENV=live python src/kabusys/run_execution.py
- 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 停止フラグ作成（手動で実行すると両ループが停止）
  - touch data/stop_requested.flag
- KillFlag を手動で作る（Execution を停止させたい緊急時）
  - echo "reason" > data/kill.flag

---

この README はローカル開発・検証・運用のための概要をまとめたものです。詳細な API、内部設計やドキュメント（例えば PortfolioConstruction.md, StrategyModel.md）が別にある場合はそちらを参照してください。必要であれば README を英語版に翻訳したり、具体的なデプロイ手順（systemd ユニットや Dockerfile）を追加できます。必要な情報を教えてください。