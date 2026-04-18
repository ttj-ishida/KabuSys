# KabuSys — README

このリポジトリは「日本株自動売買システム KabuSys」のコードベースです。  
本 README はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究・監視プラットフォームです。  
主な機能は以下のとおりです。

- 発注実行エンジン（ExecutionEngine）
  - 実際のブローカー（kabuステーション）と連携するか、ペーパートレード用のモックを使用
  - リスク管理（ポジション上限・ドローダウン等）を組み込み
- 監視（Monitoring）
  - システム稼働状況、データ鮮度、注文ログ、リスクイベントの収集とアラート
  - Kill Switch（条件を満たすと Execution を停止）
- ポートフォリオ構築ユーティリティ
  - シグナル選別、重み算出、ポジションサイズ計算、セクター制約など
- リサーチ（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value ファクター等を DuckDB 上で計算
  - IC、将来リターン、統計サマリーなど
- AI モジュール
  - ニュース NLP（OpenAI を用いたセンチメントスコアリング）
  - レジーム判定（MA とマクロニュースの組合せで market_regime を判定）
- 各種ユーティリティ／スクリプト
  - .env ウィザード、設定検証、Paper Trading 検証レポート等

設計方針の例:
- DuckDB / SQLite をデータ層に使用（分析用に DuckDB、監視ログ等に SQLite）
- 本番／ペーパートレードは DB を分離
- ルックアヘッドバイアス対策（date/time の扱いに注意）
- フェイルセーフ設計（API 失敗時はフォールバックして継続）

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 環境設定
  - config_setup.py — .env の対話式ウィザード
  - validate_config.py — 環境設定・config YAML の事前検証
- 監視
  - monitoring/monitoring_db.py — SQLite テーブル作成・永続化 API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py 等
  - monitoring/monitoring_engine.py — 各 Monitor を束ねて定期実行
  - monitoring/kill_switch.py — kill.flag による実行停止
- 発注関連（execution）
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager / OrderRepository / ExecutionEngine / RiskManager / Reconciler
- ポートフォリオ構築（portfolio）
  - portfolio_builder, position_sizing, risk_adjustment
- リサーチ（research）
  - factor_research (momentum/volatility/value)
  - feature_exploration (forward returns, IC, summary)
- AI（ai）
  - news_nlp — ニュースを LLM で評価して ai_scores に書き込み
  - regime_detector — マーケットレジーム判定
- ツール
  - tools/paper_verification_report.py — Paper Trading 結果の検証レポート出力

---

## 前提（依存関係）

最低限必要なもの（例）
- Python 3.9+
- pip
- 外部パッケージ（用途に応じて）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証は任意）
  - (標準ライブラリの sqlite3 は同梱)
- kabuステーション API（本番接続時）
- OpenAI API キー（AI 機能を利用する場合）

依存パッケージはプロジェクトに requirements.txt がない場合は手動でインストールしてください。例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の準備
   - 対話式で作る（推奨）
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成してプロジェクトルートに置く
   - 自動ロード: config.py はプロジェクトルートにある .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番で警告も致命扱いにする: python -m kabusys.validate_config --strict
6. データディレクトリ準備
   - デフォルトで使用するディレクトリ: data/ logs/
   - 必要に応じて .env で `DUCKDB_PATH` や `SQLITE_PATH` を上書き
7. （オプション）OpenAI を利用する場合は OPENAI_API_KEY を環境変数または .env に設定

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV
  - development / paper_trading / live
  - paper_trading の場合、MockBroker を使用し DB は data/paper_trading.db を使用
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, 例: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB, 例: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 機能を利用する場合)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant/partial/never/reject)
- KILL_FLAG_CLEAR_ON_START (起動時 kill.flag を自動クリアするか: 0/1)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔（秒）, デフォルト 60)
- LOG_DIR (ログ出力先、デフォルト logs/)
- その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）

簡単な .env 例（テンプレートとして）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し `data/paper_trading.db` に記録（本番 DB とは分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動を停止
    - 停止は data/stop_requested.flag を書き込むか Kill Switch（監視経由）で行う
    - 実行中は PID が data/execution.pid に書かれる

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings.sqlite_path（監視 DB）に接続し monitoring テーブルを初期化
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60秒）
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行う

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパス指定可

- AI スコアリング（プログラムから呼ぶ）
  - kabusys.ai.score_news を呼び出してニュース NLP を実行（OpenAI API キーが必要）
  - kabusys.ai.regime_detector.score_regime で日次レジーム判定を実行

- ログ
  - logs/<app_name>.log に日次ローテートで出力（デフォルト: logs/）
  - setup_logging(app_name="execution" | "monitoring") により一貫したロギング設定

---

## 停止・Kill スイッチについて

- stop flag:
  - プロジェクトルートの data/stop_requested.flag が存在すると run_execution / run_monitoring のループが安全に終了します（外部からの停止要請に使用）
- kill flag:
  - data/kill.flag は監視モジュールから ExecutionEngine を停止させるための信号として使用されます（KillSwitch が条件を満たすとファイルを書き込む）
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）

---

## DB 初期化・マイグレーション

- monitoring_db.init_monitoring_db が SQLite の監視 DB（system_status / trade_logs / positions / risk_logs / dashboard）を冪等に作成します。起動スクリプト側で自動的に呼び出されます。
- DuckDB は分析用のテーブル（prices_daily / raw_financials / raw_news 等）を前提とするため、データ投入スクリプトや ETL を用意してください（本 README では詳細を省略）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- config_setup.py                — .env ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト

src/kabusys/execution/
- execution_engine.py
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py
(発注関連コンポーネント)

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 開発・運用上の注意点

- KABUSYS_ENV を正しく設定してください（特に live は本番で危険を伴います）。
- .env を絶対にバージョン管理に含めないでください（機密情報が含まれます）。
- Paper Trading は本番 DB と分離されていますが、本番運用する前に必ず validate_config で設定チェックを行ってください。
- OpenAI API 呼び出しはコストとレイテンシが発生するため、運用設計（バッチサイズやリトライ等）に注意してください。
- ログディレクトリが作成できない場合、ファイルログは無効化されコンソールログのみになります（setup_logging の挙動）。

---

## 参考コマンドまとめ（例）

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば、README の英語版、より詳細な運用手順（systemd / supervisor 用ユニット例、Docker 化、CI テスト手順、DB のサンプルデータロード方法など）を追加で作成します。どのドキュメントを優先して作ればよいか教えてください。