README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究フレームワークです。  
本リポジトリは注文実行エンジン、監視機能、ポートフォリオ構築、ファクター計算、ニュース NLU（OpenAI）連携などを含むモジュール群を提供します。  
設計方針として「本番とペーパートレードを明確に分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に行う（環境変数で制御）」を重視しています。

主な特徴
---------
- ExecutionEngine（発注エンジン）と Monitoring（監視）を別プロセスで運用可能
- Paper Trading モード時は MockBroker を用い、専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離
- モニタリング:
  - システム稼働状況（CPU / メモリ / ディスク）ログ
  - 注文ログ・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（条件到達で data/kill.flag を書き込む）機能
- ポートフォリオ構築（候補選定、等重 / スコア重み、リスクに応じたポジションサイズ決定）
- リサーチ用モジュール（DuckDB を用いたファクター計算、将来リターン計算、IC 計算など）
- ニュース NLP（OpenAI）連携による銘柄別センチメントスコアリングおよび市場レジーム判定
- ロギングユーティリティ（コンソール + 日次ローテーション）
- 環境設定ウィザード（.env の対話式作成）と設定検証 CLI

セットアップ手順
----------------
前提: Python 3.9+ を想定（typing 構文等を使用）。以下は推奨手順です。

1. リポジトリをクローン
   - git clone … && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 推奨パッケージ（必須／任意に応じて）:
     - duckdb
     - psutil
     - openai
     - pyyaml (config 検証のため任意)
   - 例:
     - pip install duckdb psutil openai pyyaml

   注: requirements.txt は本リポジトリに含まれていないため、実行時に必要なパッケージを個別に追加してください。

4. 環境変数の準備（.env）
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成してください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

重要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用設定（主なもの）:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- LOG_DIR: ログ保存ディレクトリ
- OPENAI_API_KEY: OpenAI 利用時に必要

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む挙動を抑制できます。
- PAPER_FILL_MODE（ペーパートレードの約定モード）: instant | partial | never | reject

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env を対話的に作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV によって本番 DB / ペーパートレード DB を切り替え
    - 起動時に data/stop_requested.flag を検査し、存在すれば起動を中止
    - data/execution.pid を利用して PID 管理
    - プロセス優先度を High に設定（set_process_priority）

- 監視ループを起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を参照（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH での指定も可能）

- 研究・AI 関連（プログラム API として呼び出す）
  - kabusys.research モジュール: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary など
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ランタイム挙動のポイント
-----------------------
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出して統一されたログ出力（stdout + 日次ファイルローテーション）を行います。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出します（Windows/Linux を抽象化）。
- Kill / Stop フラグ:
  - data/kill.flag: Kill Switch による ExecutionEngine 停止シグナル（KillSwitch が書き込む）
  - data/stop_requested.flag: 起動スクリプトが外部停止要求として監視するファイル
- DB:
  - init_monitoring_db() により監視用テーブルが冪等に初期化されます（SQLite）
  - DuckDB は分析用途向け（prices_daily / raw_financials / raw_news 等）

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                   — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py            — マクロ + ETF MA で市場レジームを判定して market_regime に書き込む
- monitoring/
  - monitoring_db.py              — SQLite 用永続化層（system_status/trade_logs/positions/risk_logs/dashboard）
  - system_monitor.py             — システム監視（CPU / メモリ / データ鮮度 / プロセス監視）
  - trade_monitor.py              — （注文監視ロジック、ファイル内で定義あり）
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — 条件到達で kill.flag を書くユーティリティ
  - monitoring_engine.py          — 各 Monitor を束ねる実行ループ
  - alert_manager.py              — （アラート送信ロジック、コードベースに参照あり）
- execution/
  - execution_engine.py           — ExecutionEngine 本体（EngineConfig, run_session 等）
  - order_manager.py
  - order_repository.py
  - risk_manager.py
  - reconciler.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py          — 銘柄選定（スコアソート）
  - position_sizing.py            — 株数決定・単元丸め・aggregate cap
  - risk_adjustment.py            — セクターキャップ・レジーム乗数
- research/
  - factor_research.py            — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリ
- data/
  - pipeline.py                   — prices データ取得 / last date 関数（参照あり）
  - stats.py                      — zscore_normalize 等（参照あり）
- utils/
  - logging_setup.py              — ログ初期化ユーティリティ
  - process_priority.py           — プラットフォーム非依存の優先度設定
- tools/
  - paper_verification_report.py  — Paper Trading のパス/フェイル判定レポート生成スクリプト

運用/開発メモ
-------------
- ペーパートレードは settings.is_paper に基づき専用 DB を使用します。実運用時は KABUSYS_ENV を慎重に設定してください（live は注意喚起あり）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・フォールバック戦略を実装してあり、失敗時はフェイルセーフ（スコア 0.0 等）で継続します。
- config.py は .env ファイル自動読込を行いますが、テスト時などに自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モジュール単位でのユニットテストや CI 設定は本 README に含まれていません。プロジェクトに合わせて tests/ を追加してください。

貢献
----
バグ修正・改善提案は Issue / Pull Request で受け付けます。設計方針（本番/ペーパートレード分離、ルックアヘッド回避）を尊重した実装をお願いします。

ライセンス
----------
（ここにプロジェクトのライセンス情報を記載してください。例: MIT License）

以上。必要であれば、各モジュールの詳細使用例（コードスニペット）や運用チェックリストを追記します。