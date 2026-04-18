# KabuSys

軽量な日本株自動売買フレームワークのサンプル実装です。  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、AI ベースのニュースセンチメント評価などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は次のような機能を想定したモジュール群で構成されています。

- 発注/実行エンジン（ExecutionEngine）とブローカー抽象化（本番 / ペーパートレード切替）
- システム監視（CPU / メモリ / ディスク / プロセス生存チェック）
- リスク監視（ドローダウン、保有銘柄上限など）
- Kill Switch（条件により Execution を安全停止）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限等）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 運用ツール（ペーパートレード検証レポート、設定ウィザード、設定検証）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて MockBroker を使用）
- run_monitoring.py: SystemMonitor を定期実行して状態を監視
- config_setup.py: 対話式で `.env` を作成 / 更新
- validate_config.py: 環境変数および config/*.yaml の簡易チェック
- portfolio: 候補選定・重み付け・ポジションサイズ計算・リスク調整
- research: DuckDB を使ったファクター計算・統計解析ユーティリティ
- ai: OpenAI を使ったニュースセンチメント（score_news）やレジーム判定（score_regime）
- monitoring: SQLite ベースの監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）と各種モニター・エンジン
- tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate     # Linux / macOS
   .venv\Scripts\activate        # Windows
   ```

3. 必要なパッケージをインストール（プロジェクトに requirements.txt がないため、下記は最低限の例）
   ```
   pip install duckdb psutil openai pyyaml
   ```
   - openai: AI モジュールを使う場合
   - pyyaml: validate_config.py が config/*.yaml を検証するために任意で利用
   - duckdb: 研究・AI モジュールで使用
   - psutil: システム監視、プロセス優先度設定

4. 環境変数設定
   - 推奨は `python -m kabusys.config_setup` を実行して `.env` を作成すること
   - 手動で `.env` を作る場合は次の必須変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - そのほか重要な変数は下記「環境変数」を参照

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 運用 / オプション
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
    - paper_trading の場合、Execution は MockBroker を使い DB は data/paper_trading.db を使用
  - OPENAI_API_KEY: AI モジュール利用時に必要
  - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト: INFO
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）デフォルト: instant
  - PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）

注意:
- Settings モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- `.env` は決してバージョン管理にコミットしないでください。

例（.env の断片）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 実行方法（代表的なコマンド）

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、データは paper_trading 用 DB に分離して保存します。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60 秒）。
  - 監視はデフォルトで Settings.sqlite_path（本番用 path）を使用します（KABUSYS_ENV に依存しません）。
  - 停止は data/stop_requested.flag を作成することで検知します。

- 設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから利用）
  - ニュース NLP スコアリング:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が必要（api_key を引数で渡すことも可能）

---

## 運用上の注意 / フラグ類

- stop_requested.flag
  - run_monitoring と run_execution はプロジェクトルート下の data/stop_requested.flag を監視します。存在するとループを終了したり起動を抑止します。
- kill.flag
  - KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込んで ExecutionEngine を停止させます。KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアできますが、本番では 0 を推奨します。
- ログ
  - ログは logs/<app_name>.log に日次ローテーションで出力されます。ディレクトリ作成に失敗した場合はコンソールのみ出力されます。
- DB
  - デフォルト DuckDB: data/kabusys.duckdb
  - デフォルト 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

---

## 使い方の例（起動ワークフロー）

1. .env を作成
   ```
   python -m kabusys.config_setup
   ```

2. 設定を検証
   ```
   python -m kabusys.validate_config
   ```

3. Execution を起動（別ターミナルで）
   ```
   python -m kabusys.run_execution
   ```

4. 監視を起動（別ターミナルで）
   ```
   python -m kabusys.run_monitoring
   ```

5. 必要に応じて Kill Switch をトリガー（運用上の判断で kill.flag を書き込む／自動で書き込まれる）

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite の CRUD ヘルパ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度チェック
    - trade_monitor.py — （trade 関連監視）※詳細はコード参照
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （アラート送信の抽象化）※実装参照
  - execution/ — Execution エンジン関連（ブローカー、order 管理、リスク管理等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — マクロセンチメント + MA200 によるレジーム判定

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下の各ファイルを参照してください）

---

## 開発メモ

- DuckDB は分析用途で利用します。prices_daily / raw_financials / raw_news 等のテーブルを格納して使います。
- MonitoringDB（SQLite）は軽量な運用ログ保存用です。init_monitoring_db() は既存 DB のマイグレーション（列追加）にも対応しています。
- OpenAI を利用する機能は API 呼び出しの失敗に対してリトライやフォールバック（スコア 0.0 等）を実装しており、失敗してもシステム全体が止まらない設計になっています。
- 本 README はコードベースの主要ポイントを説明しています。詳細実装や拡張方法は各モジュールの docstring / コメントを参照してください。

---

もし README のサンプル .env、起動スクリプトの systemd サービス例、または各コンポーネントの詳しいドキュメントを追加で作成したければ教えてください。必要に応じて追補します。