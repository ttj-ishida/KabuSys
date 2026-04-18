# KabuSys — 日本株自動売買システム

この README はリポジトリ内の主要モジュールに基づき作成した概要ドキュメントです。開発者および運用担当者向けに、プロジェクト全体の目的、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。価格データや財務データを用いたリサーチ／ファクター計算、ポートフォリオ構築（銘柄選定・配分・株数決定）、注文管理（ExecutionEngine）、およびシステム監視・リスク監視・Kill Switch（自動停止）を備えています。さらに、OpenAI を用いたニュース NLP によるセンチメント評価や市場レジーム判定といった拡張機能も含まれます。

主な設計方針：
- DB は分析用に DuckDB、監視／発注履歴等に SQLite を使用（Paper Trading は実運用と分離）。
- 環境変数 / .env による設定管理。
- モジュールは可能な限り純粋関数・副作用最小化で実装。
- 実運用時のログ・プロセス優先度設定・フェイルセーフ設計を重視。

---

## 機能一覧

- 環境設定ウィザード（.env 生成・更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（発注エンジン）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
- Monitoring（システム監視）起動スクリプト: python -m kabusys.run_monitoring
  - 環境にかかわらず本番 sqlite を監視ログに使用
  - MONITOR_POLL_INTERVAL でポーリング周期を上書き可能
- 監視エンジン：SystemMonitor / TradeMonitor / RiskMonitor を統合して定期チェック・アラート発行
- Kill Switch：重大なリスク条件を満たした場合に data/kill.flag を書き込み ExecutionEngine を停止
- Portfolio 構築ユーティリティ：
  - 候補選定（select_candidates）
  - 重み算出（等配分 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限・レジーム乗数
- リサーチモジュール（DuckDB を利用）：
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）などの解析ユーティリティ
- AI 関連：
  - ニュース NLP による銘柄別センチメント（OpenAI）
  - マクロニュース + ETF MA による市場レジーム検出（OpenAI）
  - API のリトライやレスポンスバリデーションを備える
- ツール：
  - paper_trading の検証レポート生成スクリプト（paper_verification_report）

---

## 前提条件（推奨）

- Python 3.9+
- 必要パッケージ（一部）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の内容検証を行う場合）
- SQLite（標準ライブラリに含まれます）
- ネットワーク接続（OpenAI を使用する機能を使う場合）
- （任意）kabuステーション等のブローカー API（実運用時）

requirements.txt がない場合は上記パッケージをインストールしてください。例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 必要パッケージをインストール（上記参照）
3. .env の作成（推奨: 対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークン、kabu API パスワード、DB パスなどを設定します。
4. 設定検証（実行前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

備考:
- .env は絶対に Git にコミットしないでください（ウィザードもその旨の注記あり）。
- プロジェクトルートの自動検出により .env/.env.local を自動読み込みします（テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時デフォルト）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での自動 kill flag クリア（0/1、本番は 0 推奨）

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（通常: サービスとして起動）
  ```
  python -m kabusys.run_execution
  ```
  動作:
  - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して実運用 DB と分離します。
  - data/stop_requested.flag があると起動せず終了します。
  - 停止操作は data/stop_requested.flag を作成することでリクエストできます。
  - kill.flag（Settings.kill_flag_path）により ExecutionEngine を止める Kill Switch 機構があります。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作:
  - MONITOR_POLL_INTERVAL（秒）で poll（デフォルト 60 秒）
  - SystemMonitor がデータ鮮度、CPU/メモリ/Disk、Execution の PID の存在などをチェックし monitoring DB に記録します。
  - 停止は data/stop_requested.flag による検出や Ctrl-C。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系関数（ライブラリ利用）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB 接続と OpenAI API キーを引数に受け取り、DB へ書き込みを行います。

---

## 運用上の注意点

- ログ:
  - 共通の logging 設定ユーティリティがあり、Stream（stdout）と日次ローテートファイルを設定します（logs/<app_name>.log）。
- プロセス優先度:
  - 実行スクリプトは起動時に set_process_priority("high") を試行します。権限不足時は警告が出ますが続行します。
- Kill Switch:
  - RiskMonitor が重大なリスク（ドローダウン超過やポジション上限超過）を検出すると KillSwitch が data/kill.flag を書き込み ExecutionEngine を停止させます。KILL_FLAG_CLEAR_ON_START に注意してください（本番では 0 推奨）。
- Paper Trading:
  - paper_trading 環境では発注処理がモックになり、監視 DB とは別の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。検証やレポート生成はこの DB を参照します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は起動時に必要テーブルと一部カラムのマイグレーション（ない場合は追加）を行います（冪等）。

---

## 主要モジュール説明（抜粋）

- kabusys.config: .env 読み込み、Settings クラス（環境変数ラッパ）
- kabusys.config_setup: .env を対話式に作るウィザード
- kabusys.validate_config: 起動前チェック CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト
- kabusys.run_monitoring: SystemMonitor ポーリング起動スクリプト
- kabusys.utils.logging_setup: ログ設定ユーティリティ
- kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定
- kabusys.monitoring.*: 監視周り（monitoring_db, system_monitor, risk_monitor, kill_switch, monitoring_engine, alert_manager 等）
- kabusys.portfolio.*: ポートフォリオ作成ロジック（選定・重み付け・サイズ計算・リスク調整）
- kabusys.research.*: DuckDB を使ったファクター計算・解析
- kabusys.ai.*: OpenAI を使ったニュース NLP / レジーム判定
- kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成

---

## ディレクトリ構成（概略）

以下はリポジトリ内の主要ファイル・モジュール構成の概略です（抜粋）。実際のツリーはリポジトリにより差があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - trade_monitor.py (参照あり)
      - alert_manager.py (参照あり)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - execution/            (Execution 関連の実装、OrderManager 等)
      - broker_factory.py (参照)
      - execution_engine.py (参照)
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - data/                 (runtime: logs, sqlite/duckdb ファイル、flag ファイル等)

運用でよく使うファイル:
- data/stop_requested.flag — 手動停止要求（run_*.py が検出して終了）
- data/kill.flag — Kill Switch による自動停止フラグ
- data/execution.pid — 実行エンジンの PID ファイル

---

## 開発・拡張ヒント

- DuckDB 接続を使う分析機能（kabusys.research / ai.*）は副作用を最小化しており、テストしやすく設計されています。
- OpenAI 呼び出しは再試行や JSON バリデーションを組み込んでおり、外部 API の不安定性を考慮しています。テスト時は内部の API 呼び出し関数をモックすることを推奨します（コード内に patch するコメントあり）。
- logging_setup.setup_logging を全起動スクリプトで呼び出すことでログ設定が統一されます。ログディレクトリは環境変数 LOG_DIR で上書き可能。
- monitoring_db.init_monitoring_db は冪等なので、安全に複数回実行できます。既存 DB に対する簡易マイグレーションも含まれます。

---

もし README に追加したい具体的な情報（例: requirements.txt の内容、CI/CD の設定、systemd サービス定義サンプル、より詳細な API ドキュメントなど）があれば教えてください。必要に応じて追記します。