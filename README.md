# KabuSys — 日本株自動売買システム

このリポジトリは日本株向け自動売買システム「KabuSys」のコアライブラリと起動スクリプト群を含みます。  
本READMEはコードベース（src/kabusys/...）の使い方、セットアップ、主要機能、ディレクトリ構成を日本語でまとめたものです。

---

## 概要

KabuSys は以下の主要コンポーネントで構成されます。

- ExecutionEngine：発注ロジック、オーダー管理、リスク管理、ブローカークライアント連携
- Monitoring：システム状態・注文状態・リスク監視、Kill Switch（停止シグナル）
- Research：DuckDB を用いたファクター計算・特徴量解析
- Portfolio：候補選定・重み付け・ポジションサイズ計算・セクター制限
- AI モジュール：ニュースの NLP スコアリング / レジーム判定（OpenAI API を利用）
- ユーティリティ：設定管理、ログ設定、プロセス優先度設定、設定ウィザード / 検証スクリプト 等

設計方針のポイント：
- DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- Paper Trading と Live を分離（paper_trading 用 DB が別）
- LLM を使う AI 部分は API キー依存。故障時はフェイルセーフで継続する設計

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - モニタリングは環境に関わらず監視用 SQLite（デフォルト data/monitoring.db）を使用
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- AI 関連:
  - ニュース NLP による銘柄別スコアリング（OpenAI 必須）
  - 市場レジーム判定（ma200 突合＋マクロニュース LLM 混成）
- Portfolio コンポーネント（候補選定、重み付け、ポジションサイズ）
- MonitoringDB：SQLite による監視ログ／ダッシュボード永続化 API

---

## 前提 / 必要環境

- Python 3.10 以上（型アノテーションの union 型 `X | Y` を利用しているため）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai （AI 機能を使用する場合）
  - PyYAML（config/*.yaml の検証を行う場合、無くても動くが警告となる）
- SQLite は標準ライブラリで利用可能

（パッケージはプロジェクト固有の requirements.txt があればそちらを優先してください）

インストール例（最低限）:
```bash
python -m pip install "duckdb" "psutil" "openai" "PyYAML"
```

---

## セットアップ手順

1. リポジトリをクローン / 展開してプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージのインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
4. .env の作成
   - 対話式ウィザードで作成するのが簡単です:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードが作成する主なキー:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL / KILL_FLAG_CLEAR_ON_START
     - OPENAI_API_KEY は AI 機能用（ウィザードでは扱わないため必要なら .env に追加）
5. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. ディレクトリ（data, logs 等）の作成は多くのユーティリティが自動で行いますが、手動で準備しておいても良いです。

---

## 使い方（起動 & 操作）

### 監視ループの起動
- 目的：システム状態・注文/リスク監視、Kill Switch 判断、アラート発行等
- コマンド:
  ```bash
  python -m kabusys.run_monitoring
  ```
- 設定:
  - MONITOR_POLL_INTERVAL（秒、例: 30）でポーリング間隔を変更可能
  - ログは logs/monitoring.log（デフォルト）に日次ローテーションで出力

- 停止:
  - プロセス内で stop フラグ（data/stop_requested.flag）を検出すると終了します
  - 手動停止は Ctrl+C（KeyboardInterrupt）で安全に終了します

### 実行エンジンの起動（ExecutionEngine）
- 目的：発注セッションを実行（実際のブローカー接続またはペーパートレード）
- コマンド:
  ```bash
  python -m kabusys.run_execution
  ```
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - PID ファイル: data/execution.pid（設定で変更可）
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 停止は data/stop_requested.flag を作成（監視/外部からの停止制御）または Kill Switch（monitoring が data/kill.flag を書き込む）で行います

### Paper Trading 検証レポート生成
- コマンド:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- オプション:
  - --db で SQLite のパスを明示可能（優先順位: --db > 環境変数 > default）

### AI 機能（ニュース NLP / レジーム判定）
- OpenAI の API キー（OPENAI_API_KEY）が必要です
- main 関数ではなくライブラリ関数として利用可能:
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
- 注意:
  - API 呼び出しはコストやレート制限の影響を受けます。テスト環境ではキーを不要にする等の工夫を検討してください
  - 失敗時はフェイルセーフ（スコアを 0 にフォールバック等）する設計です

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（例: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

※ 設定は .env ファイルに保存できます（config_setup で生成推奨）。自動ロード順は OS 環境 > .env.local > .env（プロジェクトルート検出が成功した場合）。

---

## ログ・永続ファイルとフラグ

- ログ:
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション、30日保持
- データ:
  - DuckDB: data/kabusys.duckdb（分析用）
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- PID / Flags:
  - data/execution.pid: ExecutionEngine が使用する PID ファイル（run_execution へ渡される）
  - data/stop_requested.flag: 起動スクリプト（run_execution/run_monitoring）で監視される停止フラグ
  - data/kill.flag: Monitoring が書き込み、ExecutionEngine に停止を促す Kill Switch 用フラグ

---

## 開発者向けメモ / ヒント

- 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- 設定検証スクリプト（validate_config）は不備を事前検出するため CI に組み込みやすい
- DuckDB を使った解析・研究モジュールは副作用が少ない設計（外部 API を呼ばない）
- AI モジュールはテスト容易性のため内部の API 呼び出し関数を patch しやすい作り
- process_priority ユーティリティは Windows / POSIX の差分を吸収（psutil 使用）

---

## ディレクトリ構成（要約）

プロジェクトルートの src/kabusys 以下に主要モジュールが配置されています（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — 監視ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルを抜粋。実際のリポジトリでは追加の補助モジュールやサブモジュールがあります）

---

## よくある質問 / 注意点

- Python バージョンは 3.10 以上を推奨します（型注釈や構文要件のため）。
- AI 機能を有効にする場合は OPENAI_API_KEY を忘れずに設定してください。API 呼び出しはコスト・レート制限に注意。
- run_monitoring は監視専用 DB（settings.sqlite_path）を使用します。環境にかかわらず監視用 DB を参照する設計です。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB を使い分けます（実アカウントと隔離）。
- kill.flag / stop_requested.flag の誤った運用はプロセス起動・停止に影響するため運用手順を明確にしてください。

---

README の内容や使用方法で不明な点があれば、どの箇所を詳しく知りたいか教えてください。起動コマンド例や .env のサンプルテンプレートも用意できます。