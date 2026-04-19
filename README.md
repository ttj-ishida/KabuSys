# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、AI（ニュースセンチメント／レジーム判定）、ポートフォリオ構築ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な役割は以下のとおりです。

- 発注処理（ExecutionEngine） — ブローカークライアントを介して注文管理・リスク管理を行う。
- 監視（Monitoring） — システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェックし、必要なら Kill Switch を作動させる。
- リサーチ（Research） — DuckDB 上の価格・財務データからファクター（モメンタム、バリュー、ボラティリティ等）と指標を計算する。
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ算出、セクターキャップ等の純粋関数群。
- AI（news_nlp / regime_detector） — OpenAI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI API 必須）。
- 運用ユーティリティ — .env 設定ウィザード、設定検証ツール、ペーパートレード検証レポート等。

設計上のポイント：
- 設定は環境変数（.env）で管理。`.env` 自動読み込み機能あり（必要に応じて無効化可）。
- Paper trading と Live は DB を分離（paper_trading 環境用 DB は data/paper_trading.db）。
- ロギングは統一された setup_logging を使用し、コンソール＋日次ローテートファイル出力を行う。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 設定管理
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定の事前チェック CLI
- 監視関連
  - monitoring_db.py — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager（アラート管理）
- Execution（発注）
  - broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager
- リサーチ
  - research.factor_research — momentum/volatility/value の計算（DuckDB）
  - research.feature_exploration — 将来リターン・IC・統計サマリ
- ポートフォリオ
  - portfolio_builder, position_sizing, risk_adjustment（純関数, テスト容易）
- AI
  - ai.news_nlp — ニュース記事を OpenAI で評価し ai_scores に書込む
  - ai.regime_detector — MA とマクロセンチメントを組み合わせて日次レジーム判定
- ツール
  - tools.paper_verification_report — Paper Trading の検証レポート生成

---

## 必要条件（推奨）

- Python 3.9+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- システム上でプロセス優先度を変更する場合、適切な権限が必要になることがあります（set_process_priority）。

※ requirements.txt はリポジトリに含まれていないため、ご自身の環境に合わせて依存関係を用意してください。

例：
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリを取得
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数設定（.env）
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 任意: KABUSYS_ENV（development / paper_trading / live）, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI を使う場合）など
   - 自動ロードは通常有効。テストで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - エラーがある場合は修正してください。`--strict` を付けると警告も失敗扱いになります。

6. データディレクトリ
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
   - 必要に応じて `.env` の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

---

## 使い方

### 実行（ExecutionEngine）

- 本番または paper_trading の起動:
  - KABUSYS_ENV=paper_trading を使うと MockBrokerClient が使用され、発注は data/paper_trading.db に記録されます（本番 DB と分離）。
- 起動コマンド:
  - python -m kabusys.run_execution
- 停止方法:
  - run_execution はバックグラウンドスレッドで ExecutionEngine を動かします。停止は `data/stop_requested.flag` の作成（監視プロセス・運用手順に依存）やプロセスを SIGINT（Ctrl+C）で終了するなど。

注意:
- 起動時にプロセス優先度を "high" に変更しようとします（set_process_priority）。権限により失敗することがありますが、警告としてスキップされます。
- 実行中は pid ファイル（data/execution.pid）が利用されます。

### 監視（Monitoring）

- SystemMonitor のポーリングループを起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
- 監視は常に本番 sqlite_path を使用（環境にかかわらず monitoring 用 DB を参照）。
- 停止フラグ:
  - プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。
  - Kill Switch (`data/kill.flag`) は ExecutionEngine 停止トリガーとして使用されます。

### 設定ウィザード / 検証

- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 検証:
  - python -m kabusys.validate_config
  - `--strict` を付けると警告もエラー扱いになります。

### Paper Trading 検証レポート

- ツール:
  - python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
- デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

### AI（ニュース評価 / レジーム）

- OpenAI API を利用するため `OPENAI_API_KEY` を環境変数に設定するか、呼び出し関数にキーを渡してください。
- プログラム的に呼ぶ例:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

AI 呼び出し時の注意:
- API の失敗（429, タイムアウト, 5xx 等）はリトライやフェイルセーフ処理が組み込まれていますが、API キー未設定の場合は例外が発生します。
- レスポンスは厳密な JSON を期待するよう設計されていますが、復元ロジックもあります。

### ライブラリとしての利用例（Research / Portfolio）

- Research:
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary
  - いずれも DuckDB の接続オブジェクトと日付を渡して使用します。
- Portfolio:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - 純粋関数群なのでテスト・組み合わせが容易です。

---

## 主要ファイル / ディレクトリ構成

（リポジトリの `src/kabusys` を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する場合)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルート（想定）
- data/                      — データファイル（DB・フラグファイル等）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/                      — ログファイル（例: logs/execution.log）
- config/                    — yaml 設定ファイル群（system_config.yaml 等）
- src/                       — パッケージ実装

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV (development / paper_trading / live)
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (本番での自動クリア抑止設定)

---

## 運用上の注意 / トラブルシューティング

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブル・列の存在チェックと簡易マイグレーション（カラム追加）を行います。直接 DB を壊さないよう保守に注意してください。
- 権限:
  - process priority の設定やファイル書き込み（data/、logs/）に対する権限が必要です。必要に応じてパーミッションを確認してください。
- AI/外部 API:
  - OpenAI 呼び出しはネットワークに依存し、レート制限が発生する可能性があります。API キーの管理と課金に注意してください。
- 本番運用:
  - KABUSYS_ENV=live の場合は特に Kill Switch や LINE 通知設定を確認してください。validate_config.py は本番向けチェック（警告）を出します。
- ログ:
  - logs/<app>.log に日次ローテートで保管されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。

---

## サンプルコマンド一覧

- .env ウィザード：
  - python -m kabusys.config_setup
- 設定検証：
  - python -m kabusys.validate_config
- Execution 起動：
  - python -m kabusys.run_execution
- Monitoring 起動：
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

README に記載のない個別 API（内部ユーティリティ、Engine の詳細等）はコード内の docstring を参照してください。必要であれば起動例や contrib スクリプトの追加ドキュメント化を行います。