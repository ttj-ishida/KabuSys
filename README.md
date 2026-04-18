# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツール・AI を組み合わせた自動売買基盤の一部を実装しています。設計は本番/ペーパートレードを明確に分離し、監視・Kill Switch による安全弁やログ/DB による可観測性を重視しています。

## 主な機能一覧
- 環境設定管理
  - `.env` 自動読み込み / 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン（ExecutionEngine 起動スクリプト）
  - 本番 / ペーパートレード分離（paper_trading 時は MockBrokerClient を使用）
  - 発注・注文管理・リスク管理・リコンシリエーション
- 監視（Monitoring）
  - System / Trade / Risk モニタを束ねる MonitoringEngine
  - Kill Switch（条件を満たすと `data/kill.flag` を生成して ExecutionEngine を停止）
  - 監視ログ永続化（SQLite）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額 / スコア加重）
  - セクター集中制限、レジーム乗数、ポジションサイズ計算（単元株丸め等）
- 研究用モジュール（DuckDB 経由）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン / IC 計算 / 統計サマリー
- AI 関連
  - ニュースに対する LLM（OpenAI）を使ったセンチメントスコアリング（news_nlp）
  - マクロ + ETF MA200 を用いた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - ログ設定（stdout + 日次ファイルローテーション）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提:
- Python 3.9+（typing / 型ヒントに合わせて推奨）
- SQLite は標準ライブラリで利用
- OS により psutil が特権操作を必要とする場合があります

1. リポジトリをクローン / ワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境（推奨）を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須パッケージ（最低限）:
     - duckdb
     - psutil
     - openai
   - 便利/任意:
     - PyYAML（config/*.yaml の検証に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合は上記を個別インストールしてください）

4. 環境変数の準備（.env）
   - 対話式ウィザードで初期作成:
     - python -m kabusys.config_setup
   - または `.env` を手動で作成する（`.env.example` があれば参照）
   - 必須環境変数（少なくとも設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（省略可・デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能利用時に必須
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）※ run_monitoring 用（デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトは data 以下）
   - 補足:
     - 自動.envロードはデフォルトで有効（プロジェクトルートに .env/.env.local がある場合）
     - テスト用途など自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データディレクトリ作成（必要に応じて）
   - data/ と logs/ は自動作成されることが多いですが、権限等で失敗する場合があります。
   - 例: mkdir -p data logs

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

---

## 使い方（主要スクリプト）

注: 各スクリプトはパッケージモジュールとして起動できます（推奨）。

- 実行エンジン（ExecutionEngine 起動）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動時に data/stop_requested.flag が存在すれば起動を中止します。
    - 実行中、data/stop_requested.flag を作成するとエンジンは停止します。
    - 実行中は PID ファイル（デフォルト data/execution.pid）を作成します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 動作:
    - 監視ループを定期的に回して system/trade/risk のチェックを行います。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
    - 監視用の SQLite は環境にかかわらず Settings.sqlite_path（本番 DB）を使用します（意図的）。
    - `data/stop_requested.flag` を検知するとループを終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成 / 更新します。

- 設定検証 CLI
  - python -m kabusys.validate_config
  - 起動前に設定の不備や警告を検出します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率・成功率・P95 レイテンシ等）を集計し PASS/FAIL を出力します。

- AI 関連機能（関数 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルに書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡して market_regime テーブルへ書き込みます。

---

## 運用上の注意 / ファイル・フラグ
- kill.flag（Settings.kill_flag_path / デフォルト: data/kill.flag）
  - KillSwitch により条件を満たすと作成されます。ExecutionEngine はこのフラグにより停止します。
- stop_requested.flag（data/stop_requested.flag）
  - run_execution/run_monitoring はこのファイルの存在を監視し、存在時には起動中ループを止めます（手動停止等に利用）。
- PID ファイル（data/execution.pid 等）
  - 実行スクリプトは起動時に PID ファイルを作成します。
- ログ
  - デフォルトは logs/ ディレクトリにアプリ名別に出力（例: logs/execution.log, logs/monitoring.log）。
  - stdout（console）にも出力されます。

---

## 開発者向け情報: 主要モジュールとディレクトリ構成

以下は主要ファイル / モジュールの概要です（src/kabusys 以下）。

- run_monitoring.py
  - SystemMonitor を使ったポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可能。

- run_execution.py
  - ExecutionEngine を起動するスクリプト。paper_trading 時は専用 DB を使用。

- config.py
  - Settings クラス。環境変数の読み込み・検証・デフォルト管理を提供。
  - 自動的にプロジェクトルートの .env / .env.local を読み込む（無効化可）。

- config_setup.py
  - `.env` を対話式で生成・更新するウィザード。

- validate_config.py
  - .env や config/*.yaml の内容を検証する CLI。

- utils/
  - logging_setup.py: ルートロガーの標準化（stdout + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite を使った監視ログ永続化層（テーブル作成・マイグレーション含む）
  - system_monitor.py: CPU/MEM/DISK・データ鮮度・実行プロセス生存監視
  - trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py など（監視・アラート・Kill Switch ロジック）
    - （注）この README に掲載されていない一部ファイルはコードベースに依存します。

- execution/
  - ExecutionEngine、OrderManager、OrderRepository、BrokerClientFactory、RiskManager、Reconciler など（発注ロジック・リスク制御）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定・リスク制限・単元丸め
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum/Volatility/Value 計算（DuckDB）
  - feature_exploration.py: 前方リターン・IC・統計サマリー

- ai/
  - news_nlp.py: ニュースを LLM でスコアリングし ai_scores に書き込む
  - regime_detector.py: ETF MA200 + LLM マクロセンチメントで市場レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート出力ツール

- data/、logs/
  - 実行時に使用する SQLite / DuckDB ファイル、フラグ、PID、ログ等を格納（デフォルトパス）

---

## よくある質問 / ヒント
- ペーパートレード時の DB 分離
  - KABUSYS_ENV=paper_trading をセットすると run_execution は PAPER_TRADING_SQLITE_PATH を使い、本番監視 DB と完全に分離されます。実際の取引 API 代わりに MockBrokerClient が使用されます。

- 監視と実行の分離
  - run_monitoring は監視用 SQLite（Settings.sqlite_path）に常に接続します（環境にかかわらず本番監視 DB を対象にする設計意図あり）。監視が実行プロセスの停止や異常を検知して kill.flag を書くことで ExecutionEngine を保護します。

- OpenAI API キー
  - AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。テストではこれら呼び出し関数をモックできます（ユニットテスト向けの設計あり）。

- ログディレクトリ作成に失敗した場合
  - logging_setup はログディレクトリ作成失敗時にファイルハンドラをスキップして stdout のみで継続します。権限に注意してください。

---

## 実行例（まとめ）
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper 検証レポート（例）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

ライセンスやより詳しい設計（PortfolioConstruction.md / StrategyModel.md 等）はリポジトリ内のドキュメントを参照してください。必要であれば、インストール用 requirements.txt の作成・Dockerfile 化・systemd ユニットファイルなどの運用ドキュメントも作成できます。必要な形式（Markdown の追加構成、サンプル .env、systemd ユニット例など）があれば教えてください。