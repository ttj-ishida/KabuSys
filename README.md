# KabuSys

日本株自動売買システムのパッケージ (摘録)。この README は、同梱のコードベースに基づく概要、機能、セットアップ・起動手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実行時は .env に機密情報（トークン・パスワード等）を設定してください。`.env` は絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の主要機能を持つモジュール群を提供します。

- 戦略（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注実行エンジン（ExecutionEngine）およびブローカークライアント抽象化（paper_trading 対応）
- 監視・アラート（System/Trade/Risk の監視、Kill Switch）
- AI 補助（ニュースの NLP によるセンチメント評価、レジーム判定）
- 研究用ツール（レポート生成・検証ツール）

主に次のサブパッケージが含まれます（詳細は後述のディレクトリ構成参照）:
- kabusys.execution
- kabusys.monitoring
- kabusys.portfolio
- kabusys.research
- kabusys.ai
- kabusys.utils

---

## 主な機能一覧

- 設定管理
  - .env ファイル自動読み込み（プロジェクトルートを基準に検出）
  - 対話式設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（本番 DB と分離して data/paper_trading.db に記録）
  - ブローカー抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）
- 監視
  - System / Trade / Risk 各モニター、MonitoringEngine による定期チェック
  - Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine を安全に停止
  - monitoring DB（SQLite）へのログ永続化（monitoring_db）
- ポートフォリオ構築
  - 候補選定、スコア重み、等金額重み付け
  - セクター集中制限、レジーム乗数
  - 株数決定（lot 単位で丸め、リスクベース配分等）
- 研究・解析
  - DuckDB を利用したファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）等
- AI 統合
  - OpenAI を用いたニュースセンチメント（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

---

## セットアップ手順（開発/実行環境）

以下は一般的な手順例です。環境によって適宜読み替えてください。

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. pip を最新化して必要パッケージをインストール
   - pip install --upgrade pip
   - 必要パッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証で使用、任意)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数設定（.env）
   - リポジトリルートに `.env` を作成するか、対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - OPENAI_API_KEY: OpenAI を使う場合必須
     - LOG_LEVEL, LOG_DIR 等

5. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする strict モード:
     - python -m kabusys.validate_config --strict

---

## 使い方（起動・操作）

以下は主要コマンド例です。各コマンドはパッケージモジュールとして実行します。

1. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - 動作モード:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全に分離）
   - 起動時に data/stop_requested.flag が存在すると起動を中止します。
   - エンジンは実行中に data/stop_requested.flag を監視し、検出したら停止します。

2. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）をオーバーライド可能（デフォルト 60 秒）
   - 監視は monitoring 用 sqlite（Settings.sqlite_path）と duckdb（Settings.duckdb_path）に接続します。
   - 監視プロセスは data/stop_requested.flag を検出するとループを抜けて終了します。

3. 設定ウィザード
   - python -m kabusys.config_setup
   - .env を対話式に作成・更新します。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（デフォルト: data/paper_trading.db）

6. AI スコアリング / レジーム判定
   - ai モジュール関数はプログラム的に呼び出します（OpenAI API キーが必要）。
   - 例: ai.news_nlp.score_news(duckdb_conn, target_date, api_key=...)
   - OPENAI_API_KEY が設定されている場合は api_key を省略可能。

7. ログ
   - ログは stdout とファイル両方に出力されます（logs/<app_name>.log）
   - LOG_DIR 環境変数でログ保存先を変更可能
   - LOG_LEVEL 環境変数でレベル設定（例: DEBUG, INFO）

8. 停止・Kill Switch
   - Monitoring 側の KillSwitch は条件 (ドローダウン超過、ポジション上限等) に合致すると data/kill.flag を書き込み、ExecutionEngine に停止を促します。
   - 手動で ExecutionEngine を停止するにはプロセス管理（systemctl / supervisor 等）を使うか、監視を調整して kill.flag を作成します。
   - 実際の停止フラグファイル名:
     - 監視ループ終了用: data/stop_requested.flag
     - Execution 停止トリガー: data/kill.flag
   - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動的にクリアします（本番では推奨しません）。

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" または "1"）

Settings クラスにより多くの設定プロパティが提供されます。詳細は `src/kabusys/config.py` を参照してください。

---

## 実行上の注意点

- Paper Trading と Live（本番）は DB を分離する設計です。paper_trading モードでは paper_trading 用 SQLite に記録されます。
- OpenAI を使用する機能は API キーが必須です。API 呼び出しはリトライやフォールバック（失敗時は安全値）を組み込んでいますが、適切なキー管理と料金管理を行ってください。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみとなります。
- プロセス優先度設定は psutil を用いて行いますが、権限不足で失敗する場合は警告が出ます（動作には影響しません）。
- DuckDB や SQLite のスキーマは初回接続時に自動で初期化・マイグレーションされます（monitoring_db.init_monitoring_db）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル/ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（Settings）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - execution/                 — 発注実装関連（Engine, OrderManager, BrokerFactory など）
  - monitoring/
    - monitoring_db.py         — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール

プロジェクトルートには以下のような補助ディレクトリ・ファイルが想定されます:
- data/        — SQLite やフラグファイル（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
- logs/        — ログファイル出力先（デフォルト）
- config/      — 各種 YAML 設定テンプレート（system_config.yaml など）
- .env / .env.local / .env.example

---

## トラブルシューティング・よくある質問

- Q: 実行時に DB/ログディレクトリの作成でエラーが出る
  - A: 実行ユーザにファイル作成権限があるか確認してください。ログディレクトリは環境変数 LOG_DIR で変更できます。

- Q: OpenAI API 呼び出しで失敗する
  - A: OPENAI_API_KEY が正しく設定されているか、ネットワーク経路・プロキシ設定を確認してください。AI 関連関数は失敗時に安全側の挙動（スコア 0.0 等）で継続しますが、ログを確認してください。

- Q: Paper Trading のデータはどこに保存される？
  - A: KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）に保存され、production の monitoring DB とは完全に分離されます。

---

## 参考・補足

- 各モジュールの詳細な設計方針や数式、配置アルゴリズム等はソース中の docstring やコメントに記載されています。実運用・検証前に必ずコードと設定を精査してください。
- 本 README はコードベースの要点をまとめたものであり、実行環境固有のデプロイ手順（systemd ユニット作成、コンテナ化、CI/CD）などは含みません。必要に応じて追加してください。

---

もし README に追記してほしい内容（例: systemd 用ユニット例、コンテナ化手順、より詳しい環境変数一覧）があれば教えてください。