# KabuSys

日本株向け自動売買システムのコードベース（読み取り専用ドキュメント）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買や研究（ファクター計算・特徴量解析）、監視、ペーパートレード検証、AI ベースのニュースセンチメント評価などの機能を備えたシステムです。  
構成は以下のような責務分離を意識しており、DB（DuckDB / SQLite）、発注ブローカー、監視・アラート、ポートフォリオ構築、研究（research）、AI（OpenAI を使用）などがモジュール化されています。

主な特徴：
- 実運用（live） / ペーパートレード（paper_trading） / 開発（development）を環境で切り替え
- DuckDB を用いた分析用データ格納（prices_daily / raw_financials 等）
- SQLite による監視ログ（monitoring.db）
- ExecutionEngine による発注管理（paper_trading 時は MockBroker を利用）
- 監視エンジン（System / Trade / Risk）と Kill Switch（異常時の停止）
- ニュースを LLM（OpenAI）で評価する AI モジュール（news_nlp / regime_detector）
- Portfolio 関連の純粋関数（候補選定・重み付け・ポジションサイズ計算）
- 設定ウィザード / 設定検証 CLI、レポート生成ツール

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの `.env`, `.env.local`）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config

- 実行 & 監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - ポーリングで SystemMonitor.check_once を実行（MONITOR_POLL_INTERVAL で間隔変更可能）
  - 停止フラグ: `data/stop_requested.flag`（このファイルを作成するとループが終了）
  - Kill Switch: `data/kill.flag` を作成して ExecutionEngine を停止（監視モジュールが評価して書き込む）

- 監視
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID ファイル、データ鮮度をチェック
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション数制限の監視
  - MonitoringDB: SQLite（monitoring.db）へのログ永続化

- ポートフォリオ構築（純粋関数）
  - 候補選定・スコア順ソート（select_candidates）
  - 等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes: risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュースセンチメントスコア生成（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API による JSON レスポンス処理、リトライ・バックオフ実装

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
    - 期間指定オプションあり (`--from`, `--to`)。デフォルト DB は `data/paper_trading.db`

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements ファイルがない場合は、少なくとも以下をインストールしてください：
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML — config/*.yaml 検証時に利用
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の準備（推奨: ウィザードで作成）
   - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに `.env` を作成
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - KABUSYS_ENV=development  # development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...

   注意: 自動読み込みはデフォルトで有効。自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループは終了します

- 実行（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に発注ログを記録して本番 DB と分離
  - 実行中の停止: data/stop_requested.flag を作成すると安全停止します
  - Execution エンジンの PID ファイル: data/execution.pid（デフォルト）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 系（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - モジュール関数をプログラムから呼び出して利用（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）

---

## 重要な運用メモ

- 環境（KABUSYS_ENV）:
  - development / paper_trading / live のいずれか。`Settings.env` にて検証されます。
  - live は本番のため設定（LINE 通知や kill フラグ設定など）を慎重に行ってください。

- DB の扱い:
  - DuckDB: デフォルト `data/kabusys.duckdb`（分析用）
  - SQLite（監視）: デフォルト `data/monitoring.db`
  - Paper trading 用 SQLite: デフォルト `data/paper_trading.db`（paper_trading 時のみ使用）

- ログ:
  - ログは標準出力とファイル（logs/<app_name>.log）に出力されます
  - LOG_DIR と LOG_LEVEL で設定可能（環境変数または setup_logging の引数）
  - ローテーションは日次、30 日保持

- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び、可能であれば高優先度で実行します（OS に依存）

- 停止・キルスイッチ:
  - `data/stop_requested.flag`: run_monitoring / run_execution はこのファイル検出で安全終了
  - `data/kill.flag`: KillSwitch が条件を満たすと作成され、ExecutionEngine 停止のトリガーになります
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動でクリア（本番では推奨しない）

- OpenAI 使用:
  - API 呼び出しにはコストとレイテンシが伴います。API キーの取り扱いに注意してください
  - ニュース NLP / レジーム判定はレスポンスのバリデーションとリトライを実装しているが、外部 API に依存するため失敗を想定したフォールバックがあります

---

## ディレクトリ構成（主要部分）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動ロード）
- config_setup.py          — 対話式 .env 作成ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースセンチメント生成（OpenAI）
  - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化・書き込みラッパ
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度・PID チェック
  - trade_monitor.py       — （注文監視ロジック）
  - risk_monitor.py        — ドローダウン・ポジション数監視
  - kill_switch.py         — Kill Switch 実装（kill.flag）
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — （アラート送信ロジック）
- execution/
  - execution_engine.py    — ExecutionEngine（発注セッション管理）
  - broker_factory.py      — Broker クライアント生成（Mock / 実ブローカ）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py       — 統一的ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

（上記以外に data/、logs/、config/ 配下の YAML などが想定されます）

---

## よくある操作例

- 監視を 30 秒間隔で実行:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレードで Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート（2026-04-01 から 2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 設定の自動検証（厳密モード）:
  - python -m kabusys.validate_config --strict

---

## 注意事項 / 推奨

- .env は決してリポジトリにコミットしないでください（機密情報が含まれます）。
- 本番環境（KABUSYS_ENV=live）では必ず設定検証を行い、LINE 通知や kill flag の扱いを慎重に設定してください。
- OpenAI API を利用する機能は API キーとコストを考慮して運用してください。
- SQLite / DuckDB のファイルパスは環境変数で変更可能。バックアップ・権限管理を忘れずに。

---

## 貢献 / 拡張案（簡単に）

- Broker クライアントの追加（実口座接続や別インターフェース）
- 単元株数を銘柄ごとに管理（現状は共通の lot_size）
- より詳細なモニタリング用メトリクス（Prometheus 等へのエクスポート）
- 単体テスト・CI の整備（現在はスクリプトベースでの検証が中心）

---

質問があれば、この README を更新して補足できます。README に含めたい追加情報（例: 実行時のログサンプル、詳細な DB スキーマ、er 図など）があれば教えてください。