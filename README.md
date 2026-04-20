# KabuSys

日本株自動売買システムのリポジトリ向け README（日本語）

この README はリポジトリ内の主要スクリプト／モジュールから自動的に把握できる情報をまとめたものです。開発者・運用者向けに、概要・機能・セットアップ・使い方・ディレクトリ構成を記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する一連のコンポーネント群を提供するプロジェクトです。主な役割は以下です：

- データ取得・DuckDB を使った因子計算（research）
- ポートフォリオ構築ロジック（portfolio）
- 発注エンジン（execution） — 実口座 / ペーパートレードに対応
- 監視・アラート（monitoring）
- ニュース NLP を用いた AI スコアリング（ai）
- 運用支援ツール（tools）や設定ウィザード

設計思想として、プロダクション用コードとペーパートレードを明確に分離し、設定ファイル（.env / config/*.yaml）や環境変数で挙動を切り替えられるようになっています。

---

## 主な機能一覧

- ExecutionEngine（発注エンジン）
  - 実口座（kabuステーション）／Mock（paper_trading）での発注を抽象化
  - リスク管理（RiskManager）やオーダー管理（OrderManager）を内蔵

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態、データ鮮度の監視
  - TradeMonitor: 注文ログや滞留注文、約定異常の検知
  - RiskMonitor: ドローダウン・ポジション上限の監視、Kill Switch（data/kill.flag）発行
  - MonitoringEngine: 上記モニタをまとめてポーリング・アラート送出

- Portfolio construction（純粋関数群）
  - 候補選定、重み計算（等金額・スコア加重）
  - ポジションサイズ計算（単元丸め・利用可能資金に基づくスケーリング）
  - セクターキャップ・レジーム乗数適用

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの統計機能

- AI（OpenAI 使用）
  - news_nlp: ニュース記事を集約して LLM（gpt-4o-mini）で銘柄別センチメントを算出・保存
  - regime_detector: ETF の MA200 乖離とマクロニュースを統合して市場レジーム判定

- ユーティリティ
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート作成（tools/paper_verification_report.py）
  - ロギング設定、プロセス優先度制御などのユーティリティ関数群

---

## セットアップ手順（ローカル開発向け）

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください（venv / poetry 等）。

2. 依存パッケージのインストール（例）
   - 必要最低限の依存（主要なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証を行う場合のみ）
   - 例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```

   （リポジトリに requirements.txt がある場合はそれを利用してください）

3. プロジェクトルートの生成物
   - データベース / ログ用ディレクトリを作成（自動作成されることもありますが事前に用意しておくと安心です）:
     ```bash
     mkdir -p data logs
     ```

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成／更新できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ...
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動、default=instant）

5. 設定検証
   - 作成した設定を検証します（不足がないかチェック）:
     ```bash
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
     ```

---

## 使い方（主要スクリプト）

- ExecutionEngine（発注エンジン）起動
  - 通常実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレードで実行する場合:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - paper_trading を使うと MockBrokerClient が利用され、発注ログはデフォルトで data/paper_trading.db に保存されます（本番 DB と完全分離）。

  - 起動時の挙動:
    - プロセス優先度を "high" に設定（psutil 経由、権限により失敗する場合あり）。
    - sqlite/duckdb に接続し、Engine をスレッドで起動。
    - data/stop_requested.flag が存在すると起動を停止します（同様に実行中にフラグを置くと停止指示）。

- Monitoring（監視ループ）起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔の上書き:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）。
      ```bash
      MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
      ```
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを書き込みます。
    - 停止フラグファイル: data/stop_requested.flag を作成するとループを終了します。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼ぶ想定）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 呼び出す場合は OPENAI_API_KEY を設定するか api_key を引数で渡してください。

---

## 主要な環境変数（要約）

- KABUSYS_ENV: development | paper_trading | live（実行環境）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant, partial, never, reject）
- LOG_LEVEL: ログレベル（例: INFO）

---

## 運用・停止の仕組み

- Kill Switch:
  - RiskMonitor → KillSwitch が条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを検知して停止します。
  - Kill flag は Settings.kill_flag_path（デフォルト data/kill.flag）で指定可能。

- 停止フラグ（run_execution / run_monitoring）
  - data/stop_requested.flag を作るとそれぞれの起動スクリプトが検知して終了します。

- ログ:
  - ログはコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
  - ログディレクトリは自動作成を試みますが、権限エラー等で失敗する場合はコンソール出力のみになります。

---

## ディレクトリ構成（要点）

以下は src/kabusys 以下の主要ファイル / ディレクトリの概略です：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    (発注関連コンポーネント)

  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / CRUD ラッパ
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
    - news_nlp.py
    - regime_detector.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

その他: data/（DB・フラグファイル等）、logs/（ログファイル）が運用で使われます。

---

## 開発時の注意点・補足

- DB のマイグレーションやスキーマ変更は monitoring_db.init_monitoring_db で冪等に扱うよう考慮されています（既存カラム追加処理等）。
- Monitoring は常に Settings.sqlite_path（production 想定）へ書き込みます。テスト目的でモニタを実行する場合は sqlite_path を環境変数で上書きして分離してください。
- AI 周りは OpenAI API に依存します。API の失敗時はフェイルセーフ（スコア 0.0 など）で処理が継続する設計ですが、API キーの漏洩防止には注意してください。
- process_priority.set_process_priority() は OS ごとに実装差分があります。権限によっては設定に失敗することがあります（警告ログのみ）。

---

## よく使うコマンドまとめ

- .env を作る（ウィザード）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- 発注エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追加してほしい内容（例: 実行例のログ出力、requirements.txt の自動生成、CI 設定、より詳しい API ドキュメントなど）があれば教えてください。必要に応じて各モジュールの詳細（関数の使用例や入出力仕様）を別ドキュメントとして展開できます。