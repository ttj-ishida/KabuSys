# KabuSys

日本株向け自動売買システム（プロトタイプ）。  
このリポジトリは、システム監視・発注エンジン・ポートフォリオ構築・リサーチ・AI 補助機能などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python ベースの自動売買フレームワークです。

- データ管理（DuckDB / SQLite）
- シグナル生成・ポートフォリオ構築（純粋関数群）
- 発注処理（ExecutionEngine、実口座／ペーパートレード切替）
- 監視・アラート（MonitoringEngine、Kill Switch）
- 研究向けユーティリティ（ファクター計算、IC 計算など）
- LLM を用いたニュースセンチメント評価（OpenAI）

設計上の特徴:
- 環境変数 / .env で設定を管理
- 本番 DB とペーパートレード DB を分離
- ログは stdout および日次ローテーションファイルに記録
- 各種操作は CLI スクリプト（python -m kabusys.xxx）で実行

---

## 主な機能一覧

- 環境設定ウィザード: config_setup.py（対話式で .env を生成）
- 設定検証 CLI: validate_config.py（必須環境変数や config/*.yaml を事前チェック）
- ExecutionEngine（run_execution.py）:
  - 実口座 / ペーパートレード切替（KABUSYS_ENV）
  - MockBrokerClient を用いたペーパートレード（専用 sqlite DB）
  - プロセス優先度設定、PID 管理、停止フラグ対応
- MonitoringEngine（run_monitoring.py）:
  - System / Trade / Risk モニタリング
  - Kill Switch（条件に応じて data/kill.flag を書き込み）
  - ポーリング間隔は環境変数で調整可能
- ポートフォリオ構築モジュール:
  - 候補選定、重み付け（等金額 / スコア）、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究モジュール:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリ
- AI モジュール:
  - ニュースセンチメント評価（OpenAI を利用）: kabusys.ai.score_news
  - レジーム判定（ma200 + マクロセンチメント合成）: kabusys.ai.regime_detector
- ツール:
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 必要要件（概略）

- Python 3.9+
- 必要なパッケージ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（config/*.yaml 検証を行う場合）
- SQLite（組み込み）
- ネットワークアクセス（kabuステーション API / OpenAI 利用時）

※ requirements.txt がある場合はそれを参照して pip install -r を利用してください。無ければ最低限上記パッケージを導入してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール
3. 対話型ウィザードで .env を作成:
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants / kabu API のトークンや DB パス、KABUSYS_ENV などを設定します。
   - .env は絶対に Git にコミットしないでください。

4. 設定検証（必須環境変数やパスをチェック）:
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. DB ファイルや logs ディレクトリは自動作成されますが、必要に応じて権限を確認してください。

---

## 環境変数（主要）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）

- DB/ファイルパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 DB（data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（data/paper_trading.db）
  - PID_FILE_PATH: デフォルト data/execution.pid
  - KILL_FLAG_PATH: デフォルト data/kill.flag

- ログ
  - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト INFO）
  - LOG_DIR: ログファイル保存先（デフォルト logs/）

- ペーパートレード設定
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）

- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- その他
  - OPENAI_API_KEY: OpenAI を使う AI 機能で必要
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動で .env を読み込む処理を無効化

.env の作成は config_setup.py のウィザードを使うのが推奨です。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - プロセス優先度を "high" に設定します。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag が存在するとループは終了します。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB パスを直接指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリ関数の利用（例: AI スコアリング・レジーム判定）:
  - ニューススコアリング:
    ```
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## 停止・Kill Switch の仕組み

- ExecutionEngine の安全停止:
  - 管理側（監視等）が data/kill.flag に理由を書き込むと ExecutionEngine 側はそれを検出して停止する設計（KillSwitch）。
  - KillSwitch のパスは Settings.kill_flag_path でカスタマイズ可能。
  - run_execution/run_monitoring は data/stop_requested.flag の存在も確認しており、存在すれば終了動作を行います。

- 起動時の Kill Flag 自動クリア:
  - 環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番環境では 0 を推奨）。

---

## ロギング

- ログは stdout（StreamHandler）とファイル（TimedRotatingFileHandler、日次ローテーション、デフォルト 30 日保持）に出力されます。
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名ベース（例: execution.log, monitoring.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- LOG_DIR / LOG_LEVEL 環境変数で振る舞いを変更可能。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定読み込み
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                      — 発注エンジン関連（broker, order_manager 等）
  - monitoring/
    - monitoring_db.py
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
  - data/ (実行時に生成されることを想定)
    - *.db / *.flag / *.pid
  - tools/
    - paper_verification_report.py

（実際のファイルは src/kabusys 以下を参照してください）

---

## 開発上の注意 / トラブルシューティング

- 自動で .env を読み込む挙動:
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動読み込みします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- PyYAML が無い場合:
  - validate_config.py は YAML パースをスキップして警告を出します（インストール推奨）。

- OpenAI 関連:
  - ai モジュールを使うには OPENAI_API_KEY を設定するか、API キーを関数引数で渡してください。
  - API 呼び出しはリトライ・フェイルセーフ処理を含みますが、失敗時はデフォルト値で続行する設計です。

- 権限・プロセス優先度:
  - set_process_priority は OS 権限に依存します。権限エラーはログに出力され、処理は続行します。

- DuckDB / SQLite:
  - デフォルト DB パスは data/ 以下です。初回実行時にファイルが作成されますが、権限に注意してください。

---

## 参考コマンド一覧

- .env の作成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README を英語版にしたり、実行例（.env サンプル / systemd ユニットファイル / Dockerfile）を追加します。どの情報を優先して拡張したいか教えてください。