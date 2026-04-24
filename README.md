# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリの README（日本語）。

以下はコードベース（src/kabusys/*.py）からの抜粋を基にした説明です。各スクリプトはパッケージとして実行可能（例: `python -m kabusys.run_monitoring`）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアロジックを提供するモジュール群です。主な機能は次のとおりです。

- 発注実行エンジン（ExecutionEngine）と Broker クライアントの抽象化
- 監視用エンジン（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP（OpenAI を用いたセンチメント評価）およびレジーム判定
- Paper Trading 用の分離された DB と検証レポート生成ツール
- 設定ウィザード（.env 生成）・設定検証 CLI
- ロギング・プロセス優先度ユーティリティ等の補助モジュール

設計上のポイント:
- 本番 / ペーパートレードを環境変数（KABUSYS_ENV）で切り替え可能
- Paper Trading は本番 DB と分離（専用 SQLite）
- 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用（監視は本番対象を監視する意図）

---

## 機能一覧（抜粋）

- run_execution.py: 発注エンジン起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションあり）
- tools/paper_verification_report.py: Paper Trading の検証レポート生成
- portfolio: 候補選定・重み付け・ポジションサイズ計算・リスク調整
- research: DuckDB を用いたファクター計算・将来リターン・IC 等の解析機能
- ai: ニュース NLP スコアリング（OpenAI）およびレジーム判定
- monitoring: 監視 DB（SQLite）・監視エンジン・Kill Switch・アラート連携

---

## 必要要件（想定）

- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - sqlite3（標準ライブラリ）
- 開発環境に合わせて requirements.txt を用意している場合はそれを使用してください。
  例（必須の一部）:
  ```
  pip install duckdb psutil openai
  ```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt    # もし用意されていれば
   # または最低限:
   pip install duckdb psutil openai
   ```

4. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   生成後は `.env` を作業ディレクトリ（プロジェクトルート）に置いてください。
   .env は機密情報を含むため絶対に Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数（代表）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要設定:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBrokerClient を利用し DB は `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）
  - live: 本番。設定ミスに注意（validate_config は警告を出します）
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP / レジーム判定）で使用
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

その他:
- PID / Kill フラグ関連:
  - PID ファイル: data/execution.pid（ExecutionEngine が使用）
  - Kill フラグ: data/kill.flag（KillSwitch が書き込む）
  - Stop リクエストフラグ: data/stop_requested.flag（スクリプト停止用のファイル）

---

## 使い方（実行例）

基本的にはプロジェクトルートで実行します。Python パッケージとして実行可能です。

- 監視ループを起動（SystemMonitor）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は監視用 DB 初期化を行い、停止は data/stop_requested.flag を作るか Ctrl+C。

- 発注エンジンを起動（ExecutionEngine）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB に記録されます。
  - 起動時に data/stop_requested.flag が既にある場合は起動しません。
  - 実行中は data/execution.pid を利用し、停止は stop flag を作成するかプロセスにシグナル。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH で上書き可）
  - または `--db path/to/db.sqlite` を指定

- ライブラリ関数（プログラムから利用）:
  - ポートフォリオ構築:
    ```
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
    ```
  - リサーチ:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```
  - ニュース NLP（プログラム呼び出し）:
    ```
    from kabusys.ai.news_nlp import score_news
    # score_news(conn, target_date, api_key=None)
    ```
  - 市場レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    # score_regime(duckdb_conn, target_date, api_key=None)
    ```

---

## ロギング

- ログ設定は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で行われます。
- デフォルトのログ出力先は `logs/<app_name>.log`（日次ローテーション、30日保持）と標準出力（stdout）です。
- `LOG_DIR` 環境変数でログディレクトリを変更できます。
- 各起動スクリプトは `setup_logging(app_name="execution")` 等を呼び出しています。

---

## 停止 / Kill Switch

- 実行停止制御:
  - 監視ループや ExecutionEngine は `data/stop_requested.flag` の存在を監視して終了動作を行います（外部からこのファイルを作成して安全に停止させる）。
- 自動停止（Kill Switch）:
  - `KillSwitch` はリスク条件（ドローダウン閾値やポジション上限等）を満たした場合 `data/kill.flag` を書き込み、ExecutionEngine 側で検出して安全停止させる設計です。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動で消去しますが、本番環境では危険なので推奨されません。

---

## ディレクトリ構成（主なファイル）

以下は src 配下の主要ファイル / パッケージ構成の要約です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
  - execution/  (実行エンジン関連; BrokerFactory, ExecutionEngine, OrderManager 等)
  - data/       (実行時に生成される想定: data/*.db, data/*.pid, data/*.flag)
  - logs/       (ログファイル出力先)

（注）上の一覧はコードベースの主要ファイルを抜粋したもので、さらに詳細なモジュールが含まれます。

---

## 開発上の注意点

- .env には機密情報（API トークン等）が含まれます。絶対にレポジトリへコミットしないでください。
- validate_config は本番環境（KABUSYS_ENV=live）設定時に追加の警告を出します。実運用前に必ず検証してください。
- monitoring は監視対象として「本番 sqlite_path」を参照する点に注意。監視設定を誤ると監視対象が想定外になる可能性があります。
- Paper Trading を使用する場合、本番 DB と完全分離された SQLite を使用することで安全性を確保しています（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を利用する機能は API キー管理と API 利用コストに注意してください。API 失敗時はフェイルセーフ（スコア 0.0 等）で継続する実装です。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視起動
  ```
  python -m kabusys.run_monitoring
  ```

- 発注エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README を README.md として生成するための正確な Markdown 形式や、各コマンドの実行前提（カレントディレクトリ、仮想環境設定、requirements.txt の中身例）などを追加で作成します。どの項目をより詳しく説明しますか？