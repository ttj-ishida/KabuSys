# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買システム KabuSys のコードベースです。  
ここではプロジェクトの概要、主要機能、セットアップと起動手順、使い方の例、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下を想定したモジュール型の自動売買フレームワークです。

- データ収集 / DuckDB による時系列データ管理（prices_daily, raw_financials, raw_news 等）
- ファクター計算・特徴量解析（research モジュール）
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- ExecutionEngine による発注管理（本番 / ペーパートレードをサポート）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- LLM を用いたニュース NLP / レジーム判定（OpenAI API を利用するモジュール）
- ペーパートレードの検証レポート生成ツール

設計方針の例：重い処理は DuckDB や SQLite に保存してオフライン解析可能、API キー等は .env 管理、ペーパートレードは本番 DB と分離。

---

## 主な機能一覧

- 実行（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカー抽象化（MockBrokerClient を用いるペーパートレード対応）
  - ExecutionEngine: 発注・リスク制御・再整合（reconciler）など

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度の監視
  - TradeMonitor / RiskMonitor / MonitoringEngine：滞留注文、約定異常、ドローダウン、ポジション上限の監視とアラート
  - KillSwitch（data/kill.flag）により実行エンジンを停止する仕組み

- ポートフォリオ構築
  - 候補選定（score ソート）
  - 等金額・スコア重み付け・リスクベースの株数決定
  - セクターキャップ適用、レジーム乗数

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）等の解析ユーティリティ

- AI / NLP
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini など）で評価して ai_scores に格納
  - マクロニュース + ETF MA を使った市場レジーム判定

- ツール
  - 設定ウィザード（.env 作成）: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - ペーパートレード検証レポート生成: kabusys.tools.paper_verification_report

---

## 動作要件（推奨）

- Python 3.10 以上（ソースで | 型ヒント等を使用）
- 必要パッケージの例:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のため任意）
- SQLite（標準ライブラリに含まれます）

※ requirements.txt は本リポジトリに含まれていない想定のため、環境に合わせて上記パッケージをインストールしてください。

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - そのほか（任意/デフォルトあり）:
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE 等

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

6. データディレクトリとログディレクトリの作成（自動作成されることが多いが手動でも可）
   - mkdir -p data logs

---

## 使い方（起動 / 実行コマンド）

すべてモジュールとして起動できます（プロジェクトルートで実行）。

- ExecutionEngine を起動（本番・ペーパーいずれも内部で切替）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID を書き込みます
  - 停止シグナルは data/stop_requested.flag（run_execution と monitoring の停止フラグ）で行えます
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、data/paper_trading.db に記録されます

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で変更可能
  - 監視は本番 sqlite_path を常に使用（Monitoring は KABUSYS_ENV に依存せず本番 DB を参照）
  - 停止フラグ: data/stop_requested.flag を置くと監視ループは終了します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB を変更可能

- AI 関連（内部 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OpenAI API キーが必要です（OPENAI_API_KEY 環境変数 または api_key 引数）

---

## 監視 / 停止関連（Kill Switch, Flags）

- Kill Switch（自動停止判定）
  - 条件（例）: ドローダウン閾値超過、ポジション数上限超過など
  - 触発されると data/kill.flag を作成して ExecutionEngine に停止指示を出します（冪等）
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は自動クリアされる設定があります（本番では 0 推奨）

- 手動停止
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが検知して終了します
  - run_execution は data/execution.pid に書いた PID を確認して動作します

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用・動作設定:
- KABUSYS_ENV — execution モード（development, paper_trading, live）。デフォルト：development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト instant）

注意: .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。

---

## ロギング

- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- デフォルトでは console (stdout) と logs/<app_name>.log に日次ローテーションで出力されます（30 日保持）。
- log_dir は環境変数 LOG_DIR または引数で上書き可能。

---

## 開発・デバッグのヒント

- Python 型ヒントや純粋関数が多く、ユニットテストでのモジュール分離が容易です。
- OpenAI 呼び出し箇所は内部でラップされており、テスト時は _call_openai_api をモックする設計です（unittest.mock.patch など）。
- DuckDB / SQLite のスキーマ初期化やマイグレーションは monitoring_db.init_monitoring_db 等に実装されています。
- 設定検証ツールで .env と config/*.yaml の有無/簡易パースをチェックできます（PyYAML がある場合は YAML 内容も検証）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - config.py                  — Settings（環境変数 / .env の自動読み込み）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - utils/
    - logging_setup.py         — 共通ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py         — （コードベース内に存在）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         — （アラート送信ロジックがある想定）
  - execution/
    - execution_engine.py      — ExecutionEngine 実装（起動ロジック参照）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py

（リポジトリ全体のファイル一覧は実際のツリーを参照してください）

---

## よくある運用ワークフロー

1. .env を作成（config_setup）→ validate_config でチェック
2. データを DuckDB にロード（データパイプライン）→ research モジュールでファクター計算
3. 実運用前に paper_trading で ExecutionEngine を走らせて動作確認
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 動作確認後、必要に応じて paper_verification_report を使ってレポートを作成
4. 監視（run_monitoring）を起動して常時監視・Kill Switch を有効にする

---

## 安全上の注意

- KABUSYS_ENV=live の設定は本番発注につながります。必ず設定・鍵類・LINE 通知設定を慎重に確認してください。
- .env に含まれるすべての機密情報は Git などにコミットしないでください。
- 本番で KILL_FLAG_CLEAR_ON_START=1 を設定することは推奨されません（Kill Switch を自動消去してしまうため）。

---

必要であれば、README に以下を追記できます。
- 詳細な API ドキュメント（関数シグネチャ・戻り値）
- 事前用意すべきデータ（DuckDB のテーブルスキーマ例）
- サービス化（systemd / supervisor / Docker）手順
- テスト実行方法（pytest など）

追記希望があれば、どの項目を深掘りするか教えてください。