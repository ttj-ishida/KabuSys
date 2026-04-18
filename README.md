# KabuSys

日本株向け自動売買システムのライブラリ群 / 実行スクリプト群です。本リポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・ポジションサイジング、リサーチ（ファクター計算）や AI を使ったニュース評価などのコンポーネントで構成されています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存関係
- セットアップ手順
- 使い方（起動 / スクリプト）
- 環境変数 / .env の取り扱い
- 停止・Kill Switch の仕組み
- ディレクトリ構成（主要ファイル）
- 補足（デバッグ / 開発メモ）

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群です。主要な責務は次のとおりです。

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由での注文管理、リスク制御、リコンサイル（再整合）など。
- 監視（Monitoring）：システム状態、注文・約定ログ、リスク（ドローダウンやポジション数）を定期的にチェックしてログおよびアラート、必要なら停止フラグを発行。
- ポートフォリオ構築：シグナル選別、重み付け、ポジションサイジング（単元株丸め、利用可能資金に基づくスケーリングなど）。
- リサーチ：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ。
- AI モジュール：OpenAI（gpt-4o-mini など）を利用したニュースセンチメント評価・市場レジーム判定。
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザードや検証 CLI、検証レポート生成ツールなど。

設計方針として、実行スクリプトとライブラリの分離、DB（SQLite / DuckDB）による永続化、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- 設定ウィザード: python -m kabusys.config_setup による .env の対話式生成/更新
- 設定検証: python -m kabusys.validate_config による環境変数 / config/*.yaml の事前チェック
- 発注実行: python -m kabusys.run_execution で ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードが可能）
- 監視ループ: python -m kabusys.run_monitoring で SystemMonitor を定期実行（MONITOR_POLL_INTERVAL で間隔を調整）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report（期間指定可）
- ポートフォリオ構築: 候補選定、等金額/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
- ポジションサイジング: risk_based / equal / score による株数計算、単元株丸め、aggregate cap スケーリング
- AI: ニュースセンチメントスコア（ai_scores テーブル）と市場レジーム判定（market_regime テーブル）
- ログ出力: 統一的な logging 設定（コンソール + 日次ローテートファイル）
- プロセス優先度 / CPU affinity 制御（psutil を使用）

---

## 前提・依存関係

- Python 3.10 以上（| 型結合等を使用）
- 必須ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
- 任意 / 追加:
  - PyYAML（validate_config による config/*.yaml のパース検証を有効にするため）
- その他: SQLite は標準ライブラリで利用可

※ requirements.txt は本リポジトリ内にない場合、上記パッケージを pip で個別にインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数を作成
   - python -m kabusys.config_setup を実行して .env を対話的に生成
   - あるいは .env.example を参照して .env を手動作成
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告もエラー扱いになります
6. DB / データディレクトリの用意
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要なら .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

---

## 使い方

### 設定・検証

- .env の生成/更新:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
  - 返り値: 0=OK、1=エラー（--strict で警告も失敗扱い）

### 実行（主なスクリプト）

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用して本番 DB と分離します。
    - 起動時に停止フラグ（data/stop_requested.flag）が存在する場合は起動しません。
    - PID ファイル: data/execution.pid（Settings.pid_file_path）
- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を見る設計）
    - プロセス優先度を high に設定して起動します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from / --to: レポート期間（YYYY-MM-DD）
    - --db: SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH より優先されます）

### AI 機能

- ニュースセンチメント / レジーム判定は内部 API を呼ぶ形で利用します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。
- OpenAI API キー:
  - 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。

### 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

便利 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、run_monitoring 用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

自動 .env の読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env / .env.local を自動読み込みします。
- OS 環境変数 > .env.local > .env の優先順位で設定されます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

サンプル .env（最低限の項目）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 停止・Kill Switch の仕組み

- 停止フラグ（Execution 停止要求）:
  - data/kill.flag — KillSwitch が書き込むと ExecutionEngine が検知して停止します（監視側が生成）。
  - KillSwitch はリスク条件（ドローダウン超過 / ポジション上限超過など）を評価して書き込みます。
- 手動停止:
  - data/stop_requested.flag — run_execution / run_monitoring のループがこのファイルの存在を見て終了します。
- 起動時のクリア設定:
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に既存の kill.flag を自動で削除します（本番では 0 推奨）。

---

## ディレクトリ構成（主要）

（リポジトリの src/kabusys 以下を基準とした主要ファイル/モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注関連コンポーネント（Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - data/                    — 既定のデータ / DB ファイル（実行時に生成される／格納される）
  - logs/                    — ログ出力先（デフォルト）

（実際のツリーはリポジトリ内のファイルを参照してください）

---

## 補足 / 開発メモ

- Logging:
  - setup_logging() を各起動スクリプトで呼び出してログを統一します。ログは stdout と日次ローテーションされるファイル（logs/<app_name>.log）に出ます。LOG_DIR 環境変数で変更可能です。
- DB 初期化:
  - monitoring 用のスキーマは init_monitoring_db() によって冪等に作成／マイグレーションされます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは本番 DB と隔離された PAPER_TRADING_SQLITE_PATH を使用し、MockBrokerClient を利用して擬似発注（fill モードを PAPER_FILL_MODE で制御）します。
- AI 呼び出し:
  - OpenAI 呼び出しはリトライとバックオフを実装していますが、API キーの設定とネットワーク状況に依存します。失敗時はフェイルセーフ（0.0 のスコア等）で継続する実装です。
- テスト / CI:
  - 自動化テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env の影響を切ることができます。
  - AI 部分や外部 API 呼び出しは monkeypatch / patch によりモック化してテスト可能です。

---

この README はコードベースの要点をまとめたものです。各モジュールの詳細な仕様（引数や戻り値、内部アルゴリズムの設計意図など）はソースコードの docstring とコメントを参照してください。不明点があれば具体的な項目を指定していただければ追記します。