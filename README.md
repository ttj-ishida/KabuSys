# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築・注文実行・監視・研究・AI（ニュース NLP）などの主要コンポーネントを含むモジュール群です。

この README はリポジトリに含まれる主要な機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供します。

- 戦略・ファクター計算（research）
- ポートフォリオ構築・株数決定・リスク調整（portfolio）
- 発注エンジン（execution） — 本番・ペーパートレード対応
- 監視システム（monitoring） — システム状態・注文・リスクの定期チェック
- ニュースの NLP によるセンチメント評価（ai）
- 研究用ユーティリティ・ツール類（tools）
- 設定管理、ログ設定、プロセス優先度ユーティリティ（utils, config）

設計方針としては、DB（DuckDB/SQLite）をデータ層に用い、LLM（OpenAI）や外部 API は明示的に呼び出す箇所を限定してフェイルセーフ化しています。

---

## 主な機能一覧

- 設定管理
  - .env の自動ロード / 対話式ウィザード（kabusys.config_setup）
  - 起動前の設定検証 CLI（kabusys.validate_config）

- 実行（Execution）
  - ExecutionEngine：ブローカークライアント経由の発注、リスク管理、リコンシリエーション
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を利用し、専用 SQLite（デフォルト: data/paper_trading.db）へ記録

- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine の停止（KillSwitch）
  - 監視ログ永続化（SQLite monitoring.db）

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリー

- AI（ニュース NLP / レジーム判定）
  - raw_news を集約して OpenAI に送信し銘柄別センチメントを ai_scores に書き込み
  - マクロニュース × ETF MA の組み合わせで市場レジーム判定

- ポートフォリオ（Portfolio）
  - 候補選定、等金額/スコア加重、リスクベース株数算出、セクターキャップ等

- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - ログ設定（logs/<app>.log 日次ローテーション）
  - プロセス優先度・CPU affinity 設定

---

## 必要な依存関係（主なもの）

必須（実行する用途により一部はオプション）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML の検証を行う場合に推奨）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順

1. リポジトリをクローンしてワークスペースを準備します。

2. 仮想環境を作成し、依存パッケージをインストールします（上記参照）。

3. .env を作成
   - 対話式で作成する場合:

     ```bash
     python -m kabusys.config_setup
     ```

   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 主な環境変数（一覧）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL（デフォルト: INFO）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
     - KILL_FLAG_CLEAR_ON_START（本番で危険のためデフォルトは 0）

4. 設定検証（起動前に推奨）:

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリの準備（必要に応じて手動で作成されますが、ログ/DB のパーミッション等を確認してください）:

- data/ — PID・フラグ・DB（デフォルト）
- logs/ — ログファイル出力先

---

## 使い方（起動方法・主要コマンド）

起動スクリプトはパッケージモジュールとして実行できます。

- ExecutionEngine を起動（デフォルトは KABUSYS_ENV に応じて本番 or paper_trading を選択）:

```bash
python -m kabusys.run_execution
```

仕様メモ:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
- 起動時に data/stop_requested.flag が存在する場合は起動を中止します（停止フラグ）。
- 実行中は data/execution.pid にプロセス情報を書きます（設定で変更可）。

- Monitoring を起動（監視ループ）:

```bash
python -m kabusys.run_monitoring
```

仕様メモ:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
- 監視は常に本番 sqlite_path（SQLITE_PATH）を用いて initialisation します（環境にかかわらず）。
- data/stop_requested.flag が存在するとループ終了します。

- 設定ウィザード:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
```

- Paper Trading 検証レポート生成:

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

---

## 運用上のフラグ / ファイル

- data/stop_requested.flag
  - run_monitoring/run_execution が起動ループ内で検出すると安全停止シーケンスに入ります（存在チェックにより停止）。

- data/kill.flag
  - KillSwitch が評価条件に合致すると（例: ドローダウン超過等）作成され、ExecutionEngine に停止シグナルを送ります（Execution は起動時にオプションでクリアする挙動あり）。

- data/execution.pid
  - 実行プロセスの PID を記録（ExecutionEngine のデフォルトパス）。

- logs/<app>.log
  - 日次ローテーションで保存（utils.logging_setup を使用）。log_dir は LOG_DIR 環境変数またはデフォルト 'logs'。

---

## 環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / よく使う:
  - KABUSYS_ENV (development|paper_trading|live)
  - OPENAI_API_KEY (AI 機能利用時)
  - DUCKDB_PATH
  - SQLITE_PATH
  - PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL
  - MONITOR_POLL_INTERVAL
  - KILL_FLAG_CLEAR_ON_START

（設定ファイルや .env の例は config_setup で生成される .env を参照してください）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の概観です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数ロード・Settings クラス（アプリ設定一元管理）
  - config_setup.py
    - .env を対話式に作るウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - （発注ロジック、ブローカー抽象化、リスク制御等）

  - monitoring/
    - monitoring_db.py
      - SQLite に対する CRUD（system_status / trade_logs / positions / risk_logs / dashboard ）
    - system_monitor.py
      - CPU/メモリ/Disk/データ鮮度・プロセス PID チェック
    - trade_monitor.py
      - 注文の滞留・約定異常などのチェック（実装ファイルあり）
    - risk_monitor.py
      - ドローダウン・ポジション上限チェック
    - kill_switch.py
      - フラグファイルによる Execution 停止判定
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリング/アラート連携

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - ポートフォリオ構築の純粋関数群

  - research/
    - factor_research.py
      - Momentum / Volatility / Value などのファクター計算（DuckDB を利用）
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー等

  - ai/
    - news_nlp.py
      - raw_news → OpenAI → ai_scores 書込（バッチ、リトライ、バリデーションあり）
    - regime_detector.py
      - マクロニュース + ETF MA による市場レジーム判定（OpenAI 使用可）

  - tools/
    - paper_verification_report.py
      - ペーパートレード結果のレポート生成ツール

  - utils/
    - logging_setup.py
      - ルートロガー設定（stdout + 日次ファイルローテーション）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定（クロスプラットフォーム）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の取り扱いを慎重に設定してください。validate_config にて本番向けガードを出します。
- AI 機能（news_nlp, regime_detector）は OpenAI API キー（OPENAI_API_KEY）が必要です。失敗時はフォールバック挙動が定義されていますが、API 呼び出しはコストが発生します。
- 監視 DB（SQLITE_PATH）は monitoring コンポーネントが使用するため、バックアップやパーミッションに留意してください。
- ログはデフォルトで logs/ に出力され、日次ローテーション（30日分保管）されます。ログディレクトリが作成できない場合はコンソール出力にフォールバックします。
- データベースマイグレーションは monitoring_db.init_monitoring_db() にて簡易的なカラム追加を行います。大規模変更は慎重に行ってください。

---

## 追加情報 / 開発者向け

- 各モジュールはドキュメンテーションストリングを含んでおり、関数ごとに設計意図・引数・返り値・注記が書かれています。実装の詳細は各ファイルを参照してください。
- テストや CI 設定はこの README に含まれていません。ユニットテストを追加する際は外部 API 呼び出しをモック化してください（news_nlp 等では _call_openai_api の差し替えを想定しています）。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py など）が参照されています。存在しない場合はデフォルト .env で動作する箇所が多いですが、config YAML を使用する機能は実装に依存します。

---

必要であれば README に記載するコマンドの具体例（systemd / Supervisor / Docker 起動例）や、.env のテンプレート（JQUANTS_REFRESH_TOKEN=..., KABU_API_PASSWORD=... のサンプル）を追加で作成します。どの形式が必要か教えてください。