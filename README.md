# KabuSys

日本株自動売買システムの一部実装。ポートフォリオ構築、発注エンジン、監視・アラート、Research / AI 補助機能（ニュース NLP / レジーム検出）などを含むモジュール群です。

---

## プロジェクト概要

KabuSys は次のような目的を持つモジュール群で構成されています。

- 戦略に基づく銘柄選定・配分（portfolio）
- 発注管理と ExecutionEngine（execution）
- 監視（system / trade / risk）と Kill Switch（monitoring）
- 研究用ファクター計算・特徴量解析（research）
- ニュースの LLM によるセンチメント評価・レジーム判定（ai）
- ペーパートレード検証レポート等のユーティリティ（tools）
- 環境設定・バリデーションツール（config_setup / validate_config）

設計上の特徴：
- DuckDB：市場データ・研究用DB
- SQLite：監視ログ / ペーパートレード用 DB
- OpenAI（任意）：ニュース NLP / レジーム判定に利用
- .env ベースの設定（config_setup による対話式生成、Settings クラスで読み込み）

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文を送信・管理（paper_trading モードでは MockBroker）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の組立て

- Monitoring
  - SystemMonitor：CPU/Mem/Disk、データ鮮度、実行プロセス存在確認
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch：危険時に stop フラグ（data/kill.flag）を書き込む
  - MonitoringEngine：各 Monitor を束ねるポーリングループ

- Portfolio
  - 候補選定・重み計算（等金額/スコア加重）
  - セクター上限適用、レジームに応じた投入倍率
  - 株数計算（単元株丸め、利用可能現金・上限考慮）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（スピアマン）や統計サマリ

- AI
  - news_nlp.score_news：raw_news を集約して OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出・ai_scores へ書込
  - regime_detector.score_regime：ETF MA とマクロニュース LLM を組合せて market_regime を算出・永続化

- Tools
  - paper_verification_report：ペーパートレード用 SQLite から検証レポートを生成

- 設定管理
  - config_setup.py：対話式で .env を作成／更新
  - validate_config.py：起動前に環境変数や config/*.yaml を検証

---

## セットアップ手順

※ 以下はリポジトリ直下を想定しています（src/kabusys が配置されている場合はプロジェクトルートをワークディレクトリにしてください）。

1. Python 環境（推奨: 3.10+）を用意してください。

2. 必要パッケージをインストール（最低限）
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（validate_config の YAML 検証を使う場合）
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそちらを使用してください。）

3. .env を作成
   - 対話式ウィザードで作成することを推奨:
       python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成。
   - 自動ロードは Settings モジュールで行われます（プロジェクトルートに .env / .env.local があれば自動で読み込まれます）。
   - 自動ロードを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（起動前チェック）
     python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合は --strict を付与します。

5. DB 初期化
   - run_execution / run_monitoring の起動時に内部で SQLite のテーブル作成（init_monitoring_db）が行われます。特別な事前作業は不要です。

---

## 主要な環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション API パスワード

- 実行モード / ログ
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL

- DBパス
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（paper_trading 時に使用。デフォルト: data/paper_trading.db）

- AI
  - OPENAI_API_KEY : OpenAI を使う場合は必須（ai.news_nlp / regime_detector）

- その他
  - PID_FILE_PATH : ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH : Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアする（0/1、本番では 0 推奨）
  - MONITOR_POLL_INTERVAL : run_monitoring で監視ポーリング間隔（秒、デフォルト 60）

---

## 使い方（実行例）

- 環境セットアップ（対話式）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視ループ起動（Production 監視用スクリプト）
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）。
  - 監視は .env の KABUSYS_ENV に関係なく本番 sqlite_path を使用（監視ログは共通 DB に貯める設計）。
  - 停止はプロジェクトルート/data/stop_requested.flag の作成で検知します。

- ExecutionEngine 起動（注文エンジン）
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）。
  - 実行中の停止：project_root/data/stop_requested.flag を作成すると停止処理がトリガーされます。
  - 起動時に PID ファイル（data/execution.pid）を書きます。stale PID は SystemMonitor が検出・削除します。

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。--db で上書き可。

- AI 機能（コードから呼び出す）
  - ニューススコアリング:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

  - OpenAI キーが環境変数 OPENAI_API_KEY に設定されている場合、api_key 引数は不要。

---

## 注意事項 / 運用メモ

- paper_trading モードでは発注系は本番 DB と分離され、data/paper_trading.db に記録されます。実運用時は KABUSYS_ENV を慎重に設定してください（live は本番）。
- kill.flag（KILL_FLAG_PATH）を本番で自動クリアする KILL_FLAG_CLEAR_ON_START=1 は危険です（本番では 0 推奨）。
- run_monitoring / run_execution は起動直後に set_process_priority("high") を呼びますが、OS 権限によっては失敗して警告が出ます。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合、起動時に自動生成されることがありますが、validate_config はその旨を警告します。
- OpenAI 呼び出し部分はリトライ・フェイルセーフ実装があるものの、API キー・コスト管理に注意してください。
- .env は機密情報を含むため、絶対に VCS にコミットしないでください。

---

## ディレクトリ構成（主なファイル・モジュール）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理、自動 .env ロード
- config_setup.py           — 対話式 .env 生成ウィザード
- validate_config.py        — 起動前チェック CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

subpackages:
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory / MockBrokerClient 等
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

その他:
- data/                    — デフォルト DB / PID / flag の保存場所（実行時に作成される）
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用、任意)
  - execution.pid
  - kill.flag / stop_requested.flag

---

## トラブルシューティング

- 設定が読み込まれない / テスト環境で自動 .env ロードを無効にしたい:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出しでエラーが発生する場合:
  - OPENAI_API_KEY が設定されているか確認
  - ネットワーク/API レートを確認（ライブラリ内で指数バックオフが実装されています）

- DB スキーマが古い場合:
  - monitoring_db.init_monitoring_db はマイグレーション（カラム追加）を行うので、起動時に自動適用されます。

---

この README はリポジトリに含まれるコードを元に作成しています。各モジュールの詳細な使用法や API はソースコードの docstring / 関数コメントを参照してください。問題・改善提案があればソースコードのコメントや該当モジュールを確認の上、設定や呼び出し方法を調整してください。