# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群のリポジトリです。  
この README は、プロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・監視・リサーチ機能を備えたシステムのコアコンポーネントです。  
主に次の役割を持つモジュールを含みます。

- ExecutionEngine：発注・リスク管理・注文再整合（実際のブローカー or モック）  
- Monitoring：プロセス/システム状態、注文・リスク監視、Kill Switch の評価  
- Portfolio：銘柄選定・重み計算・ポジションサイズ計算などのポートフォリオ構築ロジック  
- Research / AI：DuckDB 上のファクター計算・将来リターン解析、LLM を使ったニュース NLP / レジーム判定  
- Utils：ログ設定・プロセス優先度等のユーティリティ  
- CLI/ツール：環境設定ウィザード、設定検証、ペーパートレード検証レポート 等

注意：本リポジトリはライブラリ／サーバプロセスの実装を提供します。実際に本番口座に接続するには外部設定（環境変数・.env）とブローカークライアント構成が必要です。

---

## 機能一覧

- 環境設定管理（.env 自動読み込み / Settings クラス）
- 実行スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを分離）
  - run_monitoring.py：SystemMonitor をポーリングして監視ログを記録
- 監視機能
  - SystemMonitor：CPU/メモリ/ディスク・プロセスの生存確認・データ鮮度チェック
  - TradeMonitor：注文ログの異常検出（滞留注文、異常約定など） ※実装ファイルあり
  - RiskMonitor：ドローダウンやポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine 停止を促す
  - MonitoringDB：SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重・スコア重み、セクター上限適用、ポジションサイズ計算（単元株丸め、aggregate cap）
- リサーチ
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI（OpenAI）
  - news_nlp: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースを組み合わせた日次レジーム判定
- 開発ツール
  - config_setup.py：.env を対話式に生成・更新するウィザード
  - validate_config.py：起動前の設定検証（必須環境変数や config/*.yaml 確認）
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成

---

## セットアップ手順（開発環境）

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （任意）PyYAML があれば validate_config の YAML 検証が有効になります: pip install pyyaml
   - 実際のプロダクション要件に応じて他パッケージ（ブローカークライアント等）を追加してください
4. プロジェクトルートに `.env` を準備
   - 対話式に作成する場合: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - 自動ロード: .env はプロジェクトルート（.git または pyproject.toml を見て探します）。._env.local を使ってローカル上書き可能
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データディレクトリの準備（任意）
   - デフォルトの DB / PID / フラグファイルは `data/` 配下に置かれます（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
6. ログディレクトリ `logs/` は起動時に自動作成されます（権限がない場合はコンソール出力のみになります）

注記: init_monitoring_db が起動時に必要なテーブルを作成するため、事前の DB 初期化は不要です。

---

## 使い方

### 基本的な起動コマンド

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- ExecutionEngine（実行エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します
  - 起動直後に data/stop_requested.flag が存在すると起動せず終了します

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使います
  - 終了は data/stop_requested.flag の作成、または Ctrl+C（KeyboardInterrupt）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
  - 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ などを評価します

### 環境変数（主なもの）

- 必須（validate_config でもチェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行制御 / 環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動読み込みを無効化

- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（ExecutionEngine の pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（KillSwitch が書き込む flag、デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動でクリア（本番では 0 推奨）

- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
  - PAPER_FILL_MODE: paper_trading 時の Mock ブローカーの fill モード（instant|partial|never|reject）
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で使用

### ログとフラグ操作

- ログ
  - setup_logging により stdout に加え logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/）
- 停止フラグ
  - run_execution/run_monitoring は `data/stop_requested.flag` を検知して安全停止します
  - KillSwitch は条件が満たされると `Settings.kill_flag_path`（デフォルト data/kill.flag）に理由を記述して ExecutionEngine の停止を促します
  - kill.flag の自動クリア設定は KILL_FLAG_CLEAR_ON_START（本番は 0 を推奨）

### 開発者向け（関数 API の利用例）

- AI スコアリング（programmatic）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=...)

- リサーチ関数（DuckDB 接続を渡して使用）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - results = calc_momentum(duckdb_conn, date(2026, 4, 1))

---

## よく使うファイル・エントリポイント（参考）

- python -m kabusys.config_setup
- python -m kabusys.validate_config [--strict]
- python -m kabusys.run_execution
- python -m kabusys.run_monitoring
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings クラス、.env 自動読み込み
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py        — レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py          — SQLite 永続化層（テーブル作成・簡易 CRUD）
  - system_monitor.py         — システム状態・データ鮮度監視
  - trade_monitor.py          — 注文関連監視（滞留・約定異常 等）
  - risk_monitor.py           — ドローダウン / ポジション上限監視
  - kill_switch.py            — Kill Switch（flag 書き込み）
  - monitoring_engine.py      — 各 Monitor の統合ポーリング
  - alert_manager.py          — アラート管理（LINE等へ送信する想定）
- execution/
  - execution_engine.py       — 実行エンジン本体
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py          — 共通ログ設定
  - process_priority.py       — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py
- data/                       — 実行時に使われる DB / フラグ / pid（git に含めないこと）

（※一部ファイルは抜粋です。詳細はリポジトリの src/kabusys 以下を参照してください）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定（特に KILL_FLAG_CLEAR_ON_START、LINE 通知周り）を慎重にしてください。validate_config は本番用の注意喚起を出します。
- .env は機密情報を含みます。決して Git にコミットしないでください（config_setup でもその旨を記載しています）。
- OpenAI API を利用する機能は API キーとコストが必要です。エラーハンドリングが入っていますが、使用時はレート制限やコストに留意してください。
- DuckDB / SQLite のファイルは適切なバックアップ・パーミッションで管理してください。

---

必要に応じて README を拡張します。特定の機能（ExecutionEngine の詳細設定、Broker 実装方法、monitoring/trade monitor の具体的な挙動など）について詳しいドキュメントを追加したい場合は、対象箇所を指定してください。