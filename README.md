# KabuSys — README

日本株自動売買のためのライブラリ / 実行スクリプト集です。  
このリポジトリは、シグナル算出（リサーチ）・ポートフォリオ構築・発注（Execution）・監視（Monitoring）・AI（ニュース NLP / レジーム判定）などの主要機能を含みます。  
以下はプロジェクトの概要、機能一覧、セットアップ手順、使い方、主要ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する Python モジュール群と起動スクリプト群です。主な目的は以下です。

- DuckDB / SQLite を用いたデータ処理・永続化
- ファクタ計算や特徴量探索などのリサーチ機能
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine による（実運用 / ペーパートレードの）発注処理
- Monitoring によるシステム・注文・リスクの定期チェックと Kill Switch
- OpenAI を利用したニュースセンチメント（AI スコアリング）・市場レジーム判定
- 簡易 CLI ツール（設定ウィザード・設定検証・ペーパートレード検証レポート生成）

設計方針として、ルックアヘッドバイアスの回避・フェイルセーフ（API 失敗時は継続）・冪等性を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルートに基づく）
  - 設定ウィザード: python -m kabusys.config_setup
  - 起動前検証: python -m kabusys.validate_config

- 発注・実行（Execution）
  - ExecutionEngine（EngineConfig 経由で起動）
  - BrokerClientFactory: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に分離
  - OrderManager / OrderRepository / Reconciler / RiskManager

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor: 注文ログの監視（滞留注文・約定異常等）
  - RiskMonitor: ドローダウンやポジション上限の監視と通知 / ログ記録
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine / run_monitoring.py による定期ポーリング

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等重み、スコア加重）
  - 単元株丸め・リスクベースの株数決定（calc_position_sizes）
  - セクターキャップ適用、レジーム乗数（calc_regime_multiplier）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を集約して LLM に投げ、銘柄ごとにスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせて日次レジーム判定

- ツール
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境を用意
   - 推奨: Python 3.9+

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証でオプション）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements ファイルがある場合はそれを使ってください（本サンプルには含まれていません）。

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成 (.env.example を参考に)
     - 重要な環境変数:
       - JQUANTS_REFRESH_TOKEN (必須)
       - KABU_API_PASSWORD (必須)
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
       - OPENAI_API_KEY（AI 機能を使う場合）
       - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
       - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
       - LOG_LEVEL（DEBUG/INFO/...）
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
       - PAPER_FILL_MODE（paper_trading 時の fill 動作: instant|partial|never|reject）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは logs/ と data/ にファイルを置きますが、起動時に自動作成されます。

---

## 使い方（起動 / 主要コマンド）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）
    - 停止フラグ: data/stop_requested.flag があると起動せず終了します。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒, 1以上）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書きます。
    - stop フラグ: data/stop_requested.flag によりループを停止します。
    - プロセス優先度を high に設定するユーティリティを呼びます（psutil を利用）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- ライブラリとしての利用（例）
  - ポートフォリオ関数の呼び出し:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: execution モード（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（1/0）

---

## ログ / ファイル / DB の取り扱い

- ロギング
  - デフォルトで stdout に出力し、日次ローテーションで logs/<app_name>.log に保存します（TimedRotatingFileHandler）。
  - ログディレクトリが作成できない場合はコンソールのみで継続します。

- PID / フラグファイル
  - data/execution.pid: Execution の PID（デフォルト、変更可）
  - data/stop_requested.flag: run_monitoring / run_execution が監視する停止フラグ
  - data/kill.flag: KillSwitch が書き込む停止シグナル（Execution 側はこれを検知して停止）

- DB
  - DuckDB: 分析用データベース（デフォルト data/kabusys.duckdb）
  - SQLite:
    - monitoring.db: system_status / trade_logs / positions / risk_logs / dashboard など（init_monitoring_db でスキーマ作成・マイグレーション）
    - paper_trading.db: paper_trading 用（KABUSYS_ENV=paper_trading の Execution はこちらを使用）

---

## 注意点 / ベストプラクティス

- KABUSYS_ENV=live の設定は本番リスクがあります。validate_config は live 時に追加の警告を出します。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも同様の注意があります）。
- OpenAI を用いる処理は API エラー（429 / タイムアウト / 5xx）に対してリトライを行いますが、API キーが未設定だと機能しません。AI 機能は外部 API を利用するため課金やレート制限があります。
- Monitoring はデフォルトで本番の monitoring DB を使用するため、テスト時は環境変数でパスを変更して分離してください。
- MONITOR_POLL_INTERVAL は 1 秒以上の整数を指定してください。不正値はデフォルト（60秒）にフォールバックします。
- process priority / cpu affinity の設定は psutil を利用します。実行環境によっては権限不足で設定が失敗するためワーニングに留まります。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 配下の主要ファイルと説明です（リポジトリルートが src/ を含む想定）。

- src/kabusys/
  - __init__.py — パッケージ宣言、バージョン
  - config.py — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力 CLI
  - utils/
    - logging_setup.py — 共通ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite スキーマ / 永続化層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 注文監視（存在）
    - risk_monitor.py — リスク監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — アラート送信管理（LINE など）（存在）
  - execution/
    - execution_engine.py — ExecutionEngine 実装（存在）
    - broker_factory.py — Broker クライアント生成（MockBroker 等）
    - order_manager.py — 注文管理
    - order_repository.py — 注文データ永続化
    - reconciler.py — ブローカーとローカル状態の照合
    - risk_manager.py — 発注時リスク制御
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・丸め・キャップ
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等ファクター計算
    - feature_exploration.py — 将来リターン/IC/統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI を利用）
    - regime_detector.py — 市場レジーム判定（OpenAI 利用）
  - data/ (実行時に生成されることが多い)
    - monitoring.db (SQLite のデフォルト)
    - paper_trading.db (paper_trading のデフォルト)
    - stop_requested.flag, kill.flag, execution.pid など

---

## トラブルシューティングのヒント

- validate_config でエラーが出る場合は .env の必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を確認してください。
- OpenAI 関連の機能が失敗したら OPENAI_API_KEY が設定されているか、API のレート制限や課金状況を確認してください。
- ログが出力されない／ファイルが作成されない場合は LOG_DIR の書き込み権限を確認してください。権限がなければコンソールのみで継続します。
- psutil を使ったプロセス優先度設定は OS 権限に依存します（特に nice の負の値や Windows のクラス変更）。失敗しても警告を出して続行します。

---

本 README はコードベース（主要モジュール）の要点をまとめたものです。詳細は各モジュールの docstring / ソースコードを参照してください。必要であれば、特定コンポーネント（例: ExecutionEngine の設定項目や RiskManager のパラメータ）の詳細説明ドキュメントも作成します。