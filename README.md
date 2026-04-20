# KabuSys — README（日本語）

これは日本株向けの自動売買 / 研究用コードベースです。  
本 README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

※ 本リポジトリのソースは src/kabusys/* 配下にあります。

---

## プロジェクト概要
KabuSys は日本株の自動売買・モニタリング・研究を目的としたモジュール群です。  
主に以下の用途を想定しています。

- 発注エンジン（ExecutionEngine）による実環境 / ペーパートレードの発注管理
- システム監視（Monitoring）とリスク監視（ドローダウン、ポジション上限など）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用ファクター計算（DuckDB を使ったファクター計算・IC計算等）
- ニュースの LLM ベース NLP によるセンチメントスコア算出（OpenAI）
- ペーパートレード結果の検証レポート生成ツール

設計方針としては「DB 操作は明示的に」「実行環境とペーパートレードの分離」「ルックアヘッドバイアス回避」などの注意が組み込まれています。

---

## 機能一覧（抜粋）
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV に応じて本番 or paper_trading）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 環境セットアップ / 検証
  - config_setup.py: .env を対話式で生成・更新するウィザード
  - validate_config.py: 環境変数 / config/*.yaml の検証 CLI
- モニタリング
  - monitoring_engine.py: System / Trade / Risk モニタを束ねるエンジン
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各種監視ロジック（DB 永続化を含む）
  - kill_switch.py: 条件で data/kill.flag を書き込み ExecutionEngine を止める
  - monitoring_db.py: SQLite ベースの監視テーブル定義と操作ユーティリティ
- Execution（発注系）
  - execution_engine, order_manager, risk_manager, reconciler, broker_factory など（発注フロー）
  - paper_trading では MockBrokerClient を使用し専用 DB に記録（PAPER_TRADING_SQLITE_PATH）
- ポートフォリオ構築
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py など（候補選定・重み計算・株数算出）
- 研究（research）
  - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ
- AI / NLP
  - ai/news_nlp.py: raw_news を LLM（OpenAI）に送って銘柄別センチメントを ai_scores に書き込む
  - ai/regime_detector.py: マクロ + ETF MA200 で市場レジーム判定を行い market_regime に書き込む
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を読み取り検証レポートを生成

---

## 必要条件（推奨）
- Python 3.10+
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - (オプション) PyYAML — validate_config で YAML 検証を行う場合
- 推奨: 仮想環境 (venv, poetry, pipenv など)

requirements の一例（手動で用意）:
- duckdb
- psutil
- openai
- PyYAML

---

## セットアップ手順（基本）
1. リポジトリをクローン、またはパッケージを展開
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env 作成（対話式推奨）
   - python -m kabusys.config_setup
     - .env に J-Quants トークン、kabu API パスワードなどを入力します
5. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります
6. 初期データディレクトリを作成（必要に応じて）
   - data/ ディレクトリや logs/ は自動作成されますが、権限に注意してください

---

## 主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- LOG_LEVEL (デフォルト: INFO)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (紙トレード用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading 時の Mock の fill モード: instant|partial|never|reject)
- OPENAI_API_KEY (AI モジュール利用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒, デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。0/1)

※ .env は絶対にリポジトリにコミットしないでください（config_setup に注意書き有り）。

---

## 使い方（主要コマンド・実行例）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor ポーリング）
  - 環境変数で間隔変更可: MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
  - 補足:
    - 監視は data/ にある stop_requested.flag を検知するとループを終了します
    - Monitoring は常に設定の sqlite_path を使用します（環境に依らず）

- 実行エンジン起動（ExecutionEngine）
  - 実行:
    - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
    - 起動前に data/stop_requested.flag があると起動せず終了します
    - 実行中は data/execution.pid に PID を出します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / LLM ベースの処理（プログラムから呼ぶ）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（duckdb.connect(...)）
    - target_date: date オブジェクト
    - api_key: None の場合は環境変数 OPENAI_API_KEY を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - OpenAI API の呼び出しは冪等性やリトライが組み込まれていますが API キーと課金に注意してください

- 停止 / Kill Switch
  - KillSwitch は条件が満たされると data/kill.flag を書き込みます（ExecutionEngine 停止トリガ）
  - 管理者が手動で停止する場合は data/stop_requested.flag を作成するとループを静かに終了できます

---

## ログ
- setup_logging() により:
  - stdout（StreamHandler）出力
  - 日次ローテートされるファイル出力: logs/<app_name>.log（デフォルト logs/）
- ログディレクトリやログレベルは環境変数 LOG_DIR / LOG_LEVEL で上書き可能

---

## データベース
- DuckDB: 分析用（デフォルト data/kabusys.duckdb）
- SQLite: 監視・発注履歴用（デフォルト data/monitoring.db）
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- monitoring_db.init_monitoring_db() でテーブルが冪等作成されます。既存 DB に対して軽微なマイグレーション（列追加）も行います。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主なファイルと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み、Settings クラスを提供
  - config_setup.py
    - .env を対話式で作るウィザード
  - validate_config.py
    - 起動前の設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py: ログ設定ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite テーブル定義・読み書きユーティリティ
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: 発注ログ監視（ファイルに含まれています）
    - risk_monitor.py: ドローダウン・ポジション上限チェック
    - kill_switch.py: kill.flag ロジック
    - monitoring_engine.py: 各モニタの束ね
    - alert_manager.py: 通知管理（LINE等、実装箇所あり）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - 発注フロー、ブローカラッパー、リスク制御等
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定、aggregate cap のスケーリング
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB を使用）
    - feature_exploration.py: 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py: ニュース → LLM センチメント → ai_scores へ書き込み
    - regime_detector.py: ETF MA200 + マクロ LLM でレジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成

---

## 開発・運用上の注意
- .env ファイルは絶対にリポジトリにコミットしないこと
- KABUSYS_ENV を "live" に設定する際は特に注意（validate_config は警告を出します）
- パーミッションやファイル所有権により logs/ や data/ の作成が失敗することがあるため、起動前にディレクトリ権限の確認を推奨
- OpenAI 呼び出しには API キーと課金が必要。ローカルテストではモック化を推奨
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）や kill.flag による制御を行うため、運用時は運用ガイドラインに従って手順を整備すること

---

## よく使うコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視開始: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README はコードベースの主要な使い方と構成をまとめたものです。実際の運用・カスタマイズ時は各モジュール内のドキュメント（関数の docstring）を参照してください。必要があれば README の補足（例: 詳細な設定例、運用手順、デバッグ方法）を追加します。