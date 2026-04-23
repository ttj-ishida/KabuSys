# KabuSys

日本株自動売買システムのリポジトリ（簡易 README、日本語）。

この README ではプロジェクト概要、主要機能、セットアップ手順、使い方（起動コマンド例）、およびディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコードベースです。主な要素は以下です。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を担う。
- 監視（Monitoring）: システム状態、注文・約定、リスクを定期的にチェックしアラートや Kill Switch を発動。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制限など。
- リサーチ / ファクター計算: DuckDB 上の市場データからファクターを計算（Momentum/Volatility/Value 等）。
- AI モジュール: OpenAI を用いたニュースのセンチメント評価（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ類: ロギング設定、プロセス優先度設定、設定ファイルウィザード/検証、ツール群（ペーパートレード検証レポート等）。

設計方針として、本番 DB とペーパートレード DB は分離されるようになっており、DuckDB を分析用に利用します。各モジュールは可能な限り副作用を抑え、テストしやすい純粋関数・明示的な依存注入を採用しています。

---

## 機能一覧

- 実行
  - ExecutionEngine（run_execution.py）での注文実行・監視・停止（Kill Switch 対応）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、専用 SQLite（data/paper_trading.db）へ記録
- 監視
  - SystemMonitor: CPU/メモリ/ディスク監視、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留や約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン、ポジション上限監視と永続化／リスクログ化
  - KillSwitch: 条件に基づき data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額/スコア加重、リスクベース配分、単元株丸め、セクター制限、レジーム乗数適用
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュースを LLM でセンチメント評価し ai_scores に保存
  - マクロニュースと ETF MA200 乖離による市場レジーム判定
  - API 呼び出しはバックオフやリトライ、フォーマット検証を実装
- ツール
  - 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - ペーパートレード検証レポート生成: python -m kabusys.tools.paper_verification_report
- ユーティリティ
  - 統一ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 自動読み込み（プロジェクトルートに基づく、無効化オプションあり）

---

## セットアップ手順（ローカル開発向け）

1. Python バージョン
   - Python 3.10 以上を推奨（typing の | 演算子などを使用）

2. 依存ライブラリ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証に任意）
   - （必要に応じて他の実装依存パッケージ）
   インストール例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに移動し、.env を作成
   - 対話ウィザードを使用する：
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で `.env` を作成してください。
   - 自動ロードを無効にする場合（テストなど）:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定を検証
   ```
   python -m kabusys.validate_config
   ```
   - 警告もすべてエラー扱いにする場合は `--strict` を付ける

5. 必要ディレクトリの作成
   - デフォルトでは以下のファイルパスが使われます（無ければ作成されます）:
     - data/monitoring.db（SQLite）
     - data/paper_trading.db（ペーパートレード用 SQLite）
     - data/kabusys.duckdb（DuckDB）
     - logs/（ログ）
   - 実行時に自動で生成される場所もありますが、権限等のため事前作成推奨

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（"instant"|"partial"|"never"|"reject"、デフォルト: "instant"）
- LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアするか ("0"/"1")

注意:
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（起動・実行例）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番・開発共通:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードで起動する場合（専用 DB を使用）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行開始前に data/stop_requested.flag（停止フラグ）が存在すると起動しません。

- 監視プロセス起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    export MONITOR_POLL_INTERVAL=30  # 30秒間隔
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings に基づき監視用 SQLite（SQLITE_PATH）および DuckDB へ接続します。
  - 監視は常に本番 sqlite_path を使用（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または `--db` で指定可能。

- AI モジュール呼び出し（プログラム内 API）
  - ニューススコアリング:
    ```
    from kabusys.ai import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="...")
    ```

- ログ
  - setup_logging によりコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）へ出力されます。
  - ログディレクトリは LOG_DIR 環境変数またはデフォルトの `logs/` を使用。

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では LINE 通知や kill flag の設定などを慎重に行ってください。validate_config は live 用の追加ガードを実行します。
- OpenAI API を使用する機能は API キーが必須です。API の障害時にはフェイルセーフ（デフォルト値の使用やスキップ）を行う設計ですが、挙動を理解した上で運用してください。
- ペーパートレードは本番データベースと完全分離するため、PAPER_TRADING_SQLITE_PATH を確認してください。
- Monitoring は常に本番 sqlite_path を参照する点に注意してください。Monitoring が監視対象 DB を参照して運用判断（Kill Switch 書き込み等）を行います。

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイル／フォルダと役割の概略です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、検証ユーティリティ）
  - config_setup.py
    - .env 作成ウィザード（対話式）
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、スレッド起動、停止制御）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整可能）
  - utils/
    - logging_setup.py
      - ロギング共通設定（Stream + 日次ローテート）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - （発注・注文管理・リスク管理の中心）
  - monitoring/
    - monitoring_db.py
      - SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度・プロセス存在監視
    - trade_monitor.py
      - 注文滞留・約定異常チェック（ソース省略）
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - kill_switch.py
      - stop flag 書き込みロジック
    - monitoring_engine.py
      - 各 monitor を束ねるポーリングエンジン
    - alert_manager.py
      - 通知管理（ソース省略だが存在を想定）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算
    - position_sizing.py
      - 株数決定・単元丸め・資金スケーリング
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - Momentum/Volatility/Value 等のファクター計算（DuckDB 参照）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py
      - ニュースを LLM でスコアリングし ai_scores へ書き込み
    - regime_detector.py
      - MA200 と LLM による市場レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成スクリプト

（上記は主要ファイルの概観です。細かい実装や補助モジュールはソースツリーを参照してください。）

---

## 開発 / テストのヒント

- .env の自動読み込みはプロジェクトルートを検出して行われます。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと副作用を避けられます。
- DuckDB 接続を外部から注入してユニットテストを書くと、データをメモリ上で用意して高速にテストできます。
- AI 呼び出しはモジュール内の `_call_openai_api` を patch してモック化すると良いです（テストでの外部 API を避けるため）。

---

## 参考コマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- Paper Trade レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に環境変数一覧の完全テーブル、ユースケース別の起動手順（開発 / ステージング / 本番）、およびデプロイ（systemd / docker / k8s）向けのサンプルユニットファイル/Dockerfile を追加で作成します。どの情報を追加したいか教えてください。