# KabuSys

日本株向けの自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、バックテスト・リサーチ・発注・監視・ペーパートレード等を含む
日本株自動売買プラットフォーム「KabuSys」の実装です。
モジュールはなるべく純粋関数／副作用分離で設計されており、実運用向けの制御（ログ、
プロセス優先度、Kill Switch、監視 DB）や OpenAI を用いた NLP / レジーム判定などの
補助機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
- ファイル・ディレクトリ構成（主要ファイル）
- 付記（注意点）

---

## プロジェクト概要

KabuSys は次のようなコンポーネントを含む自動売買システムです。

- 発注実行エンジン（ExecutionEngine）: ブローカークライアントを介して発注を行う
- 監視（Monitoring）: システム状態・注文状況・リスクのポーリング監視とアラート発行
- ペーパートレード: 実口座とは分離した専用データベースでの試験運転
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクターキャップ等
- リサーチ: ファクター計算、将来リターン、IC 等の解析ユーティリティ（DuckDB 前提）
- AI 支援: ニュースセンチメント評価（OpenAI）・市場レジーム判定
- 各種ユーティリティ: 設定読み込み (.env), ロギング設定, プロセス優先度設定 等

設計方針の一部:
- 設定は .env / 環境変数経由（config_setup.py で対話的に作成可能）
- 本番用 DB（monitoring.sqlite / duckdb）とペーパートレード DB は明確に分離
- LLM 呼び出しは API キー必須、失敗時は安全側のフォールバック処理を行う

---

## 機能一覧

主な機能：
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔設定可）
- 設定管理
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: .env や config/*.yaml の事前検証
- 監視（monitoring）
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスチェック
  - trade_monitor: 注文滞留・約定異常検出（実装参照）
  - risk_monitor: ドローダウン・ポジション上限監視
  - kill_switch: 監視に基づく kill.flag 書き込み（ExecutionEngine 停止トリガ）
  - monitoring_db: SQLite を使った永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring_engine: 各モニタを束ねて周期実行、アラート連携
- ポートフォリオ（portfolio）
  - 銘柄候補選定、等重/スコア加重、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ（research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns, IC, summary）
- AI（ai）
  - news_nlp.score_news: OpenAI でニュース記事を集約し銘柄ごとにセンチメントスコア化、ai_scores に保存
  - regime_detector.score_regime: ETF とマクロ記事を組合せて市場レジーム判定・保存
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・成功率・レイテンシ等）

ユーティリティ:
- utils/logging_setup: stdout + 日次ローテートファイルの標準ロギング初期化
- utils/process_priority: Windows/Linux の差を吸収したプロセス優先度/CPU affinity 設定
- config: .env 自動読込（プロジェクトルート検出）、Settings クラスで各種設定を取得

---

## セットアップ手順

前提:
- Python 3.9 以上を推奨（型ヒント・modern パッケージを想定）
- system には duckdb, psutil, openai などのパッケージが必要

1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML を入れると validate_config が YAML の中身も検証します:
     - pip install pyyaml
4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定
5. 設定の検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正、--strict をつけると警告も失敗扱いになります
6. データディレクトリ・ログディレクトリ
   - デフォルトでは `data/` に DB（monitoring.db, paper_trading.db）や pid/flag ファイルが作られます
   - ログはデフォルト `logs/` に app_name.log として日次ローテーションで出力されます

---

## 使い方

基本的な起動・操作方法を示します。

- ExecutionEngine（発注エンジン）起動
  - 通常:
    - python -m kabusys.run_execution
  - KABUSYS_ENV を切り替える:
    - export KABUSYS_ENV=paper_trading
    - -> paper_trading モードでは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）にログ保存します
  - 停止:
    - 外部から停止要求を出すには `data/stop_requested.flag` を作成してください（run_execution はこの存在を監視して停止します）
    - 監視からの kill（リスクトリガ）により `data/kill.flag` が書き込まれると ExecutionEngine は停止されます
  - PID ファイル:
    - 実行時に pid ファイルを保持（Settings.pid_file_path。デフォルト data/execution.pid）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 短いポーリング間隔で動かす場合は環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごとにポーリング
  - 監視は Settings.env に依らず本番 sqlite_path を使用して監視 DB を初期化します
  - 停止:
    - `data/stop_requested.flag` が検出されるとポーリングループを終了します

- .env の対話的作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱う

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（OpenAI 必須）
  - ニュースセンチメント付与:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
      - conn は duckdb 接続オブジェクト
      - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - レジームスコア算出:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ロギング:
- すべての起動エントリポイントでは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出しています
- デフォルト: stdout と `logs/<app_name>.log`（日次ローテート、30日保持）

停止フラグの種類（運用上の注意）:
- data/stop_requested.flag
  - 外部から「プロセス全体を終了してほしい」要求を与えるためのフラグ
  - run_execution / run_monitoring の両方がチェックします
- data/kill.flag
  - 監視の KillSwitch（リスクトリガ）が書き込むフラグ
  - 主に ExecutionEngine を即座に停止させるために使います
- Kill Switch の自動クリア
  - Settings.kill_flag_clear_on_start が "1" の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では推奨されません）

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys/` 配下の主要モジュールと役割です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス、.env 自動読み込みロジック
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
      - 統一ロギングの初期化
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定（psutil 使用）
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py  (存在。注文監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信インターフェース)
  - execution/
    - ブローカー工場・エンジン・注文管理等（run_execution から起動）
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
  - data/
    - pipeline.py, stats.py, 等（DuckDB を前提にしたデータ処理）

（プロジェクト全体のファイル一覧はリポジトリのツリーを参照してください）

---

## 付記 / 運用上の注意

- .env は機密情報（API トークン等）を含むため Git へコミットしないでください。
- validate_config で事前チェックを行い、本番（KABUSYS_ENV=live）では特に LINE 通知設定等を確認してください。
- OpenAI 利用:
  - OPENAI_API_KEY を環境変数に設定するか、関数に直接 api_key を渡してください。
  - LLM 呼び出しはネットワークやレート制限を受けるため、エラー処理（リトライ）とフェイルセーフが組み込まれていますが、API 使用料には注意してください。
- DB のバックアップ・アクセス権限、ログローテーション設定などは運用環境に合わせて調整してください。
- プロセス優先度操作や CPU affinity の設定は管理者権限を要する場合があります。設定に失敗した場合は警告を出してスキップします。

---

必要があれば、README に含める以下の追加情報を作成します：
- 開発環境でのユニットテスト実行方法
- 具体的な config/*.yaml のテンプレート説明
- 各モジュール（ExecutionEngine / OrderManager / BrokerClient）の詳細 API ドキュメント

ご希望があれば追加で追記します。