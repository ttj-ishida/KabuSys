# KabuSys

日本株向け自動売買システム（ライブラリ/ランタイム）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 日次・オンデマンドのリサーチ（ファクター計算、将来リターン、IC解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- ExecutionEngine による発注処理（本番 / ペーパートレードを切替）
- 監視機能（システム状態、注文ログ、リスク監視、Kill Switch）
- ニュースの NLP による銘柄センチメント評価および市場レジーム判定（OpenAI 利用）
- 運用・検証用ツール（ペーパートレード検証レポート等）

設計方針として、可能な限り外部副作用を分離し、DuckDB / SQLite をデータ格納に使用。多くの処理は「副作用を持たない純粋関数」で実装されています。

---

## 機能一覧

- run_execution.py
  - ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパートレード切替）
  - paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB に記録
  - プロセス優先度を "high" に設定
  - stop フラグ（data/stop_requested.flag）で安全に停止

- run_monitoring.py
  - SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能
  - 監視ログは monitoring 用の SQLite（settings.sqlite_path）に永続化（環境に関係なく本番 sqlite_path を使用）

- 設定管理
  - Settings クラス（kabusys.config）: .env / 環境変数から設定を取得
  - config_setup.py: 対話式ウィザードで .env を生成/更新
  - validate_config.py: 起動前検証（必須環境変数や config/*.yaml の存在等）

- 監視（monitoring パッケージ）
  - MonitoringDB（SQLite 永続層）
  - SystemMonitor（CPU/メモリ/ディスク・プロセス状態・データ鮮度）
  - TradeMonitor（trade_logs の監視）※実装ファイル群あり
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（条件を満たしたら data/kill.flag を書き込む）
  - MonitoringEngine（各監視を束ねてポーリング、アラート発行）

- ポートフォリオ（portfolio パッケージ）
  - 銘柄選定（score / rank ベース）
  - 等金額・スコア重み付け
  - セクターキャップ適用
  - ポジションサイズ計算（リスクベース/等配分/スコア配分）

- リサーチ（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン / IC / 統計サマリ機能
  - DuckDB を用いた高速集計

- AI（ai パッケージ）
  - news_nlp: raw_news を OpenAI に送って銘柄ごとにセンチメントを算出・ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースセンチメントを組み合わせて市場レジーム判定
  - OpenAI API を利用（OPENAI_API_KEY が必要）

- ツール（tools）
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL 判定を行うレポート生成

- ユーティリティ（utils）
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.9+（推奨）
- SQLite は標準ライブラリで使用
- 必要な外部パッケージ（代表的なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（validate_config の YAML 検証に必要。任意）

例: 仮想環境作成と依存インストール
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai PyYAML

プロジェクトルートに移動後、.env を作成します（推奨: 対話式ウィザードを使用）:

- 対話式で .env を作成:
  - python -m kabusys.config_setup
  - ウィザードに従って J-Quants トークン、kabu API パスワード 等を入力します

- 手動で .env を作る場合は最低限以下を設定してください:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - OPENAI_API_KEY（AI 機能を使う場合）
  - DUCKDB_PATH（任意、デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（任意、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
  - LOG_LEVEL（任意、デフォルト INFO）
  - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

設定を検証:
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いになります

ログディレクトリ:
- デフォルトは logs/。書き込み権限があることを確認してください。

初回実行時、data/ ディレクトリなどは自動生成されることがありますが、環境により権限エラーが発生する場合があるので予め作成しておくと安全です。

---

## 使い方（起動・コマンド）

主要なエントリポイントはモジュール実行です。プロジェクトルートで実行してください。

- 監視プロセスを起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（秒）でループ間隔を上書き（デフォルト 60）
  - 監視は Settings.sqlite_path を使用（環境にかかわらず同じ監視 DB を使用）

- ExecutionEngine を起動（当日セッション処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、API 呼び出しは MockBrokerClient に切替
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します
  - 実行時には data/execution.pid（デフォルト）に PID を書き込みます

- 設定の対話式作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD / --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI / レジーム判定 / ニューススコア（プログラムから呼び出す関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（api_key を引数で渡すことも可）

停止・Kill Switch
- ExecutionEngine の停止
  - data/stop_requested.flag を作成すると run_execution の起動中スレッドは停止処理に入ります
- Kill Switch（システムが危険と判定）
  - KillSwitch は条件が満たされると data/kill.flag を作成します（ExecutionEngine は起動時にこの kill.flag を検出して異常時停止します）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で kill.flag をクリアします（本番では 0 推奨）

ログ
- logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保持）
- アプリケーションからは setup_logging(app_name="execution" 等) を呼び出して使用

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数・.env の読み込みロジック）
  - config_setup.py
    - .env を対話的に作成/更新するウィザード
  - validate_config.py
    - 起動前に設定整合性をチェックする CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py (ログ設定)
    - process_priority.py (プロセス優先度 / CPU affinity)
  - monitoring/
    - monitoring_db.py (SQLite 永続層)
    - system_monitor.py (CPU/メモリ/ディスク/プロセス/データ鮮度)
    - trade_monitor.py (注文ログ監視)
    - risk_monitor.py (ドローダウン / ポジション制限)
    - kill_switch.py (kill.flag 制御)
    - monitoring_engine.py (各モニタを束ねる)
    - alert_manager.py (アラート送信管理) — 実装ファイルあり
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
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - data/  （ランタイム生成ファイルを置く想定）
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - stop_requested.flag / kill.flag / execution.pid など

---

## よくある注意点 / 運用メモ

- KABUSYS_ENV の値:
  - development / paper_trading / live のいずれかのみ有効
  - live は本番扱いのため、LINE 通知等の設定を忘れないこと
- 監視 DB：
  - run_monitoring は環境に関係なく Settings.sqlite_path（本番 sqlite_path）を使用します。監視データを本番と分離したい場合は sqlite_path を別に設定してください
- paper_trading：
  - KABUSYS_ENV=paper_trading 時は broker が MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録されます
- OpenAI：
  - AI 機能を使用するために OPENAI_API_KEY を設定してください（news_nlp, regime_detector など）
  - API 呼び出しはリトライやフェイルセーフを含む実装ですが、コスト・レート制限に注意してください
- ログ出力失敗：
  - logs/ ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみになります。起動時の標準出力やシステムログも確認してください
- Kill Switch と起動時自動クリア：
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（Kill Switch が自動で消えるため）。本番では 0 を推奨します
- DB マイグレーション：
  - monitoring_db.init_monitoring_db() はテーブル作成および軽微なカラム追加マイグレーションを含みます

---

何か特定のセクション（例: system_monitor の内部動作、ExecutionEngine の設定詳細、デプロイ手順 / systemd ユニット例など）について追記・詳細化が必要であれば教えてください。README を目的に合わせて拡張します。