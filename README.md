README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの一部実装です。本リポジトリには実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI を使ったニュース NLP / レジーム判定、および運用ユーティリティ群が含まれます。

主な設計方針:
- 本番／ペーパー（Paper Trading）モードを区別して運用可能
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB として利用
- OpenAI を使った NLP 処理は外部 API キーで制御
- .env（環境変数）による設定管理と対話式ウィザード / 検証 CLI を提供
- ログはコンソール + 日次ローテートで永続化

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV に応じて本番 or MockBroker（paper_trading）を使用
  - 発注履歴・ポジションの永続化（SQLite）
  - 実行中停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- 監視ループ起動スクリプト: run_monitoring.py
  - システム状態、注文・約定の監視、リスク監視、KillSwitch 判定、アラート送信
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard 等の永続化
- RiskMonitor / SystemMonitor / TradeMonitor / MonitoringEngine
  - ドローダウン・ポジション上限・プロセス停止・データ鮮度・滞留注文監視
  - KillSwitch による自動停止（必要に応じて data/kill.flag を作成）
- Portfolio（選定・重み付け・ポジションサイズ計算）
  - 等配分 / スコア加重 / リスクベース配分、セクターキャップ、レジーム乗数
- Research（ファクター計算・将来リターン・IC・統計サマリ）
  - DuckDB の prices_daily / raw_financials を用いた独立計算
- AI モジュール
  - news_nlp: ニュースを OpenAI（gpt-4o-mini 等）でセンチメント化して ai_scores に格納
  - regime_detector: ETF MA とマクロニュースの LLM 評価を合成して market_regime を算出
- ユーティリティ
  - logging_setup: 統一ロギング（stdout + 日次ファイルローテーション）
  - process_priority: プラットフォーム依存を吸収した優先度 / CPU affinity 設定
  - config_setup: .env の対話式ウィザード
  - validate_config: 起動前チェック（環境変数 / config/*.yaml の存在など）
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを出力

セットアップ手順
--------------
1. Python / 仮想環境
   - 推奨: Python 3.10+（duckdb / psutil / openai などの互換性を確認してください）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - 追加で YAML ファイル検証をしたい場合: pip install pyyaml
   - 実際の requirements.txt がある場合はそれを利用してください。

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - またはプロジェクトルートに .env を作成し必要な環境変数を設定してください。
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（0/1、本番では 0 推奨）

4. ディレクトリの作成（自動作成される場合もありますが手動で用意しておくと安心）
   - mkdir -p data logs

使い方
------
基本コマンド例（プロジェクトルートで実行）:

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、data/paper_trading.db に記録されます（本番 DB と分離）。
    - 実行はバックグラウンドスレッドで run_session を回します。停止は data/stop_requested.flag の作成で通知されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を常に使用（環境に依らず）。
  - 監視ループの停止: data/stop_requested.flag を作成するか KeyboardInterrupt (Ctrl-C)。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム的に呼び出す）
  - news スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...") など
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

停止・Kill Switch
- 実行エンジンを停止したい場合、監視側や外部から data/kill.flag を書き込むことで停止シグナルを送れます（KillSwitch により評価されます）。
- run_monitoring / run_execution は data/stop_requested.flag の存在でも停止します（両スクリプトで参照するパスあり）。

注意点
- 本番（KABUSYS_ENV=live）では .env の値を慎重に設定してください。validate_config は本番向けの追加チェックを行います。
- AI 機能を使う場合、OPENAI_API_KEY が必要です。API 呼び出しは失敗時にフォールバックする設計ですが、コストとレート制限に注意してください。
- logs ディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで動作します。
- Paper Trading は本番 DB と分離されますが、設定ミスにより上書きしないよう .env を確認してください。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動読み込みと Settings クラス
- config_setup.py          — .env 対話ウィザード CLI
- validate_config.py       — 起動前検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- broker_factory.py        — ブローカークライアントの生成ファクトリ（本番 / mock 切替）
- execution_engine.py      — 実行エンジン本体
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

src/kabusys/monitoring/
- monitoring_db.py         — SQLite 永続化層
- system_monitor.py        — システム監視
- trade_monitor.py         — 注文 / 約定監視（コード参照）
- risk_monitor.py          — ドローダウン / ポジション上限監視
- kill_switch.py           — kill.flag 管理
- monitoring_engine.py     — 各監視を束ねる実行ループ
- alert_manager.py         — （アラート送信ロジック、コード参照）

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py       — Momentum / Volatility / Value 計算（DuckDB 使用）
- feature_exploration.py   — 将来リターン / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py              — ニュース NLP スコアリング（OpenAI 経由）
- regime_detector.py       — レジーム判定（MA + マクロ NLP 合成）

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート

src/kabusys/utils/
- logging_setup.py         — ログ初期化ユーティリティ
- process_priority.py      — プロセス優先度 / CPU affinity
- __init__.py

data/
- (SQLite / pid / flag ファイルが置かれる想定ディレクトリ)
logs/
- (<app_name>.log が日次ローテートで格納される既定ディレクトリ)

付録: よく使う環境変数（抜粋）
----------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- LOG_LEVEL / LOG_DIR — ログ設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

以上が本コードベースの主要な使い方と構成の概要です。必要であれば、個別モジュール（ExecutionEngine の起動フロー、Monitoring の詳細、AI モジュールのテスト方法など）についてさらに詳しい README やサンプルコマンドを作成します。どの部分を深掘りしますか？