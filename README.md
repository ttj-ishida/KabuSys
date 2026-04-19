# KabuSys

日本株向け自動売買システムのリポジトリ（ドキュメント版）。この README は、開発者 / 運用者向けにプロジェクトの概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したコードベースです。戦略のリサーチ／ファクター計算、ポートフォリオ構築、発注エンジン（本番／ペーパートレード分離）、監視（Monitoring）、およびニュースを使った AI スコアリング等のモジュールを含みます。監視ログは SQLite、分析用に DuckDB を利用します。OpenAI を用いた NLP（ニュースセンチメント）やレジーム判定の仕組みも搭載しています。

主な設計方針:
- 本番とペーパートレードは DB を分離（paper_trading モードでは Mock ブローカを使用）
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を直接参照しない設計）
- フェイルセーフ：API エラーやデータ欠損時は安全側にフォールバック
- .env / .env.local による設定管理と対話式ウィザード・検証 CLI を提供

---

## 機能一覧

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（本番/ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 設定管理
  - config_setup.py: .env を対話式に作成／更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック CLI
  - Settings クラス: 環境変数アクセスのラッパー（設定検証・デフォルト）
- 監視（Monitoring）
  - MonitoringDB: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch: 条件に応じて data/kill.flag を生成して ExecutionEngine を停止
  - run_monitoring: ポーリングループ、ポーリング間隔は環境変数で上書き可（MONITOR_POLL_INTERVAL）
- 発注・実行
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, BrokerClientFactory
  - run_execution: スレッドでエンジンを動かす。KABUSYS_ENV=paper_trading 時は MockBroker を使用し data/paper_trading.db を使用
- ポートフォリオ構築（純粋関数群）
  - portfolio: 候補選定、重み計算（等重、スコア重み）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ / ファクター計算
  - research: モメンタム、ボラティリティ、バリュー計算、将来リターン、IC 計算、統計サマリ
  - DuckDB 経由で prices_daily / raw_financials 等テーブルを利用
- AI（OpenAI）
  - ai.news_nlp: ニュースをまとめて OpenAI に投げ、銘柄ごとのセンチメント（ai_scores）を書き込む
  - ai.regime_detector: ETF の MA200 とマクロニュースを組み合わせて市場レジーム判定し DB に保存
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等）
- ユーティリティ
  - utils.logging_setup: 統一ログ設定（stdout + 日次ローテーションファイル）
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提・依存関係

必須（代表例）
- Python 3.10 以上（型アノテーションで | を使用しているため）
- 以下の Python パッケージ（pip でインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合、無くても警告になるが機能はスキップされる）
- SQLite は標準ライブラリで使用
- ネットワーク接続（OpenAI を使う機能を利用する場合）

例: 開発環境構築
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン・ワークディレクトリへ
   - 例: git clone <repo> && cd <repo>

2. Python 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に `.env` をプロジェクトルートに配置

   注意:
   - 自動で .env を読み込む機能がある（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - .env.local は .env を上書きするため開発時の秘密情報を置くのに便利

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要なら）
   - data ディレクトリに監視用 SQLite（デフォルト: data/monitoring.db）や paper_trading.db が置かれる
   - ログは logs/ に出力（LOG_DIR, LOG_LEVEL で変更可）

---

## 実行方法（使い方）

基本的な起動コマンドはモジュールとして実行します。

1. ExecutionEngine（注文実行）
   - 本番（KABUSYS_ENV=live）
     - KABUSYS_ENV=live を .env に設定してから:
       - python -m kabusys.run_execution
   - ペーパートレード（KABUSYS_ENV=paper_trading）
     - KABUSYS_ENV=paper_trading を設定すると MockBroker が使われ、データは data/paper_trading.db に記録され本番 DB と分離されます。
     - python -m kabusys.run_execution

   動作:
   - 起動時にプロセス優先度を high に設定
   - DB 接続（paper_trading モード時は paper_sqlite_path を使用）
   - ExecutionEngine がバックグラウンドスレッドでセッションを実行し、data/stop_requested.flag を作成している場合は起動せず終了します
   - 停止は data/stop_requested.flag の作成、または kill.flag を介した KillSwitch による停止が可能

2. Monitoring（監視ループ）
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を上書き:
     - export MONITOR_POLL_INTERVAL=30  （秒）
   - 監視は常に本番の sqlite_path（settings.sqlite_path）を使用してログを書き込みます（環境に依らず）

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
   - オプション:
     - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
   - 簡易判定基準（稼働率、約定率、送信率、P95 レイテンシ等）を出力します

4. AI スコアリング / レジーム判定（Python API）
   - ニューススコアリング（DuckDB 接続を渡して実行）
     - 例:
       from openai import OpenAI  # OpenAI の初期化は score_news 内で行える
       import duckdb
       from kabusys.ai.news_nlp import score_news
       conn = duckdb.connect("data/kabusys.duckdb")
       count = score_news(conn, target_date, api_key="sk-...")

   - レジーム判定:
       from kabusys.ai.regime_detector import score_regime
       count = score_regime(conn, target_date, api_key="sk-...")

   注意: OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフェイルセーフがあり、失敗時は安全側の既定値で継続します。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログディレクトリ, デフォルト: logs/）
- OPENAI_API_KEY（AI 機能利用時）

その他は config_setup.py のウィザードが案内します。

---

## 停止・安全装置

- data/stop_requested.flag:
  - run_execution/run_monitoring の起動/ループ監視で参照される停止フラグファイル。作成されると実行ループは安全に停止します。
- data/kill.flag:
  - KillSwitch による停止（条件が成立すれば kill.flag を書き込み ExecutionEngine へ停止を通知）
- PID ファイル:
  - 実行側は data/execution.pid を使用してプロセス状態を管理します（Settings.pid_file_path 参照）

---

## トラブルシューティングと運用メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストや特殊な起動環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- validate_config.py は起動前に必ず実行して設定漏れやパスの問題を検出してください。--strict モードで警告も失敗とみなせます。
- ログディレクトリ作成失敗時はコンソール出力のみで継続します。ログ出力がない場合は LOG_DIR のパーミッションやディスク空き容量を確認してください。
- OpenAI を使う AI 機能は API 失敗時にフェイルセーフでスキップする設計ですが、APIキーや料金設定は事前に確認してください。
- DuckDB 用のテーブル（prices_daily / raw_financials / raw_news 等）はリサーチ・AI 機能で参照されます。データの整備・更新は別途データパイプラインを用意してください（data.pipeline モジュールの利用を想定）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリの主要なディレクトリとファイルの概要（src/kabusys を基点）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — Settings / .env 自動読み込み
    - config_setup.py           — 対話式 .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py        — （アラート送信ロジック：LINE などを想定）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
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
    - data/                       — 実行時に生成されるデータファイル（例: monitoring.db, paper_trading.db）
    - tools/
      - paper_verification_report.py

補足:
- logs/ — ログ出力ディレクトリ（デフォルト）
- .env, .env.local — 環境変数ファイル（プロジェクトルート）

---

## 開発メモ / 拡張案

- ポジション単元（lot_size）や銘柄別の単元情報を stocks マスタで管理してポジション計算に反映する拡張
- AI モジュールの応答フォーマットと検証ロジックの追加堅牢化
- Monitoring のアラートルールや通知チャンネル（LINE, PagerDuty 等）の拡張
- DuckDB / SQLite のスキーマ管理をマイグレーションツールで体系化

---

この README は現状のコードベース（主要モジュール）を元に作成しています。運用前に必ず python -m kabusys.validate_config で設定を検証し、.env の内容・DB パス・API キーが正しいことを確認してください。必要であれば README をプロジェクト固有の運用手順に合わせて追記してください。