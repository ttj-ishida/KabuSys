# KabuSys

日本株自動売買システムの Python コードベース用 README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / リサーチ基盤です。  
主な機能は次のとおりです。

- 戦略用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）による発注管理（paper/live 切替対応）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ニュース NLP を用いた AI スコアリング（OpenAI）
- Paper Trading 向け検証レポート生成ツール
- .env 対話式ウィザードと設定検証 CLI

設計上の特徴：
- DuckDB（分析用）と SQLite（監視 / 発注履歴等）を併用
- 環境変数ベースの設定（.env の自動読み込み / 対話式生成サポート）
- OpenAI と連携した NLP 機能（オプション）
- テストしやすい純粋関数群（ポートフォリオ・リスク計算など）

---

## 主な機能一覧（抜粋）

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading のときは MockBroker を使い、data/paper_trading.db に記録
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は環境に関わらず production の sqlite_path を使用
- 設定関連
  - config_setup.py: .env 対話式ウィザード（初期作成 / 更新）
  - validate_config.py: 起動前の設定検証 CLI（--strict オプションあり）
- 分析 / 研究
  - research.factor_research: モメンタム / ボラティリティ / バリュー等の計算
  - research.feature_exploration: 将来リターン、IC、統計サマリ等
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定、等重・スコア重み算出
  - portfolio.position_sizing: 株数決定、単元丸め、aggregate cap 調整
  - portfolio.risk_adjustment: セクター上限、レジーム乗数
- AI / ニュース
  - ai.news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に保存
  - ai.regime_detector: ETF（1321）MA とマクロニュースを合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成 CLI

ユーティリティ:
- utils.logging_setup: 統一的なロギング設定（stdout + 日次ローテートファイル）
- utils.process_priority: プロセス優先度 / CPU affinity 設定

---

## 前提（依存関係）

※ここに示す依存はコード中に出てくる主要ライブラリです。実際の requirements.txt を参照してください。

- Python 3.10+（型ヒントで X | Y 構文を使用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml のパース検証を行う場合）
- sqlite3（標準ライブラリ）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - 例: git clone <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要なパッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があればそれを使用: pip install -r requirements.txt）

4. .env ファイルを生成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト data/paper_trading.db）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

6. データ / ログ ディレクトリの準備（通常は自動作成されます）
   - data/ 、 logs/ が想定されます。権限等に注意してください。

---

## 使い方（起動 / CLI）

基本的にはモジュールとして Python から起動できます。

- 実行エンジン（ExecutionEngine）起動
  - 例（本番や paper_trading の切替は KABUSYS_ENV で制御）:
    - export KABUSYS_ENV=development
    - python -m kabusys.run_execution
  - Paper Trading:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - このモードでは MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。

- 監視プロセス起動（SystemMonitor）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は常に settings.sqlite_path（production 想定の monitoring.db）を使用します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（SQLite DB パス; 環境変数 PAPER_TRADING_SQLITE_PATH を上書き）

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit(1)）になります

ログ:
- logs/ ディレクトリに <app_name>.log が日次ローテーションで出力されます（デフォルトで 30 日分保持）。
- console ログは stdout に出ます。

停止 / Kill スイッチ:
- data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送れます（KillSwitch 機能）。
- run_* スクリプトは data/stop_requested.flag の存在を確認して安全停止します。
- PID 管理: data/execution.pid 等の PID ファイルを使用します。

設定の一例（環境変数 / .env）:
- KABUSYS_ENV=development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...  # ai 機能を利用する場合
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- MONITOR_POLL_INTERVAL=30

注意:
- run_monitoring は Monitoring 用の sqlite DB（settings.sqlite_path）を用いるため、環境に依らず監視は同じ DB にログを残します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用し本番 DB と分離します。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は src/kabusys 以下の主要ファイル・モジュールの抜粋説明です。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数の集中管理・検証）
    - .env の自動読み込みロジック（プロジェクトルート検出）
  - config_setup.py
    - .env 作成ウィザード（対話式）
  - validate_config.py
    - 起動前検証 CLI（必須 env のチェック、config/*.yaml の存在確認 など）
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - logging_setup.py（ロギング初期化: stdout + 日次ローテート）
    - process_priority.py（プロセス優先度 / CPU affinity 設定）
  - portfolio/
    - portfolio_builder.py（候補抽出・重み付け）
    - position_sizing.py（株数計算・集約キャップ）
    - risk_adjustment.py（セクター上限・レジーム乗数）
  - research/
    - factor_research.py（モメンタム、ボラ、バリュー等）
    - feature_exploration.py（将来リターン、IC、統計）
  - ai/
    - news_nlp.py（ニュースを LLM でスコアリングして ai_scores に書込）
    - regime_detector.py（ETF MA とマクロニュースを合わせてレジーム判定）
  - monitoring/
    - monitoring_db.py（SQLite への永続化層）
    - system_monitor.py（CPU/メモリ/ディスク/データ鮮度/プロセス監視）
    - risk_monitor.py（ドローダウン／ポジション上限監視）
    - trade_monitor.py（trade_logs の監視） ※詳細はコード参照
    - monitoring_engine.py（複数 monitor を束ねる）
    - kill_switch.py（kill.flag の作成 / 管理）
    - alert_manager.py（LINE 等の通知ラッパ — 実装を確認してください）
  - tools/
    - paper_verification_report.py（ペーパートレード検証レポート）
  - data/ （実行時に生成／使用するファイル）
    - monitoring.db（SQLITE_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - kill.flag / stop_requested.flag / execution.pid など
  - logs/ （log ファイルが出力される）

（上記は主要モジュールのサマリです。細かい実装は各ソースファイルを参照してください）

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では .env の値や kill flag の設定に十分注意してください。validate_config は live 時に追加警告を出します。
- OpenAI を使う機能は API キーとコストに注意して運用してください。エラー時はフェイルセーフでスコアを 0 にする等の実装になっていますが、想定外の挙動には注意が必要です。
- ログディレクトリや DB ファイルの権限、ディスク容量を監視してください。monitoring もディスク使用率等を確認しますが、十分な余裕が必要です。
- 単体テストや統合テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 env ロードを無効化できます。

---

README は以上です。必要であれば次の内容も追加します：
- 実行時の具体的な systemd / supervisor サービスユニット例
- CI / テスト実行コマンド
- 主要クラス（ExecutionEngine / OrderManager / BrokerClientFactory など）の簡易アーキテクチャ図

どれが必要か教えてください。