# KabuSys

日本株向け自動売買システムのコアライブラリ群です。本リポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などのコンポーネントを含みます。

注意: .env などのシークレットは絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: ブローカークライアントと連携して発注・注文管理を行う。
- 監視（Monitoring）: システム状態・注文状況・リスク監視、Kill Switch による実行停止。
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制約など。
- リサーチ（Research）: DuckDB を用いたファクター計算・IC 計算・特徴量探索。
- AI（AI モジュール）: ニュースセンチメントや市場レジーム判定（OpenAI API を利用）。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、検証ツール等。
- ツール: Paper Trading の検証レポート生成など。

設計方針の一部:
- DuckDB/SQLite をデータ保存に利用。paper_trading モードでは本番 DB と分離。
- .env / 環境変数で構成。Settings クラスで安全にアクセス。
- ログは標準出力 + 日次ローテーション（logs/<app>.log）に出力。
- 実行中のプロセスは優先度を高く設定（できる環境で）。

---

## 主な機能一覧

- Execution
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（Mock を含む）
  - 注文管理・リスクガード（RiskManager 等）

- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（prices_daily 等）
  - 注文・約定ログの監視（滞留注文、約定異常）
  - リスク監視（ドローダウン、ポジション数上限）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み Execution を停止）
  - ログ・監視 DB (SQLite) の初期化・マイグレーション

- Portfolio
  - 候補選定（スコア順）
  - 等金額/スコア重み/リスクベースの配分
  - セクター上限適用、レジーム乗数

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ

- AI
  - ニュースを OpenAI でセンチメント評価し ai_scores に書き込み
  - マクロニュース + MA200 乖離を合成した市場レジーム判定

- ツール
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提:
- Python 3.9+ を推奨
- 必要なパッケージ: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（config 検証の詳細表示に必要）など

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
     （requirements.txt がない場合は duckdb/psutil/openai 等を個別にインストール）

3. .env を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に自分で作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（よく使うもの）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB (data/paper_trading.db)
     - LOG_LEVEL — INFO 等
     - OPENAI_API_KEY — AI 機能を使う場合

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. ディレクトリ作成（必要に応じて）
   - data/ と logs/ は自動作成されることが多いですが、権限や配置に応じて事前作成しておくと安全です。

---

## 使い方（起動・ツール）

基本的にはパッケージモジュールとして起動します（-m）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - run_monitoring は monitoring 用の SQLite（settings.sqlite_path）を本番/環境にかかわらず使用します。
    - 起動時にプロセス優先度を "high" に設定しようとします（環境により失敗する場合あり）。

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
    - 実行エンジンは data/execution.pid に PID を書きます（設定により変更可能）。
    - 停止制御: data/stop_requested.flag が存在すると起動やループ中に停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定可）
  - 生成される指標: 稼働率、注文成功率、送信率、レイテンシ（P95 など）と PASS/FAIL 判定

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- AI 関連（プログラムから呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - いずれも OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

停止・Kill スイッチ関連:
- run_monitoring / run_execution を手動で停止するにはプロジェクトルートの data/stop_requested.flag を作成します（存在を検出して安全に終了します）。
- システム側で Kill Switch（ドローダウン等で自動発動）を確認したい場合は data/kill.flag をチェックしてください。Kill Switch は起動中の ExecutionEngine に停止シグナルを与えます。
- kill.flag を手動で削除するには: rm data/kill.flag

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI API を使う場合に必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" でクリア）

自動ロード:
- config.Settings モジュールはプロジェクトルートの .env および .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にすると無効化可能）。

---

## ディレクトリ構成（主なファイル/モジュール）

(ルート)/
- config/ ........................................ 設定テンプレート YAML 等（system_config.yaml など）
- data/ .......................................... 実行時データ: monitoring.db, paper_trading.db, kill.flag, execution.pid など
- logs/ .......................................... ログ出力先（デフォルト）
- src/kabusys/
  - __init__.py .................................. パッケージ定義
  - config.py .................................... 環境変数 / Settings
  - config_setup.py .............................. .env 対話ウィザード
  - validate_config.py ........................... 起動前設定検証ツール
  - run_monitoring.py ............................ Monitoring ポーリングループ
  - run_execution.py ............................. ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py ........................... ログ設定ユーティリティ
    - process_priority.py ........................ プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py .......................... SQLite テーブル管理 / 永続化ラッパ
    - system_monitor.py .......................... システム状態・データ鮮度監視
    - trade_monitor.py ........................... (注文監視ロジック)
    - risk_monitor.py ............................ ドローダウン・ポジション監視
    - kill_switch.py ............................. Kill Switch 実装
    - monitoring_engine.py ........................ 各 Monitor を束ねるエンジン
    - alert_manager.py ........................... (通知管理)
  - execution/ .................................. 実行エンジン関連（broker, order_manager 等）
  - portfolio/ .................................. portfolio_builder, position_sizing, risk_adjustment
  - research/ ................................... factor_research, feature_exploration
  - ai/
    - news_nlp.py ................................ ニュースセンチメントスコアリング
    - regime_detector.py ........................ レジーム判定
  - tools/
    - paper_verification_report.py ............... Paper Trading の検証レポート

---

## 開発上の注意・トラブルシュート

- 必須環境変数が未設定だと validate_config や Settings プロパティでエラーになります。特に JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須です。
- .env は自動ロードされますが、テストや CI でロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）を見て安全に終了します。これを作成することで外部から停止できます。
- AI 機能は OpenAI API への依存とレート制限に注意。API エラー時はフェイルセーフでスコアをスキップまたは中立値へフォールバックする実装になっています。
- DuckDB / SQLite のファイルパスは Settings で制御します。paper_trading モードでは paper_sqlite_path を使用して本番データと分離します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ログディレクトリの書き込み権限を確認してください）。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 手動停止（サービスループに対して）:
  - touch data/stop_requested.flag
- 手動で Kill Switch を削除（注意して実行）:
  - rm data/kill.flag

---

必要であれば README にサンプル .env のテンプレートや system_config.yaml の生成手順、ユニットテストの実行方法、CI 設定例などを追加できます。どの情報を優先して追記しましょうか？