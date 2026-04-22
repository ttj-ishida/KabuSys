# KabuSys

日本株向け自動売買システム KabuSys のリポジトリ用 README（日本語）。

概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）とそれを支える監視・検証・研究用コンポーネントを含むシステムです。  
主な設計方針は「本番口座・発注系 API から分離した研究処理」「フェイルセーフ（API失敗時のフォールバック）」「ルックアヘッドバイアス回避」です。

主要要素：
- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム稼働状況、注文やリスクの監視、Kill Switch（停止フラグ）を提供
- Portfolio モジュール：候補選定、重み計算、ポジションサイジング等の純粋関数
- Research モジュール：ファクター計算、特徴量探索、IC 等の算出
- AI モジュール：OpenAI を使ったニュースセンチメント評価やレジーム判定
- 開発用ツール：.env ウィザード、設定検証、ペーパートレード検証レポート等

---

## 機能一覧

- 環境設定管理（.env 読み込み・ウィザード）
- 起動前設定検証 CLI（`validate_config`）
- ExecutionEngine（本番 / ペーパートレード切替）
  - ブローカークライアントの抽象化（本番 or Mock）
  - 注文管理・リスク管理・突合せ（reconciler）
- Monitoring
  - システム状態（CPU/メモリ/ディスク）監視
  - 注文ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（閾値超過で data/kill.flag を作成）
  - 監視ループ起動スクリプト（`run_monitoring.py`）
- 研究（Research）
  - モメンタム・ボラティリティ・バリュー計算（DuckDB を使用）
  - 将来リターン・IC・統計サマリー
- AI（OpenAI）
  - ニュースのセンチメントを LLM によりスコア化（ai_scores へ書き込み）
  - 市場レジーム判定（ma200 + マクロ記事センチメントの合成）
- ツール
  - .env 環境設定ウィザード（`config_setup.py`）
  - 設定検証（`validate_config.py`）
  - ペーパートレード検証レポート生成（`tools/paper_verification_report.py`）
- ログ管理：コンソール（stdout） + 日次ローテートファイル（logs/*.log）

---

## 必要条件

- Python 3.9+（コードは型ヒント等を使用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - psutil
- 任意 / 推奨
  - PyYAML（config/*.yaml 検証用）
- SQLite（組み込み）を利用
- （実際に取引する場合）kabuステーション等のブローカ API 設定

※ requirements.txt が別途ある場合はそちらを使ってください。典型的なインストール例は下記。

---

## セットアップ手順

1. リポジトリをクローン・作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）

   macOS / Linux:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール（例）

   ```bash
   pip install duckdb openai psutil
   # もし PyYAML を使う場合
   pip install PyYAML
   ```

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

4. .env を作成する（ウィザードを使用）

   対話式ウィザードで .env を作成できます：
   ```bash
   python -m kabusys.config_setup
   ```

   または手動で .env をプロジェクトルートに配置してください（.env.example を参照）。

5. 設定を検証

   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数 / 主要設定

主に .env に設定するキー（抜粋）：

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: MockBroker を使用し `data/paper_trading.db` に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知）

実行時に上書き可能な一部パラメータ：
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔〔秒〕、デフォルト 60）

Kill / Stop に関するファイル：
- データディレクトリ: data/
  - data/kill.flag — Kill Switch による実行停止フラグ（KillSwitch が書き込む）
  - data/stop_requested.flag — run_* スクリプトが検知してプロセスを安全に終了するためのフラグ
  - data/execution.pid — ExecutionEngine の PID ファイル（起動時に使用）

---

## 実行方法（基本）

リポジトリ構成に応じ、モジュールとして直接起動します。

- ExecutionEngine を起動（本番 or ペーパートレードは KABUSYS_ENV で切替）

  ```bash
  # KABUSYS_ENV を .env または環境変数で設定してから起動
  python -m kabusys.run_execution
  ```

  ペーパートレードにしたい場合:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行中に data/stop_requested.flag が作成されると安全に停止します。

- Monitoring（ポーリング監視ループ）を起動

  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を上書きしたい場合
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  こちらも data/stop_requested.flag を検知して終了します。Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視ログは一元管理）。

- ペーパートレード検証レポートを生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 開発者向け / モジュールの使い方

- 設定ウィザード（対話式）:
  - `python -m kabusys.config_setup`

- 設定検証:
  - `python -m kabusys.validate_config [--strict]`

- ロギング:
  - 全スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name="...")` を呼び出します。ログは標準出力と `logs/<app_name>.log` に日次ローテーションで保存されます。

- Research / Portfolio / AI モジュールの呼び出し（Python API）
  - 例: モメンタム計算
    ```python
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    results = calc_momentum(conn, date(2026, 4, 15))
    ```
  - AI: ニューススコアリング
    ```python
    from datetime import date
    from kabusys.ai import score_news
    import duckdb

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 15), api_key="sk-...")
    ```

- Kill Switch:
  - `KillSwitch` は `data/kill.flag` を作成し、ExecutionEngine に停止シグナルを与えます。kill.flag は ExecutionEngine 側での保護のためにチェックされます。

---

## 監視・停止フロー（補足）

- 監視モジュールは SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、条件に応じて KillSwitch を作動させます。
- KillSwitch が write する `data/kill.flag` は ExecutionEngine 起動時や実行中にチェックされます（ExecutionEngine は paper/live によらずこのフラグを監視）。
- 管理者が単純にプロセスを終了させたい場合は `data/stop_requested.flag` を作成すると run_* スクリプト群が順次安全に停止します。

---

## ディレクトリ構成（主要ファイル）

概略ツリー（src/kabusys 配下の主要ファイル）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・.env の自動読み込みと Settings
  - config_setup.py          # .env ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (参照用・実装による)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    # 実行時に使用される（/data/*.db, *.flag, *.pid 等）
  - logs/                    # ログ出力先（デフォルト）

※ 上はリポジトリ内の主要コンポーネントを抜粋したものです。実際のファイルはさらに細分化されています。

---

## 備考 / 運用上の注意

- .env は機密情報（APIキー等）を含むため、Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- 本番（KABUSYS_ENV=live）で運用する際は LINE 等の通知設定を必ず確認してください。validate_config は live 時の注意点もチェックします。
- OpenAI を使用する機能は API コストやレイテンシが発生します。APIキーは環境変数 `OPENAI_API_KEY` に設定してください。
- Monitoring は監視 DB（SQLite）へ書き込みを行います。監視 DB は運用上の重要ソースになるためバックアップ・権限の管理を推奨します。
- process_priority / cpu_affinity の設定は OS 権限に依存します。権限不足では設定できない可能性があるためログを確認してください。

---

## バージョン

パッケージの __version__ は `src/kabusys/__init__.py` に定義されています（例: 0.1.0）。

---

必要であれば README にサンプル .env の雛形、より詳細な起動例（systemd / cron 用 unit / service ファイル例）、テスト手順、CI 設定例などを追加できます。どの情報を優先して追加しますか？