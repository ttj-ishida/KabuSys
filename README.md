# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
ポートフォリオ構築・ポジションサイズ計算・発注実行（ExecutionEngine）・監視（Monitoring）・研究（ファクター計算・特徴量分析）・AI を使ったニュースセンチメント/レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、次の用途を想定したモジュール群です。

- 日次で銘柄選定 → 重み付け → 発注（実取引 / ペーパートレード切替可）
- ExecutionEngine による注文実行・リスク管理・再建（reconciler）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）とキルスイッチ（kill.flag）
- DuckDB を使ったデータ分析・ファクター計算（research）
- OpenAI を使ったニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード・検証ツール 等）
- ペーパートレード検証レポート出力ツール

設計上のポイント:
- 環境変数 / .env による設定管理
- Production / PaperTrading を環境変数 `KABUSYS_ENV` で切替
- SQLite（監視・注文ログ等）と DuckDB（時系列データ・分析）を併用
- フェイルセーフ設計（API失敗時はデフォルト値で継続、DBマイグレーションは冪等）

---

## 機能一覧

主な機能・モジュール

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV=paper_trading で MockBroker へ切替）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で調整）
- 設定管理
  - config_setup.py — .env 対話式ウィザード（初期作成 / 更新）
  - validate_config.py — 環境設定の事前検証
  - config.py — Settings クラス（環境変数アクセスラッパ）
- 監視
  - monitoring/monitoring_db.py — 監視用 SQLite スキーマ・永続化層
  - monitoring/system_monitor.py — システム／データ鮮度監視
  - monitoring/risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring/kill_switch.py — kill.flag 書き込みロジック
  - monitoring/monitoring_engine.py — 各 Monitor をまとめる
- 発注・実行（execution/*）
  - ExecutionEngine, OrderManager, RiskManager, Reconciler, BrokerFactory 等（起動スクリプトから組立）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（research/*）
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary）
- AI（ai/*）
  - news_nlp.py — OpenAI を使ったニュースセンチメント取得（ai_scores への書込）
  - regime_detector.py — マクロ + ETF MA200 乖離を合成してレジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（Console + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定

---

## 前提 / 要件

- Python 3.10 以上（| 型注釈などの使用のため）
- SQLite（Python 標準 sqlite3 を使用）
- 推奨パッケージ（機能に応じて）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（validate_config の YAML 検査を行う場合）
- 任意:
  - 実運用では kabuステーション API の接続情報や J-Quants トークンが必要

例: 必要パッケージ（最低限・代表）
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt が無い場合は上記を参考に環境を準備してください）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

3. .env ファイルの作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードが .env を生成します（Git にコミットしないでください）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う任意変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
     - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証
   - python -m kabusys.validate_config
   - 警告やエラーを確認。--strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ準備
   - デフォルトでは以下のようにファイルを参照します:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db（paper_trading 時）
     - data/execution.pid / data/kill.flag / data/stop_requested.flag（プロセス制御用）
   - 必要に応じて .env でパスを変更してください

---

## 使い方

主な実行コマンド例（パッケージとして実行）

- 監視ループを起動（SystemMonitor）
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

  注意: monitoring は KABUSYS_ENV にかかわらず production (settings.sqlite_path) の SQLite を使用します。

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV による挙動:
    - paper_trading: MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 実ブローカークライアントを使用（必要な設定を環境変数で用意すること）
  - python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI スコアリング（コードから呼び出す例）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key 指定 or OPENAI_API_KEY 環境変数
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル: logs/<app_name>.log（app_name は起動スクリプト内で指定、例: "execution", "monitoring"）
  - ローテーション: 日次、過去 30 日分を保持

- プロセス優先度
  - 起動スクリプト内で set_process_priority("high") を呼んでいます。必要に応じて utils.process_priority.set_cpu_affinity() を用いて CPU 固定も可能。

- 停止 / キルスイッチ
  - data/stop_requested.flag: run_monitoring / run_execution はこのファイルを検出するとループ停止します（手動停止フラグ）。
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 側は kill.flag の存在を検出して停止します。
  - ExecutionEngine の PID ファイル: data/execution.pid（実行中プロセスの管理に利用）

---

## ディレクトリ構成

主要ファイル / ディレクトリ（src/kabusys 以下）

- __init__.py
- config.py — Settings / 自動 .env ロードロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

- ai/
  - news_nlp.py
  - regime_detector.py

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (存在：監視の一部)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (アラート送信の実装がある想定)

- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- monitoring scripts / tools
  - tools/paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- data/（実行時に利用するディレクトリ）
  - monitoring.db（デフォルト: data/monitoring.db）
  - paper_trading.db（ペーパートレード時）
  - kabusys.duckdb（DuckDB）
  - execution.pid / kill.flag / stop_requested.flag

---

## 開発者向けメモ

- Settings（config.py）は .env 自動ロードを行います。テストから自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML が無い場合でも動作しますが、config/*.yaml の中身検証はスキップされます（警告出力）。
- DuckDB 関係の関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数で受け取り、外部依存を避ける設計（テスト容易化）。
- OpenAI 呼び出し部分はリトライやレスポンス検証を慎重に行っています。API レスポンスの破損やネットワークエラーはフェイルセーフで処理されますが、API キー未設定時は例外が出ます。

---

## よくある Q&A / トラブルシュート

- Q: MONITOR_POLL_INTERVAL を変更したい
  - A: 環境変数 MONITOR_POLL_INTERVAL を秒数で設定します（例: export MONITOR_POLL_INTERVAL=30）。不正値や 0 以下はデフォルト 60 秒にフォールバックします。

- Q: Paper Trading と本番 DB が混ざってしまわないか
  - A: run_execution.py は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使い分離します。monitoring は environment に関係なく settings.sqlite_path を使います（監視は production path を想定）。

- Q: OpenAI を使った処理で API キーを指定するには？
  - A: 環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key 引数を渡してください。

---

README は簡単な入門を目的としています。詳細は各モジュールの docstring（ソース内コメント）を参照してください。追加で実行例や構成サンプル（.env.example）を作成したい場合はお知らせください。