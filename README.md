# KabuSys

バージョン: 0.1.0

日本株自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリはトレーディングエンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ニュース解析などのモジュールを含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコア実装です。  
主な設計方針は以下です。

- モジュール化されたコンポーネント（execution / monitoring / portfolio / research / ai）  
- 環境変数（.env / .env.local）による構成管理（自動ロード機能あり）  
- 本番 / ペーパートレードを容易に切り替え可能（KABUSYS_ENV）  
- DuckDB を用いたリサーチ向けデータ、SQLite を監視・発注ログ用に使用  
- OpenAI を用いたニュース NLP / レジーム判定モジュール（オプション）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（実行エンジン）: ブローカーとのやり取り、注文管理、リスクチェック、再整合処理
  - BrokerClientFactory: 本番/ペーパーのクライアント切り替え
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視、監視ログ保存
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常、ドローダウン・ポジション上限監視
  - KillSwitch / MonitoringEngine / AlertManager（アラート連携）
- Portfolio
  - 銘柄選定、等/スコア加重、セクター上限適用、位置サイズ計算（lot 単位）
- Research
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリ
- AI（任意）
  - news_nlp: ニュースを LLM（OpenAI）でセンチメント化して ai_scores に保存
  - regime_detector: MA 乖離 + マクロニュースでレジーム（bull/neutral/bear）判定
- ツール
  - 設定ウィザード（config_setup）、設定検証 CLI（validate_config）、
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

## 依存関係（主なもの）

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証のため任意）
- その他標準ライブラリ

（実行環境に合わせて requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係インストール（例）
   ```
   pip install duckdb psutil openai
   # 開発向けに requirements.txt がある場合はそれを使う
   # pip install -r requirements.txt
   ```

4. 環境変数ファイル作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を手動作成（例は下記）。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの・デフォルト）

以下を `.env` に設定するのが基本です（.env.example を参考にしてください）。

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要な切替／パス
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 専用 DB）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- AI 関連
  - OPENAI_API_KEY: OpenAI を利用する場合に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）

- 監視関連
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

.env の自動読み込み:
- .env と .env.local はプロジェクトルートにあれば自動で読み込まれます。
- OS 環境変数は .env より優先され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます。

簡単な .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=
```

---

## 使い方（主要なコマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  動作概要:
  - 起動時にプロセス優先度を high に設定
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用（本番 DB と分離）
  - data/stop_requested.flag が存在すると起動を中止する
  - 実行中に stop フラグを検出すると安全に停止する
  - PID ファイル: data/execution.pid（設定でパス変更可）

- Monitoring を起動（システム監視）
  ```
  python -m kabusys.run_monitoring
  ```
  動作概要:
  - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60）
  - 監視ログは sqlite_path（デフォルト data/monitoring.db）へ書き込む（環境にかかわらず本番 sqlite_path を使用）
  - 監視開始でプロセス優先度を high に設定

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI ニューススコアリング / レジーム判定（プログラム API）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続を受け取り実行するため、スクリプトから直接呼び出すか独自のジョブを作って使用します。
  - OPENAI_API_KEY が必要（引数で上書き可能）

---

## 停止 / Kill Switch

- 手動でエンジンを停止したい場合:
  - `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが検知して停止します（run_execution は起動前にこのフラグがあると起動しません）。
  - `KillSwitch`（監視コンポーネント）が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
- Kill flag の自動クリアは環境変数 KILL_FLAG_CLEAR_ON_START=1 で制御（本番では 0 推奨）。

---

## ログ

- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log、日次ローテーション、30日分保存）に出力されます。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御できます。
- ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/ を使用します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__=0.1.0）
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロード機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - execution/ — 実行エンジン本体（broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
  - portfolio/ — 銘柄選定・配分・リスク調整・サイズ計算（pure functions）
  - research/ — ファクター計算、特徴量探索
  - ai/
    - news_nlp.py — ニュース NLP スコアリング
    - regime_detector.py — 市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - data/ — 実行時に作成されるデータ/フラグ/DB を置く想定（パスは環境変数で変更可）

（実際のファイル構成はリポジトリを参照してください）

---

## 注意点 / 運用上のヒント

- KABUSYS_ENV によって挙動（本番 DB とペーパートレード DB の使い分けなど）が変わります。運用時は必ず validate_config を実行して設定をチェックしてください。
- .env は決してリポジトリにコミットしないでください（config_setup も README に警告あり）。
- AI 機能は API キーが必要であり、API 呼び出しの失敗時はフェイルセーフ（スコアをデフォルト値に）になる設計です。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（警告が出ます）。
- run_execution/run_monitoring は Ctrl-C（KeyboardInterrupt）で優雅に停止します。外部からの停止には stop_requested.flag を利用します。

---

この README はコードベース（src/kabusys）から抽出した要点をまとめたものです。詳細な設計やアルゴリズムの仕様は各モジュール内の docstring や Project のドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を参照してください。