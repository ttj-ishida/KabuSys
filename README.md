# KabuSys

日本株向け自動売買システム（KabuSys） — 小規模なトレーディング実行、監視、リサーチ、AI支援モジュールを含むモノリポジトリ。

以下はリポジトリ内の主要スクリプト・モジュールの概要と、セットアップ / 実行方法の簡潔な説明です。

---

## プロジェクト概要

KabuSys は次の機能を持つ Python ベースの自動売買システムです。

- 注文発行・注文管理（ExecutionEngine）
- システム監視・リスク監視・Kill Switch（Monitoring）
- ポートフォリオ構築（候補選定、ウェイト計算、株数決定）
- ファクター計算・リサーチ（DuckDB を用いた時系列計算）
- ニュース NLP を用いた銘柄センチメント評価（OpenAI API）
- 市場レジーム判定（MA + マクロセンチメント）
- ペーパートレード用分離 DB と検証レポート生成ツール

設計方針として、本番 DB とペーパートレード DB を明確に分離し、リサーチ／AI モジュールは原則外部 API に依存せず DuckDB を用いる部分と、OpenAI を呼び出す部分（明示的な API キーが必要）に分かれています。

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV によって実運用 / ペーパートレードを切替。
  - プロセス優先度設定、pid ファイル管理、停止フラグ（data/stop_requested.flag）対応。
  - ペーパートレード時は MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）に記録。

- run_monitoring.py
  - SystemMonitor のポーリングループ（デフォルト 60 秒）を実行。
  - MONITOR_POLL_INTERVAL 環境変数で間隔変更可。
  - 監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を SQLite に永続化。

- monitoring/* モジュール
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / monitoring_db（マイグレーション含む）

- portfolio/*
  - 候補選定、等重・スコア重み付け、セクター制限、レジーム乗数、株数決定（単元株丸めや利用可能現金に基づくスケーリング）

- research/*
  - calc_momentum / calc_volatility / calc_value 等のファクター計算（DuckDB 接続を受ける純粋関数）
  - forward returns, IC 計算、統計サマリ等

- ai/*
  - news_nlp: raw_news から銘柄ごとに記事を集約し OpenAI に投げて ai_scores を書き込む
  - regime_detector: ETF 1321 の MA200 乖離 + マクロニュースセンチメントで日次レジーム判定

- tools/paper_verification_report.py
  - ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力

- util
  - logging_setup: 共通ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プラットフォーム差分を吸収したプロセス優先度設定ユーティリティ
  - config, config_setup, validate_config: 環境変数管理 / .env 作成ウィザード / 設定検証

---

## 必要条件

- Python 3.9+
- 推奨パッケージ（代表例 — 実行環境に応じてインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config.yaml 検証を使う場合)
- システムでは書き込み可能な data/ と logs/ が必要（logging_setup が自動作成を試みます）。

例（簡易）:
pip install duckdb psutil openai PyYAML

注意: requirements.txt は本コードスニペットに含まれていません。実際のパッケージはリポジトリ付属の要件ファイルに従ってください。

---

## 環境変数・設定（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルトを示す）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を使う場合必須
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60 秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（通常は 0。本番で 1 は危険）

注意:
- Monitoring の DB 接続（monitoring 用テーブル作成）は run_monitoring/run_execution 内で init_monitoring_db を呼んで行われます。
- run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番パス）を使う点に注意。

---

## セットアップ手順（例）

1. リポジトリをクローンして Python 仮想環境を作成:
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

3. .env を作成（対話式ウィザード）:
   - python -m kabusys.config_setup
   - あるいは手動で .env を作成し上記の必須値を設定

4. 設定を検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. data/ と logs/ ディレクトリを生成（通常は自動生成されますが、権限に注意）:
   - mkdir -p data logs

6. OpenAI を使う機能を利用する場合は OPENAI_API_KEY を環境変数または .env に設定。

---

## 実行方法（主要コマンド）

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録
    - 停止フラグ data/stop_requested.flag が存在すると起動中に停止します
    - PID ファイル: data/execution.pid（デフォルト、Settings.pid_file_path による）

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用してログを残します

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（ライブラリ API 呼び出し例）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を要求します（引数で渡しても可）。

ログ:
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ローテーション: 日次、30日分保管

停止・Kill Switch:
- KillSwitch はリスク条件（ドローダウン、ポジション上限等）により data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
- 手動停止: data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。

---

## 主要ディレクトリ構成

（ソースは src/kabusys 以下にある想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数の解決と Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    （※実装ファイルは本スニペットに含まれていませんが、Execution に関するコンポーネント群）

  - monitoring/
    - monitoring_db.py         — SQLite スキーマ作成 / 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py       — セクターキャップ / レジーム乗数
    - __init__.py

  - research/
    - factor_research.py       — Momentum / Value / Volatility 等
    - feature_exploration.py   — forward returns / IC / 統計サマリ等
    - __init__.py

  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント）
    - __init__.py

  - tools/
    - paper_verification_report.py

  - data/                      — 既定の data ファイル群（DB・flag 等。ランタイムで生成）
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード用)
    - kill.flag
    - stop_requested.flag
    - execution.pid

  - logs/                      — デフォルトログディレクトリ（logging_setup が作成）

---

## DB / マイグレーション

- monitoring_db.init_monitoring_db(conn) は冪等にテーブル・インデックスを作成します。
  - system_status, trade_logs, positions, risk_logs, dashboard を作成
  - 既存 DB に必要カラムがない場合は ALTER TABLE による追加マイグレーションを実行する箇所があります（例: dashboard.peak_value, trade_logs.latency_ms）。

- DuckDB は分析用途に使用（prices_daily / raw_financials / raw_news / ai_scores などのテーブルを前提）。

---

## 開発上の注意点・補足

- Production（KABUSYS_ENV=live）では LINE の通知設定や kill flag の取り扱い等を慎重に確認してください（validate_config は live 時に追加警告を出します）。
- run_monitoring は環境変数 MONITOR_POLL_INTERVAL に不正な値（0以下や整数でない文字列）が渡された場合にデフォルト 60 秒にフォールバックします。
- プロセス優先度設定（set_process_priority）は起動直後に呼ばれ、権限がなければ警告ログを出してスキップします。
- OpenAI 呼び出しはリトライ・バックオフを組み込んでいますが、API キーやレート制限には注意してください。AI モジュールは失敗時にフェイルセーフ（0や空の結果）で継続する設計です。
- portfolio / research の関数は副作用のない純粋関数設計を意識しており、テストが容易です。

---

README はここまでです。特定のモジュール（ExecutionEngine の設定項目、Broker 実装、TradeMonitor の詳細、テーブルスキーマの完全仕様など）について詳しい説明が必要であれば、その対象を指定してください。さらに実運用向けのデプロイ手順（systemd / supervisor / コンテナ化 / CI/CD）やセキュリティ（API キーの安全な管理）についても別途まとめます。