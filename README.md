# KabuSys

日本株向け自動売買システム（ライブラリ / バッチ実行プログラム群）

このリポジトリは、トレード実行エンジン、監視（Monitoring）機構、ポートフォリオ構築、リサーチ用ファクター計算、AI（ニュース NLP / レジーム判定）などを含む自動売買システムのコードベースです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine（発注・注文管理・リスク管理・約定調整） — run_execution.py で起動
- Monitoring（システム状態・注文状態・リスク監視・Kill Switch） — run_monitoring.py / monitoring_engine によるポーリング
- Portfolio（銘柄選定・重み計算・ポジションサイズ決定・リスク調整）
- Research（DuckDB を使ったファクター計算・特徴量解析）
- AI モジュール（ニュースセンチメント、レジーム判定。OpenAI を利用）
- CLI ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート 等）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定 等）

設計方針の要点:
- DuckDB / SQLite をデータ格納に利用し、分析と実行/監視を分離
- 環境変数（.env）による設定管理。`config_setup.py` で対話的に .env を作成可能
- Paper Trading と Live を明確に分離（paper_trading 用 DB を利用）
- AI 呼び出しはリトライ・バリデーション等の堅牢化（失敗時はフェイルセーフ）

---

## 機能一覧

- 実行系
  - 発注管理（OrderRepository / OrderManager）
  - リスク管理（RiskManager） — ポジション上限、ドローダウンなど
  - ExecutionEngine によるセッション実行・PID 管理・停止フラグ対応
  - Paper Trading モード（MockBrokerClient を使用し別 DB に記録）

- 監視系
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor：注文滞留や約定異常の検出（trade_logs テーブルを参照）
  - RiskMonitor：ダッシュボード値に基づくドローダウン・ポジション数監視
  - KillSwitch：条件で kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：各 Monitor の周期実行と AlertManager 連携

- ポートフォリオ関連（純粋関数群）
  - 銘柄選定（select_candidates）
  - 配分計算（等金額・スコア加重）
  - ポジションサイズ算出（単元丸め・最大投下額・aggregate cap）
  - セクターキャップ適用、レジーム乗数

- リサーチ / ファクター
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（Information Coefficient）や統計要約

- AI
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF ma200 とマクロニュースを使い市場レジーム判定（market_regime に保存）

- ツール
  - 設定ウィザード: python -m kabusys.config_setup（.env 作成）
  - 設定検証: python -m kabusys.validate_config（--strict オプションあり）
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提
- Python 3.10+
- Git リポジトリをクローン済み

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   推奨パッケージ:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML ファイルをチェックする場合）
   例:
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

3. .env の作成
   対話式ウィザードを用意しています:
   - python -m kabusys.config_setup
   これによりプロジェクトルートに `.env` が作成されます。必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主な環境変数（省略時のデフォルト）
   - KABUSYS_ENV: development | paper_trading | live  （default: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - PAPER_FILL_MODE: instant | partial | never | reject  （default: instant）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
   - LOG_LEVEL: INFO
   - LOG_DIR: logs/
   - KILL_FLAG_CLEAR_ON_START: 0 | 1

   注意: 自動読み込みはプロジェクトルートの .env / .env.local を参照します。テスト用途などで自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 本番確認モード: python -m kabusys.validate_config --strict

5. データディレクトリ作成（.env のパスがデフォルトの場合）
   - mkdir -p data logs

---

## 使い方

基本的にはパッケージエントリポイントを利用します。

- 実行エンジン（Execution）
  - 起動: python -m kabusys.run_execution
  - 停止: `data/stop_requested.flag` を作成すると起動中のエンジンが検知して停止します
  - Paper Trading モード: KABUSYS_ENV=paper_trading を設定すると MockBroker を利用し paper_trading.db に記録します

- 監視ループ（Monitoring）
  - 起動: python -m kabusys.run_monitoring
  - ポーリング間隔の上書き: 環境変数 MONITOR_POLL_INTERVAL（秒）で調整（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使います（監視ログは production DB に保存）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH

- AI / Research / Portfolio のライブラリ呼び出し例（Python REPL やスクリプト内）
  - Portfolio:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - Research:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.research import calc_momentum
    - calc_momentum(conn, date_obj)
  - AI（ニュース NLP）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")

- ログ
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）と stdout。

- Kill Switch / 停止フラグ
  - KillSwitch は監視結果に基づいて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側は起動時・ループ内でこのフラグをチェックします）。
  - `data/stop_requested.flag` は手動で作成してプロセスを停止させるために利用されます。

---

## 開発者向け注意点 / 実装メモ

- Python バージョン: typing で `|` を使っているため Python 3.10 以上が必要です。
- DuckDB / SQLite:
  - 分析用には DuckDB（`data/kabusys.duckdb`）、監視/履歴には SQLite（`data/monitoring.db`）を使用します。
  - init_monitoring_db() はマイグレーションも行い、存在しないカラムを追加します（冪等）。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を試みます。権限がない場合は警告が出ますが動作は継続します。
- AI 呼び出し:
  - OpenAI SDK を利用。API 呼び出しはリトライ・バリデーション処理が組み込まれています。
  - OpenAI API キーは環境変数 OPENAI_API_KEY、もしくは関数引数で渡してください。
- テスト・マックロジック:
  - モジュール内の API 呼び出し部分は簡単にモック可能（テスト用に呼び出し関数を patch して置換する設計）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- __version__ = "0.1.0"

トップレベル実行 / 設定関連
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI

サブパッケージ / モジュール
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status / trade_logs / risk_logs / positions / dashboard）
  - system_monitor.py
  - trade_monitor.py (※実装参照)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (※実装参照)
- execution/
  - execution_engine.py
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクト内で用いられるデータ / フラグ等
- data/monitoring.db （SQLite、監視ログ）
- data/paper_trading.db （Paper Trading 用 SQLite）
- data/kabusys.duckdb （DuckDB 分析 DB）
- data/execution.pid （ExecutionEngine の PID ファイル）
- data/stop_requested.flag （外部停止指示フラグ）
- data/kill.flag （Kill Switch が書き込む停止フラグ）
- logs/ （ログファイル配置、LOG_DIR で上書き可）

---

## よく使うコマンド例

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視エンジン起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 指定 DB: --db path/to/paper_trading.db

- ライブラリ関数を Python スクリプトから呼び出す例
  - from kabusys.portfolio import select_candidates
  - from kabusys.research import calc_momentum
  - from kabusys.ai import score_news

---

## サポート / 貢献

バグ報告や改善提案は Issue を作成してください。Pull Request を歓迎します。

---

以上が本コードベースの概要と導入・利用方法です。README に記載のない追加の操作や開発手順が必要であれば、該当する機能（例: ExecutionEngine の詳細設定、Broker の実装方法、テストモードの使い方など）に合わせて追記します。必要な箇所を教えてください。