# KabuSys

日本株自動売買システムのコンポーネント群。  
このリポジトリはシグナル生成 / ポートフォリオ構築 / 発注エンジン / 監視 / 研究用ユーティリティや AI 補助モジュールなどを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を持つ小規模な自動売買フレームワークです。

- 取引戦略に基づく銘柄選定・配分（ポートフォリオ構築）
- 発注管理・発注エンジン（ExecutionEngine） — 本番 / ペーパートレード分離
- 監視コンポーネント（System / Trade / Risk）と Kill Switch による安全停止
- DuckDB を用いた研究用ファクター計算、特徴量解析モジュール
- OpenAI を利用したニュース NLP（センチメント）およびレジーム判定
- ペーパートレード検証レポート生成ツール
- .env 対話式ウィザード・設定検証 CLI

設計のポイント:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に依存）
- 自動化された監視・アラート・Kill Switch により安全弁を提供
- DuckDB を用いたオフライン分析（prices_daily / raw_financials 等）

---

## 主な機能一覧

- Execution
  - 発注エンジン起動スクリプト（python -m kabusys.run_execution）
  - BrokerClientFactory により本番/モックを切り替え
  - 発注・リスク管理・照合（reconciler）機能

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - kill.flag による安全停止、stop_requested.flag による終了検出
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き

- Portfolio
  - 銘柄選定（select_candidates）
  - 重み計算（等分 / スコア重み）
  - ポジションサイジング（lot 単位丸め、リスクベース等）
  - セクターキャップやレジーム乗数の適用

- Research
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）
  - ニュースセンチメントのスコアリング（ai.news_nlp.score_news）
  - マクロニュース + ETF MA を用いたレジーム判定（ai.regime_detector.score_regime）

- Tools
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - 対話式 .env 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## セットアップ手順

前提:
- Python 3.10+（typing の union などを利用）
- SQLite（標準で利用可能）
- DuckDB（Python パッケージ）
- psutil（プロセス優先度・メトリクス取得）
- OpenAI ライブラリ（AI 機能を使う場合）
- PyYAML（config の内容検証を行う場合、任意）

1. リポジトリをクローンしてワークディレクトリに移動:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
   pip install -r requirements.txt
   ※ requirements.txt がない場合は最低限以下を入れる:
   pip install duckdb psutil openai

   （開発用に PyYAML を入れると validate_config の YAML 検証が有効になります）
   pip install pyyaml

4. 初期設定 (.env) を作成:
   python -m kabusys.config_setup

   対話式ウィザードで必要項目を入力して `.env` を生成します。生成後は設定検証を推奨します:
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

5. DB ファイルとログディレクトリはデフォルトで `data/` と `logs/` に生成されます。必要に応じて .env でパスを上書きしてください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション／設定:
- KABUSYS_ENV: 実行環境 (development|paper_trading|live) — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: ログファイル出力先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を利用する AI 機能で使用
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視用フラグ設定

監視用制御:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- data/stop_requested.flag: 存在すると run_monitoring / run_execution のループを終了

注意:
- Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用して監視データを書き込みます。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番データと分離）。

---

## 使い方

主なコマンド例:

- .env の作成（対話式）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番またはペーパートレードは KABUSYS_ENV に従う）
  python -m kabusys.run_execution

  実行フロー:
  - プロセス優先度を "high" に設定
  - SQLite / DuckDB に接続
  - BrokerClientFactory でブローカークライアントを作成（モック切替）
  - Engine.run_session を別スレッドで実行し stop flag を監視

- Monitoring 起動
  python -m kabusys.run_monitoring

  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。  
  run_monitoring は data/stop_requested.flag の存在を検知してループを終了します。

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

- 研究用関数（Python から直接呼び出し）
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  # DuckDB 接続を渡して使用

- AI スコアリング（OpenAI API キーが必要）
  from kabusys.ai import score_news
  # DuckDB 接続と target_date を渡して使用

ログ:
- setup_logging により stdout (StreamHandler) と 日次ローテートファイル (logs/<app>.log) を設定します。ログディレクトリは LOG_DIR またはデフォルト logs/。

停止／Kill Switch:
- リスク条件に従い kill.flag が書き込まれると ExecutionEngine に停止信号が送られます。kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）を参照します。起動時に KILL_FLAG_CLEAR_ON_START=1 をセットすると自動クリアします（本番では注意）。

---

## ディレクトリ構成（抜粋）

リポジトリは `src/kabusys` 以下に主要モジュールが格納されています。主要ファイルと役割:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数／設定読み込みユーティリティ
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動エントリポイント
  - run_monitoring.py          — Monitoring 起動エントリポイント

- src/kabusys/execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  （発注に関連する実装）

- src/kabusys/monitoring/
  - monitoring_db.py           — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py                — ニュースセンチメント取得（OpenAI）
  - regime_detector.py         — レジーム判定（MA + LLM）

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - logging_setup.py           — 統一ログ設定
  - process_priority.py        — プロセス優先度 / CPU affinity

デフォルトのデータ・ログ配置:
- data/                       — SQLite / pid / flag 等（デフォルト）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag / stop_requested.flag
- logs/                       — アプリケーションログ

---

## 注意事項 / 運用上のヒント

- 本番では KABUSYS_ENV=live を慎重に扱ってください。validate_config は live 向けの追加警告を出します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は開発用です。本番では 0 を推奨します。
- Monitoring は監視用 DB（SQLITE_PATH）に書き込むため、監視データのバックアップやローテーションを検討してください。
- OpenAI を使うモジュールは API 利用料が発生します。API キーは .env に設定してください。API 呼び出しはリトライ・フェイルセーフを考慮した実装になっていますが、連続実行時のレート制限に注意してください。
- DuckDB は分析向けに高速で便利ですが、スキーマ（prices_daily / raw_financials / raw_news 等）の整合性が前提です。研究用データ取り込みパイプラインを整備してください。

---

もし README に追記してほしい点（例: 具体的な .env サンプル、起動スクリプトのデバッグ方法、CI/デプロイ手順 など）があれば教えてください。