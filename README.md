# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）。  
このリポジトリは以下の主要機能を含み、実運用（live）およびペーパートレード（paper_trading）に対応する設計になっています。

## プロジェクト概要
KabuSys は、銘柄選定・ポートフォリオ構築、発注エンジン、監視（モニタリング）、研究（ファクター計算）、およびニュース NLP / レジーム判定を備えた日本株自動売買基盤です。  
主に以下の責務を持つコンポーネントで構成されています。

- ExecutionEngine: ブローカーとやり取りして注文管理・約定処理を行う（paper_trading では MockBroker を使用）。
- Monitoring: システム健全性・注文状態・リスク指標を定期ポーリングしてログ・アラート・Kill Switch を管理。
- Portfolio: 候補選定、配分重み計算、ポジションサイズ決定、セクター制約・レジーム補正。
- Research: DuckDB 上でファクター計算・特徴探索・将来リターン計算などを実行。
- AI: ニュースを LLM（OpenAI）でセンチメント評価し、レジーム判定に利用。
- Utils: ロギング設定・プロセス優先度など運用ユーティリティ。
- CLI ツール: .env 作成ウィザード、設定検証、Paper Trading 検証レポート生成など。

## 主な機能一覧
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring: SystemMonitor を定期実行（MONITOR_POLL_INTERVAL で間隔設定可能）
- 設定関連
  - config_setup: .env を対話的に作成/更新するウィザード
  - validate_config: .env と config/*.yaml の起動前チェック
  - Settings クラス: 環境変数の集中管理・バリデーション
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・プロセスの死活・データ鮮度を監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限を監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化
  - MonitoringEngine: 複数の Monitor を束ねてポーリング・アラート送信
- 発注ロジック（Execution）
  - ブローカークライアント分離（本番/モック）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等
- ポートフォリオ構築（純粋関数）
  - 候補選択、等金額・スコア加重、リスクベースの株数決定、セクターキャップ、レジーム乗数
- 研究（Research）
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - forward returns、IC（Spearmanランク相関）、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を LLM でセンチメント付与して ai_scores に書き込む
  - regime_detector.score_regime: ma200 とマクロニュースを合成して market_regime を判定
- 運用ツール
  - tools.paper_verification_report: Paper Trading DB を集計し検証レポートを出力

## セットアップ手順（開発・運用共通の流れ）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 必要な主なライブラリ: duckdb, psutil, openai, (PyYAML は設定検証で任意)

3. .env の作成（ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を対話式で設定します。
   - 生成された .env は絶対にコミットしないでください（機密情報が含まれるため）。

4. 設定の検証
   - python -m kabusys.validate_config
   - 必要なら --strict を付けて警告もエラー扱いにできます。

5. データディレクトリ作成（自動作成される場合もありますが、明示的に作ると権限問題を回避できます）
   - mkdir -p data logs

6. 実行準備（OpenAI を使う機能を利用する場合）
   - 環境変数 OPENAI_API_KEY を設定（.env に書き込むか環境変数としてセット）

## 使い方（主要コマンド）
- ExecutionEngine を起動（本番またはペーパーは .env の KABUSYS_ENV で制御）
  - python -m kabusys.run_execution
  - ペーパートレードの場合、KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、データは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に保存されます。

- Monitoring を起動（常駐プロセスとして動作）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（デフォルト 60）
  - python -m kabusys.run_monitoring

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前に推奨）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになる

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能

- Research / AI モジュール（Python API）
  - DuckDB 接続を渡して関数を呼び出す（例: research.calc_momentum）
  - AI スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key 省略時は環境変数 OPENAI_API_KEY を使用

## 主要な環境変数
（一部抜粋。詳細は kabusys.config.Settings を参照）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行管理ファイルパス
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI を使う機能で参照される API キー
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト instant）

## 運用上の注意
- monitor / execution は stop フラグファイル（data/stop_requested.flag）や kill.flag（data/kill.flag）で制御されます。KillSwitch により自動で kill.flag が書かれる場合があります。
- ログは標準出力（stdout）と日次ローテートされたファイル（logs/<app_name>.log）へ出力されます。
- 本番（live）モードでは設定の検証を慎重に行ってください（validate_config は live 時に警告を出します）。
- OpenAI 呼び出しは外部 API 依存のため、API 失敗時はフェイルセーフ（スコアを 0 にする等）で設計されている箇所が多いですが、運用時は API キー管理とリトライ設定を確認してください。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下のおもなファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義
  - __version__ = "0.1.0"
  - config.py — Settings クラス（環境変数読み込み・自動 .env ロード・バリデーション）
  - config_setup.py — .env 対話ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成（CLI）
  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視永続化層
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定監視（実装ファイルは存在）
    - risk_monitor.py — ドローダウン・保有数監視
    - kill_switch.py — Kill Switch（flag ファイル生成）
    - monitoring_engine.py — 複数 Monitor を束ねる実行エンジン
    - alert_manager.py — 通知管理（LINE など、実装参照）
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周りコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数計算・スケーリング
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄ごとスコア付与
    - regime_detector.py — ma200 + マクロニュースを合成して市場レジーム判定

（実際のリポジトリには上記以外にも補助モジュール・実装ファイルが含まれます。詳しくはソースツリーを参照してください。）

## 開発・拡張のヒント
- DuckDB を用いて分析テーブル（prices_daily, raw_financials, raw_news 等）を構築し、research / ai モジュールはその DuckDB 接続を受け取って実行する設計です。データ準備が前提となります。
- AI（OpenAI）呼び出し部分はリトライやレスポンス検証を丁寧に行うよう実装済みです。テスト時は _call_openai_api をパッチして振る舞いをシミュレートできます。
- ポートフォリオ構築・ポジションサイズ決定は純粋関数として実装されているため、単体テストを作りやすいです。

---

README に含めてほしい追加の項目（例: サンプル .env.example、requirements.txt の中身、データベース初期化スクリプト、起動の systemd / Supervisor サンプルなど）があれば教えてください。必要に応じて追記します。