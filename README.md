# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、戦略計算・ポートフォリオ構築、実行エンジン、監視、AI ユーティリティ、分析ツールを含む自動売買フレームワークの実装です。DuckDB / SQLite をデータ永続化に用い、kabuステーション API や J-Quants、OpenAI を外部サービスとして利用できます。

## 概要
- 実トレード / ペーパートレード両対応（`KABUSYS_ENV` により切替）
- ExecutionEngine による発注管理・リスク管理・照合
- Monitoring コンポーネント（System / Trade / Risk）による常時監視と Kill Switch
- 研究用モジュール（ファクター計算、特徴量解析）
- AI モジュール（ニュースセンチメントによるスコアリング、レジーム判定）
- ツール類（.env ウィザード、設定検証、Paper Trading 検証レポート）

## 主な機能一覧
- 環境設定ウィザード（.env 生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env や config/*.yaml の事前チェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合はモックブローカーを使用し、Paper DB（デフォルト: `data/paper_trading.db`）へ記録
  - PID ファイル管理（デフォルト: `data/execution.pid`）
- 監視プロセス起動スクリプト: `kabusys.run_monitoring`
  - System / Trade / Risk 監視をポーリングし、monitoring DB（デフォルト: `data/monitoring.db`）へ記録
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）でオーバーライド可（デフォルト 60 秒）
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成して行う
- Kill Switch（`data/kill.flag` を書き込む）による ExecutionEngine 強制停止
- AI
  - ニュース NLP スコアリング: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（ma200 + マクロニュース + LLM）: `kabusys.ai.regime_detector.score_regime`
- 研究 / 分析
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン / IC 計算等
- ツール
  - Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`

## 必要な依存ライブラリ（主なもの）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- PyYAML（config YAML 検証を行う場合に必要）

（テストや一部機能は追加依存がある可能性があります。setup/requirements ファイルがあればそちらを参照してください）

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境の作成と有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール（例）
   ```bash
   pip install duckdb psutil requests openai pyyaml
   ```

4. 環境変数設定（.env を作成する方法は次節参照）
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/よく使う環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
     - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

5. 初期設定ファイル作成（対話ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードに従って .env を作成・更新してください。

6. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

## 使い方（主要スクリプト／コマンド例）

- 監視プロセス起動
  ```bash
  # ポーリングループを開始（MONITOR_POLL_INTERVAL を秒で指定可）
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - 監視は常に「本番（production）用 sqlite_path」を使用する設定です（Monitoring は環境に依存せず監視 DB を参照します）。
  - 停止方法: プロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループが終了します。

- 実行エンジン起動
  ```bash
  # 通常起動（KABUSYS_ENV に従う）
  python -m kabusys.run_execution

  # ペーパートレード環境で起動する例
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - paper_trading の場合は MockBrokerClient を使い、発注・約定ログは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録され、本番 DB と分離されます。
  - 実行中の停止は `data/stop_requested.flag` 作成で行えます（run_execution は起動時に同ファイルが存在する場合は起動しません）。

- .env の作成・編集
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（前述）
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定・DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 機能（ライブラリ関数として利用）
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB 内のテーブル（raw_news / prices_daily / ai_scores / market_regime 等）を参照します。
  - OPENAI_API_KEY が必要です（関数引数で渡すことも可）。

## 停止・Kill Switch
- 監視スクリプトや実行エンジンはプロジェクトルート下の `data/stop_requested.flag` による停止を監視しています。停止させたい場合はこのファイルを作成してください。
- Kill Switch（`data/kill.flag`）は監視ロジックが異常を検出した際に書き込まれ、ExecutionEngine 側で検知して安全に停止します。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に kill.flag を自動クリアしますが、本番（live）では危険なためデフォルトは 0（クリアしない）を推奨します。

## .env（主要項目の例）
以下は .env に含めるべき主要キー例（実際には `python -m kabusys.config_setup` を使って作成してください）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABUSYS_ENV=development|paper_trading|live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=...
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- LINE_CHANNEL_ACCESS_TOKEN=... (任意)
- LINE_USER_ID=... (任意)

## ディレクトリ構成
（リポジトリの主要ファイル / ディレクトリ）
```
src/
  kabusys/
    __init__.py
    config.py                     # 環境変数読み込み・Settings
    config_setup.py               # .env ウィザード CLI
    validate_config.py            # 設定検証 CLI

    run_execution.py              # ExecutionEngine 起動スクリプト
    run_monitoring.py             # Monitoring ポーリング起動スクリプト

    execution/                    # 発注エンジン関連（Engine, OrderManager, Reconciler, RiskManager 等）
      ...

    monitoring/
      monitoring_db.py            # monitoring 用 SQLite 永続化レイヤ
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py
      kill_switch.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      news_nlp.py                  # ニュース NLP スコアリング（OpenAI）
      regime_detector.py           # 市場レジーム判定（OpenAI）
      __init__.py

    tools/
      paper_verification_report.py

    data/ (実行時に使用するディレクトリ・ファイル例)
      execution.pid
      stop_requested.flag
      kill.flag
      monitoring.db                # デフォルト SQLITE_PATH
      paper_trading.db             # PAPER_TRADING_SQLITE_PATH
      kabusys.duckdb               # DUCKDB_PATH
```

各サブパッケージ（execution, monitoring, portfolio, research, ai）はそれぞれ責務が分離されています。monitoring_db.py は DB スキーマ初期化（マイグレーション含む）を提供し、冪等に実行できます。

## 実運用時の注意
- 本番環境（KABUSYS_ENV=live）では設定値・キー管理を厳密に行ってください。`validate_config` は live の場合に追加警告を出します。
- OpenAI や外部 API を使用する機能は API キーや通信エラーに依存します。デフォルトでリトライやフェイルセーフが実装されていますが、レート制限やコストに注意してください。
- psutil を使用してプロセス優先度 / CPU affinity を変更しています。権限やプラットフォームによっては設定に失敗することがあります（警告ログ）。
- DB ファイルはデフォルトで `data/` 下に置かれます。適切な配置・バックアップ・アクセス権限を確保してください。
- .env は絶対に Git にコミットしないでください（`config_setup._write_env` のヘッダにも注意喚起があります）。

---

上記がこのコードベースの README（概要・セットアップ・使い方・構成）です。必要であれば、起動フロー図、より詳細な環境変数説明表、デプロイ手順（systemd / supervisor 用のサンプル unit / service ファイル）なども追記できます。どの追加情報が必要か教えてください。