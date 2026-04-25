KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは以下の主要機能を持つコンポーネント群で構成されています。

- ExecutionEngine（発注エンジン）: 実際の発注またはペーパートレード（モック）で注文を実行
- Monitoring（監視）: システム状態・注文状態・リスク監視、Kill Switch による自動停止
- Portfolio（銘柄選定・配分・株数決定）: 候補選定、重み付け、ポジションサイズ計算
- Research（ファクター計算・特徴量解析）: DuckDB を使ったファクター算出・IC 計算等
- AI（ニュース NLP / レジーム判定）: OpenAI を利用したニュースセンチメント評価と市場レジーム判定
- Tools（紙トレ検証レポート等）: Paper Trading の検証レポート生成など
- Utilities: ログ設定、プロセス優先度設定、環境設定ウィザード等

目標は「本番にも耐えうる設計の実装例」を示すことであり、設定や DB を分離しペーパートレードとの混在を避ける設計になっています。

主な機能一覧
-------------
- 実行環境の分離
  - KABUSYS_ENV によるモード切替: development / paper_trading / live
  - paper_trading 時は MockBrokerClient を採用し、paper_trading 用 DB を使用
- 監視・アラート
  - SystemMonitor: CPU/メモリ/ディスク、プロセス稼働、データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文の滞留、約定異常、ドローダウンや保有銘柄上限の監視
  - KillSwitch: 指定閾値超過時に kill.flag を書き込みエンジン停止を促す
- 発注・リスク管理
  - OrderManager / RiskManager / Reconciler（実装箇所は別ファイル群に依存）
- ポートフォリオ構築
  - 候補選定（スコア降順）、等ウェイト / スコア重み / リスクベース配分
  - セクターキャップ、レジーム乗数、単元株丸め、aggregate cap のスケーリング
- リサーチ機能
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI 統合（OpenAI）
  - ニュースを LLM（gpt-4o-mini など）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA を合成した市場レジーム判定
- 運用支援ツール
  - .env 対話式生成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト

前提 / 必要な依存
-----------------
- Python 3.10+
  - typing の | 演算子などを使用しているため 3.10 以上を推奨します
- 推奨パッケージ（最低限）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の構文チェックを有効にする場合。必須ではない）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

セットアップ手順
----------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb psutil openai pyyaml
   - 必要に応じてプロジェクトに requirements.txt を追加して pip install -r で管理してください。

3. 環境変数 (.env) の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成された .env に機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を設定すること。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict を付ける

5. 初回起動前の準備
   - data/ ディレクトリや logs/ は自動作成されます（ログ出力時やフラグ書き込み時）。
   - paper_trading モードでテストする場合は KABUSYS_ENV=paper_trading と指定してください。
   - Paper Trading 用 DB のデフォルトは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
   - 監視用 SQLite のデフォルトは data/monitoring.db（SQLITE_PATH で変更可）
   - DuckDB のデフォルトは data/kabusys.duckdb（DUCKDB_PATH で変更可）

使い方（主要コマンド例）
------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - 通常（.env に KABUSYS_ENV を設定済み）:
    - python -m kabusys.run_execution
  - paper_trading モードで直接指定:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/execution.pid が生成され、data/stop_requested.flag があると起動をスキップします。
  - 停止は監視側から kill.flag を作成されるか、監視スクリプトが stop_requested.flag を作る等で行います。

- Monitoring（監視）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア、レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - モジュール API を利用して日次スコアを計算・書き込みできます（詳細は kabusys.ai.* の関数を参照）

停止・Kill Switch（運用上の注意）
--------------------------------
- 停止フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring のポーリングループを終了させるために監視スクリプト等で使用
  - data/kill.flag (既定): KillSwitch が閾値超過時に作成し ExecutionEngine に発注停止を促す
- KillSwitch は冪等に flag を書き込みます（既存なら追記しない）
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御できますが、本番では 0（自動クリアしない）を推奨します

主要な環境変数（抜粋・デフォルト）
---------------------------------
- KABUSYS_ENV: development / paper_trading / live（default: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: AI を使う場合に必要
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO 等（ログレベル）
- MONITOR_POLL_INTERVAL: run_monitoring から読み込むポーリング間隔（秒）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要なモジュールと説明です（抜粋）。

- src/kabusys/__init__.py
  - パッケージ定義、バージョン

- 設定・起動系
  - config.py: 環境変数の読み込み・Settings クラス（各種既定値・検証）
  - config_setup.py: .env 対話ウィザード
  - validate_config.py: 起動前検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト

- execution/（別ファイル群で実装）
  - broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等

- monitoring/
  - monitoring_db.py: SQLite スキーマ定義・永続化層
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: / alert_manager.py / risk_monitor.py / kill_switch.py / monitoring_engine.py

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定・aggregate cap
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等の計算（DuckDB 使用）
  - feature_exploration.py: 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py: ETF MA + マクロ NLP によるレジーム算出

- utils/
  - logging_setup.py: 統一ログ設定（stdout + 日次ファイルローテーション）
  - process_priority.py: プロセス優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config は警告で通知します）。
- .env は秘匿情報を含むため Git 等にコミットしないでください。
- OpenAI API を使用する箇所は API コストとレイテンシ、レート制限を考慮して運用してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。

拡張・開発のヒント
-------------------
- DuckDB は分析用途に適しており、research モジュールは SQL と Python を組み合わせた実装です。prices_daily や raw_financials テーブルを用意して検証できます。
- broker クライアントは BrokerClientFactory 経由で生成されるため、実装を差し替えて実際のブローカーへ接続可能です（ペーパートレード分離設計あり）。
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD や KABUSYS_ENV を活用して環境の切り替えを行ってください。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を記載していません。実運用や配布を行う場合は適切なライセンスを追加してください。
- バグ修正や機能拡張は Pull Request で歓迎します。大きな構造変更を行う場合は事前に issue で相談してください。

最後に
------
この README はコードベース内のモジュール実装に基づく概要ドキュメントです。詳細な実装（ExecutionEngine の内部処理等）は各ソースファイルの docstring と実装を参照してください。必要であれば、特定コンポーネントの利用方法や API ドキュメントを追加で作成します。