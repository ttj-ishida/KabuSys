# KabuSys

日本株向け自動売買システムのパイロット実装（ライブラリ / 起動スクリプト群）。

この README はリポジトリ内の主要なモジュール・スクリプトに基づいて、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買基盤の構成要素を提供します。

- システム監視（SystemMonitor / MonitoringEngine）
- 注文実行（ExecutionEngine と OrderManager 等）
- リスク監視（ドローダウン・ポジション上限監視）
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- リサーチ・ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュース NLP による AI スコアリング（OpenAI 利用）
- ペーパートレード用検証レポート生成ツール

設計方針の一部:
- データ永続化は DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- Paper Trading は本番 DB と分離（専用 SQLite）
- 環境変数 / .env による設定管理（自動ロード機能あり）
- OpenAI を利用する AI 機能は API キー必須、失敗時はフォールバック（フェイルセーフ）

---

## 主な機能一覧

- 起動スクリプト
  - run_monitoring.py: SystemMonitor を定期実行して system_status 等を記録
    - 環境変数: `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
    - 監視は常に本番 SQLite パス（Settings.sqlite_path）を使用
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により挙動切替）
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、`data/paper_trading.db` に記録
    - 停止フラグファイルによる停止制御（data/stop_requested.flag）
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新
  - validate_config.py: .env / config/*.yaml の事前検証 CLI（--strict オプションあり）
  - 自動 .env ロード: プロジェクトルート (.git または pyproject.toml が基準) が見つかれば自動で `.env` → `.env.local` を読み込み（OS 環境変数は保護）。無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 監視 / Kill Switch
  - MonitoringDB: SQLite に監視ログ・トレードログ等を永続化
  - MonitoringEngine: 各 Monitor（System/Trade/Risk）を束ねてポーリング、アラート送信、kill.flag 書き込み判定
  - KillSwitch: `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送出
- ポートフォリオ構築
  - 候補選定 select_candidates、等金額/スコア加重重み付け、ポジションサイズ算出（lot 単位の丸め、aggregate cap）
  - セクター上限適用、レジーム乗数の算出
- リサーチ（DuckDB ベース）
  - ファクター計算: momentum, volatility, value（prices_daily / raw_financials を参照）
  - 将来リターン、IC 計算、ファクター統計
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルに保存
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースの LLM センチメントから市場レジーム判定を行い market_regime テーブルへ保存
- ツール
  - tools.paper_verification_report: Paper Trading 用の稼働・注文成功率・レイテンシ等の検証レポート生成

---

## 必須/推奨環境変数

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- OPENAI_API_KEY: OpenAI を利用する機能を使う場合に必須
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）

その他:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）

注意:
- .env は絶対にリポジトリにコミットしないこと（config_setup は生成時に注意書きを出します）。

---

## セットアップ手順（開発向け）

1. Python 要件
   - Python 3.10+ を推奨（型注釈での Union 表記等を利用）
2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 依存パッケージのインストール（代表的なもの）
   - pip install duckdb psutil openai
   - OpenAI と YAML 検証を使う場合: pip install PyYAML
   - 実プロダクションで使用するパッケージは requirements.txt を用意している場合はそれを使ってください（本リポジトリ内にない場合は上記を参考にしてください）
4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（下記にサンプルを示します）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗にする場合: python -m kabusys.validate_config --strict
6. 初期データディレクトリの作成（必要に応じて）
   - mkdir -p data logs

サンプル .env（例）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（主要コマンド）

リポジトリをパッケージとしてインポート可能な状態にした上で、モジュールを -m で実行します。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（warning を fail とする）: python -m kabusys.validate_config --strict

- 監視ループ（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: Ctrl+C またはプロジェクトルートの data/stop_requested.flag を作成するとループは検知して終了します

- Execution エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 SQLite に記録（PAPER_TRADING_SQLITE_PATH）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - Execution の PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（ライブラリ関数経由で呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して指定日分のニュースをスコア化し ai_scores に書き込み
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime にレジーム判定を保存

ログ:
- setup_logging により stdout と 日次ローテートされたファイル（logs/<app_name>.log）へ出力

停止 / Kill:
- KillSwitch は `data/kill.flag` を書くことで ExecutionEngine に停止を促します
- 実行中の ExecutionEngine は `data/stop_requested.flag` を検知して停止します

注意:
- OpenAI を利用する処理は API キーが必須です。利用時は `OPENAI_API_KEY` を .env に設定してください。

---

## ディレクトリ構成（抜粋）

リポジトリは package `kabusys`（src/kabusys）配下に主要モジュールを持ちます。主要ファイル・モジュールの説明付きツリー:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 設定チェック CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - utils/
    - logging_setup.py
      - 統一的なログ設定（stdout + 日次ローテーション）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite への監視ログ永続化層
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/プロセス存在の監視
    - trade_monitor.py
      - （トレード監視ロジック: 滞留注文・約定異常等の検出）※実装あり
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - kill.flag の作成 / クリア
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - alert_manager.py
      - LINE などへの通知（実装箇所）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
      - 注文実行 / リスク管理 / ブローカラッパー 等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - ポートフォリオ構築ロジック（純粋関数群）
  - research/
    - factor_research.py
    - feature_exploration.py
    - DuckDB ベースのファクター・統計計算
  - ai/
    - news_nlp.py
      - raw_news を OpenAI に投げて銘柄別スコアを生成
    - regime_detector.py
      - 市場レジーム判定（MA200 + マクロ LLM センチメント）
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成ツール
  - data/（実行時に生成される想定）
    - monitoring.db（SQLite デフォルト）
    - kabusys.duckdb（DuckDB デフォルト）
    - paper_trading.db（Paper Trading 用 SQLite）
    - execution.pid, kill.flag, stop_requested.flag など

---

## 運用時の注意点

- KABUSYS_ENV が `live` のときは本番挙動になります。設定や通知先（LINE トークン／ユーザ）を慎重に確認してください。
- 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨します（自動クリアを防ぐ）。
- Paper Trading は本番 DB と完全分離されます（paper_sqlite_path を使用）。
- OpenAI 呼び出しは失敗時にフォールバック策がある（例: macro_sentiment=0）ものの、API 利用料や遅延を考慮して運用してください。
- ログディレクトリ作成に失敗した場合はコンソールのみの出力にフォールバックします。
- process priority / cpu affinity の設定は OS 権限に依存します。AccessDenied が出る可能性がありますがログに警告が出てスキップされます。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視開始: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行開始: python -m kabusys.run_execution
- ペーパーレポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はソースコードの主要な部分に基づいて作成しています。実際の運用にあたっては、config/*.yaml や各コンポーネントの実装（ExecutionEngine や Broker の具体実装）を確認し、適切なテスト・検証を行ってください。必要であれば README を拡張してデプロイ手順、監視ダッシュボード、バックアップ手順などを追記できます。