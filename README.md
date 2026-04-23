# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買フレームワークです。戦略の研究・ファクター計算・ポートフォリオ構築・発注実行・監視・ペーパートレード検証・AI（ニュース NLP / レジーム判定）などの機能群を含みます。

以下はこのコードベースの概要・機能・セットアップ・使い方・ディレクトリ構成です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から成る自動売買基盤です。

- データベース（DuckDB / SQLite）を用いたデータ管理
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築・リスク調整・ポジションサイズ算出（portfolio）
- 発注実行エンジン（ExecutionEngine）と注文管理（paper/live 対応）
- 監視コンポーネント（System/Trade/Risk Monitor）と Kill Switch
- ニュースを LLM でスコアリングする AI モジュール（OpenAI）
- ペーパートレードの検証レポート生成ツール
- 環境設定ウィザード・設定検証 CLI、ログ設定ユーティリティ等

設計上の特徴：
- DB（DuckDB / SQLite）を使ったオフライン処理が可能（研究・検証分離）
- Paper Trading（KABUSYS_ENV=paper_trading）時は発注をモックにて完全分離
- AI を利用する処理は APIキーが未設定だと例外またはフェイルセーフを取る

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード、対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading と Live を切り替え可能（専用 SQLite に分離）
- 監視
  - System / Trade / Risk モニタと MonitoringEngine（run_monitoring.py）
  - Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
- ポートフォリオ構築
  - 候補選択、等重／スコア加重、リスクベース位置付け、セクターキャップ
- 研究（Research）
  - モメンタム／ボラティリティ／バリューなどのファクター計算（DuckDB 使用）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（news_nlp.score_news）
  - マクロニュースと ETF MA を使った市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
  - Monitoring DB 永続化層（kabusys.monitoring.monitoring_db）

---

## 必須・推奨依存関係

推奨 Python バージョン: 3.10+（型注釈に Python 3.10 の構文を使用）

主な Python パッケージ（プロジェクトにより必要な機能が異なります）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合）
- その他（用途に応じて）

インストール例:
```
python -m pip install duckdb psutil openai pyyaml
```

（requirements.txt があればそれを使ってください）

---

## 環境変数（主要）

validate_config と Settings モジュールから抜粋した主要変数：

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）
- OPENAI_API_KEY — AI 機能で必要
- PAPER_FILL_MODE — paper_trading の埋め方（instant|partial|never|reject）, デフォルト: instant

設定ファイルは .env（プロジェクトルート）に置くことを想定しています。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

PAPER_FILL_MODE の有効値: "instant", "partial", "never", "reject"

---

## 初期セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai pyyaml
   ```
4. 対話式ウィザードで .env を生成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに従い JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等を入力してください。

5. 設定の自動検証
   ```
   python -m kabusys.validate_config
   ```
   警告も厳密に扱う場合は `--strict` を付けます。

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/` に DB や flag ファイルを保存します。
   - ログは `logs/` に日次ローテートされます（logging_setup 使用時）。

---

## 使い方（主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパートレード切替は KABUSYS_ENV による
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード: KABUSYS_ENV=paper_trading を .env に設定すると MockBrokerClient を使い、data/paper_trading.db に記録します。
  - 実行停止:
    - `data/stop_requested.flag` を作成すると起動中の run_execution は検知して停止します。
    - Kill Switch（監視側）がトリガーすると `data/kill.flag` が書かれ、ExecutionEngine は停止するよう設計されています。

- 監視ループ起動（Monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔の変更:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60 秒）。
    - 例: `MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring`
  - 監視は実行環境に関わらず本番 sqlite_path を利用して監視 DB を保持します。

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env の初期作成/更新（対話式ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB パスは `data/paper_trading.db`。`--db` で指定可能。

- AI 機能（プログラムから呼び出す）
  - ニュース NLP スコア付け:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="...")  # target_date は datetime.date
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")
    ```

---

## 停止・制御（フラグファイル）

- 一時停止 / 停止を制御するフラグや PID ファイル:
  - data/stop_requested.flag — run_monitoring / run_execution の外部停止用（存在検知で停止）
  - data/kill.flag — Kill Switch（監視から Execution を強制停止するために書き込まれる）
  - data/execution.pid — ExecutionEngine の PID ファイル（run_execution が利用）
- KillSwitch は監視結果（ドローダウン等）に応じて `kill.flag` を書きます。既に存在する場合は再書き込みしない（冪等）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイルとディレクトリ（src/kabusys 配下を中心に）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB レイヤ
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        — （コードベースに含まれる想定のモジュール）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信を担う想定のモジュール）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                     — 実行時に生成される DB / flag / pid（ルートの data/）
  - logs/                     — ログ（デフォルト）

注: 上記は主なモジュールを抜粋したものです。詳細はソースツリーを参照してください。

---

## 開発・デバッグのヒント

- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` を使って統一的に行っています。`logs/<app_name>.log` に日次ローテートで保存されます。
- 設定検証（validate_config）は起動前に .env や config/*.yaml の不備を検出するのに便利です。
- Paper Trading は本番 DB と完全分離される設計です（PAPER_TRADING_SQLITE_PATH を使う）。
- AI 機能は OpenAI API を利用するため、API キーの管理に注意してください。API 呼び出しはリトライやフォールバックを備えていますが、コストやレイテンシを考慮して運用してください。
- ストップや強制停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で行います。手動でフラグを作成・削除して動作を確認できます。

---

## よくあるコマンドまとめ

- .env 作成（対話式）:
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
  python -m kabusys.run_monitoring
  ```

- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README は概要です。各モジュールの詳細な仕様・設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）がある場合はそちらも参照してください。追加で README に含めたい具体的なコマンド例や .env のテンプレートがあれば教えてください。必要に応じて追記します。