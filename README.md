# KabuSys

日本株向け自動売買システム（ライブラリ・実行スクリプト群）

このリポジトリは、自動売買の実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価、設定ウィザード・検証ツールなどを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。主な目的は次のとおりです。

- ExecutionEngine による発注フロー（ライブ／ペーパートレード対応）
- Monitoring コンポーネントによる稼働監視・リスク監視・アラート
- Portfolio 構築およびポジションサイジング関数（純粋関数）
- Research 用のファクター計算・特徴量解析（DuckDB ベース）
- OpenAI を用いたニュース NLP（センチメント評価）およびレジーム判定
- 対話式 .env 作成ウィザード / 設定検証ツール
- ペーパートレード検証レポート出力スクリプト

設計方針として、実行（ブローカー呼び出し）と研究・分析ロジックは分離されており、ペーパートレード時は本番 DB と分離された SQLite を使用します。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動するエントリポイント
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient と専用 SQLite (data/paper_trading.db) を使用
  - プロセス優先度を高く設定するユーティリティ呼び出しを含む
  - stop/kill フラグファイル検出による安全停止処理

- run_monitoring.py
  - SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - Monitoring は環境に関わらず本番 sqlite_path を使用（運用上の分離）

- monitoring/
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, MonitoringDB（SQLite）
  - リスクイベントのデデュプリケーション、ダッシュボード upsert、kill.flag ロジック等

- ai/
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores への書込）
  - regime_detector: ETF（1321）MA とマクロニュースで市場レジーム判定、DB へ書込

- portfolio/
  - 銘柄選定、等重・スコア重み計算、セクター上限適用、ポジションサイズ計算（lot 丸め・aggregate cap）
  - 純粋関数群で副作用なし

- research/
  - ファクター計算（momentum / volatility / value）、将来リターン計算、IC計算、統計サマリー（DuckDB ベース）

- tools/
  - paper_verification_report.py: ペーパートレード DB から Pass/Fail 判定の検証レポート生成

- config_setup.py / validate_config.py
  - .env を対話式に生成・更新するウィザード
  - 起動前に環境変数・config/*.yaml・パス等を検証する CLI

- utils/
  - process_priority, CPU affinity の設定ユーティリティ（psutil 使用）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing, match 等の利用に依存しないが型注釈を活用）
- SQLite は標準ライブラリに含まれます
- 必要な外部パッケージ: duckdb, psutil, openai（AI 機能）、PyYAML（validate_config の YAML 検証; 任意）

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （validate_config の YAML 検証を有効化する場合）pip install pyyaml

   例（開発用途）:
   - pip install -e .  （パッケージ化されている場合）

4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: 本番用の .env は絶対に Git にコミットしないこと

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題がある場合はエラーメッセージに従って修正
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - run_execution / run_monitoring の起動時に SQLite テーブル等は自動作成されます（init_monitoring_db）

注意:
- OpenAI を使用する機能（news_nlp, regime_detector）を使う場合は OPENAI_API_KEY を環境変数に設定してください。
- 実行中、プロセス優先度変更や PID ファイルの作成などに管理者権限が必要な場合があります（環境に依存）。

---

## 使い方（主要コマンド）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV により動作モードが変わる:
      - development: 発注は行われない（開発用）
      - paper_trading: MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
      - live: 実際のブローカー API（kabuステーション）へ発注
    - 実行前に kill.flag をクリアしたい場合:
      - Settings.kill_flag_clear_on_start を 1 に設定していると起動時に kill.flag が自動クリアされます（本番では 0 推奨）

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - デフォルトで MONITOR_POLL_INTERVAL=60 秒
    - 環境変数で上書き可能:
      - export MONITOR_POLL_INTERVAL=30

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）

- AI 機能（例）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して DuckDB 接続と target_date を渡す
  - OPENAI_API_KEY が必要（引数からも渡せる）

プロセス停止制御:
- data/stop_requested.flag: run_* スクリプトでポーリングループを安全終了させるために監視されるファイル（存在すればループは終了します）
- KillSwitch（data/kill.flag）: Monitoring コンポーネントが条件を満たすと kill.flag を書き込み、ExecutionEngine 停止をトリガーする設計

---

## 主要設定項目（抜粋）

- KABUSYS_ENV: execution モード
  - development | paper_trading | live

- データベースパス（デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject

- ログ/監視系
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

- OpenAI
  - OPENAI_API_KEY: AI モジュールで使用

---

## ディレクトリ構成（概要）

リポジトリは src/kabusys 配下にコードがあります。主要ファイル／パッケージ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings クラス
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリング
    - regime_detector.py      — マクロ + ETF MA で市場レジーム判定

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化、CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジックをまとめる想定）

  - execution/                — ExecutionEngine, OrderManager, BrokerFactory 等（詳細は実装ファイルに依存）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - data/                     — データ処理 / pipeline（DuckDB 操作用ユーティリティ等）
  - tools/
    - paper_verification_report.py

  - utils/
    - process_priority.py      — プロセス優先度/CPU affinity 設定ユーティリティ

- data/
  - （実行時に生成される DB / PID / flag ファイル等）
  - デフォルトのファイル:
    - data/kabusys.duckdb
    - data/monitoring.db
    - data/paper_trading.db
    - data/execution.pid
    - data/kill.flag
    - data/stop_requested.flag

---

## 運用上の注意 / FAQ

- 本番環境（KABUSYS_ENV=live）の場合は .env の設定を慎重に管理してください。validate_config は live 設定時に追加の警告を出します。
- モジュールが psutil に依存するため、プロセス優先度変更や CPU affinity 設定は環境権限によって失敗することがあります（ログに警告が出ます）。
- OpenAI 呼び出しでは RateLimit / ネットワーク障害などを考慮したリトライロジックが実装されていますが、API 利用料には注意してください。
- ペーパートレードは本番 DB と分離されます。paper_trading モードを使うことで実際の注文を出さずに発注ロジック検証が可能です。
- monitoring は本番 sqlite_path を参照します（run_monitoring は KABUSYS_ENV に依らず本番 monitoring DB に書き込みます）。そのため、検証用に監視ログを分離したい場合は SQLITE_PATH を調整してください。

---

README はここまでです。実装・追加ドキュメント（API の詳細、ExecutionEngine の設定、AlertManager の送信先設定など）は各モジュールの docstring およびコメントを参照してください。もし README に追加したいコマンド例や設定ファイルテンプレート（.env.example）を含めたい場合は教えてください。