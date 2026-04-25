# KabuSys

日本株向け自動売買システムのコアライブラリ / 起動スクリプト群です。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI ユーティリティなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine：発注・注文管理・リスク管理を担う実行エンジン（本番・ペーパートレード対応）
- Monitoring：プロセス／システム状態・注文状態・リスク監視、Kill Switch による自動停止
- Portfolio：銘柄選定・重み算出・ポジションサイジング・リスク調整の純粋関数
- Research：DuckDB ベースのファクター計算・特徴量解析ユーティリティ
- AI：ニュースセンチメント解析や市場レジーム判定（OpenAI 利用）
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- 設定ユーティリティ：.env 作成ウィザード、設定検証 CLI

設計方針として、DB（SQLite / DuckDB）をデータ永続化に利用し、外部 API 呼び出し（OpenAI / J-Quants / kabuステーション）は設定に応じて利用します。ペーパートレードは本番 DB と分離して専用 DB に記録されます。

---

## 主な機能一覧

- プロセス優先度の設定（高優先度で起動）
- ExecutionEngine の起動/停止（停止はフラグファイルで制御）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor のポーリング）
- Kill Switch：ドローダウンやポジション上限超過で停止フラグを書き込む
- AI ベースのニュースセンチメント（OpenAI）とレジーム検出
- Portfolio モジュール：候補選定、等金額/スコア加重、リスクベースの株数算出
- Research：モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算
- 設定ウィザード（.env 作成）と設定検証 CLI
- ペーパートレード検証レポート生成スクリプト

---

## 依存関係（主要）

ソース内から推定される主な依存パッケージ:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- （sqlite3 は標準ライブラリ）

インストール例（仮）:
```bash
pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt / setup.py がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存をインストール
3. 初期 .env を作成
   - 対話型ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成（.env.example を参照）
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じてデータディレクトリを作成（ログ・DB・flag 保存用）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/

注意:
- 自動で .env を読み込む仕組みがあり（.env, .env.local）、自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (監視用)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログ出力レベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- PAPER_FILL_MODE: Paper トレード時の約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 実行方法（スクリプト）

以下はプロジェクト内の起動スクリプトの使い方例です。いずれもプロジェクトルートで実行します。

- ExecutionEngine（発注エンジン）起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV に依存
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が利用され、記録は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に行われます
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します
    - PID ファイル: data/execution.pid（デフォルト）

- Monitoring（監視ループ）起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - オプション / 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 停止:
    - プロジェクトルートの data/stop_requested.flag を作成するとループは終了します
    - kill.flag（デフォルト data/kill.flag）は ExecutionEngine に停止シグナルを送るために監視側が書き込みます

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

---

## ログ / フラグ / PID の取り扱い

- ログ: `kabusys.utils.logging_setup.setup_logging` によって stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- 停止フラグ:
  - data/stop_requested.flag: 起動ループ（monitoring / execution）が検出すると安全に終了します（手動停止用）。
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止を促します（監視が書き込む）。
- PID: ExecutionEngine は data/execution.pid（デフォルト）に PID を書く想定です。

---

## ライブラリ的な使い方（例）

- ポートフォリオ構築関数:
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - 例:
    ```python
    from kabusys.portfolio import select_candidates, calc_equal_weights
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_equal_weights(candidates)
    ```
- Research（DuckDB 接続を渡してファクター計算）:
  ```python
  import duckdb
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026,4,1))
  ```
- AI（ニューススコアリング）:
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - DuckDB 接続を渡して `kabusys.ai.news_nlp.score_news(conn, target_date)` を呼び出す

---

## 注意点 / 運用ガイド

- 本番環境（KABUSYS_ENV=live）の場合は特に `.env` の設定や LINE 通知設定を確認してください。validate_config は本番向けの追加チェックを行います。
- Paper Trading は本番 DB と分離されます（`PAPER_TRADING_SQLITE_PATH` を利用）。
- OpenAI や外部 API 呼び出しは失敗時にフェイルセーフ（スコア 0.0、あるいはスキップ）で継続する設計になっていますが、API キーの管理・レート制限対策は運用上の重要課題です。
- ログディレクトリ作成に失敗した場合はコンソールにフォールバックします。ログのローテーション設定は 30 日分保持です。

---

## ディレクトリ構成（概要）

プロジェクトルートに `src/` 配下のパッケージが想定されています。主なファイル/ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理 (.env 自動ロード)
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / affinity 設定
  - execution/                 — 実際のエンジン / ブローカーファクトリ 等（要参照）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        (実装による)
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

注意: 上記は主要ファイルの抜粋です。詳細は各モジュールファイルを参照してください。

---

## よく使うコマンドまとめ

- 環境ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に含めたい追加情報（例: 実際の依存関係のリスト、systemd ユニットの例、デプロイ手順、テストの実行方法など）があれば教えてください。必要に応じて追記します。