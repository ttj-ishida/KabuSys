# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
この README はコードベースの主要コンポーネント、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究プラットフォームです。  
主な目的は以下：

- シグナル生成とポートフォリオ構築（ファクター計算・リサーチ）
- 発注/実行エンジン（実口座／ペーパートレード切替）
- 監視（システム状態、注文状況、リスク監視）と Kill Switch
- ニュース NLP を使った AI スコアリング・レジーム判定
- Paper Trading の検証レポート生成

設計方針として、DuckDB/SQLite をデータ層に用い、外部 API（kabuステーション、J-Quants、OpenAI）は設定に基づいて呼び出します。テスト・開発用にペーパートレードモード（MockBroker）を用意しており、本番 DB と分離されます。

---

## 機能一覧

- 環境設定ウィザード（.env の対話生成）: `kabusys.config_setup`
- 設定検証 CLI（.env・config/*.yaml の検査）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `run_execution.py`
  - KABUSYS_ENV によりペーパートレード（`paper_trading`）と本番（`live`）を切替
  - paper_trading では MockBrokerClient を用い、`data/paper_trading.db` を使用
- 監視ポーリング（SystemMonitor のループ）: `run_monitoring.py`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）
  - 監視は環境にかかわらず本番用の sqlite_path を使用
- MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard の永続化
- MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor をまとめて実行、アラートと Kill Switch 処理
- RiskMonitor: ドローダウン・ポジション上限の監視とログ化
- KillSwitch: `data/kill.flag` により ExecutionEngine の停止指示
- ポートフォリオ構築ユーティリティ（候補選定、重み、ポジションサイズ、セクター制限など）
- リサーチモジュール（ファクター計算、forward returns、IC、統計要約）
- AI モジュール
  - news_nlp: ニュースのセンチメントを OpenAI でスコアリングして `ai_scores` に保存
  - regime_detector: ETF とマクロ記事を元に市場レジーム判定して `market_regime` に保存
- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提: Python 3.9+ を想定（実際の互換性は pyproject.toml を参照してください）。

1. リポジトリをクローンして作業ディレクトリに移動します。

2. 仮想環境を作成して依存をインストールします（例）:
   - pip を使う場合:
     ```
     python -m venv .venv
     source .venv/bin/activate  # PowerShell/Windows の場合は別コマンド
     pip install -r requirements.txt
     ```
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証をする場合に任意）

   ※ requirements.txt がない場合は、上の主要パッケージを個別にインストールしてください。

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   主要な必須環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）

   代表的な設定（.env に書かれる項目）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb（分析用）
   - SQLITE_PATH: data/monitoring.db（監視用）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード DB）
   - LOG_LEVEL: INFO（デフォルト）
   - KILL_FLAG_CLEAR_ON_START: 0 | 1

   自動読み込み:
   - プロジェクトルートの `.env` / `.env.local` は起動時に自動読み込みされます（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 自動検出は `.git` または `pyproject.toml` を基準とします。

4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告を FAIL として扱う
   ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - ポイント:
    - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し、`paper_sqlite_path`（デフォルト: `data/paper_trading.db`）に書き込みます。
    - 起動時に `data/stop_requested.flag` が存在すると起動しません。
    - 実行中は `data/execution.pid` に PID を書きます（設定で変更可）。

- 監視ループ（SystemMonitor）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定可能（デフォルト: 60）。
  - 監視は monitoring 用 SQLite（Settings.sqlite_path）にログを保存します。監視は環境にかかわらず本番 sqlite_path を使用します。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで検知してループを終了します。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - 引数なしの場合は全期間。`--db` オプションで DB を指定可能。
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` も DB 指定に使用できます（デフォルト: `data/paper_trading.db`）。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- AI 機能を使う（news_nlp / regime_detector）
  - OpenAI API を使用するため `OPENAI_API_KEY` を設定する必要があります（引数で渡すことも可能）。
  - これらは DuckDB 接続を受け取りスコアリング結果をテーブルへ書き込みます。

ログ
- ログ出力は標準出力とファイル（logs/<app_name>.log）に日次ローテーションで保存されます。ログディレクトリは環境変数 `LOG_DIR`、ログレベルは `LOG_LEVEL` で設定可能。

停止制御（Kill Switch / stop flag）
- `data/kill.flag` : KillSwitch が評価して書き込むファイル。ExecutionEngine はこのフラグにより停止される想定。
- `data/stop_requested.flag` : run_monitoring / run_execution の外部停止用フラグ。存在時にループや起動を停止します。

---

## 環境変数（代表一覧）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログ保存ディレクトリ)
- MONITOR_POLL_INTERVAL (監視ループの秒間隔)
- KILL_FLAG_CLEAR_ON_START (1 にすると ExecutionEngine 起動時に kill.flag を消去)

注意:
- `config.py` により `.env` / `.env.local` は自動ロードされます（オーバーライド制御あり）。自身で読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル）

```
src/kabusys/
├── __init__.py                 # パッケージ定義、__version__
├── config.py                   # 環境変数 / Settings
├── config_setup.py             # .env 対話式ウィザード
├── validate_config.py          # 設定検証 CLI
├── run_execution.py            # ExecutionEngine 起動スクリプト
├── run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
├── tools/
│   └── paper_verification_report.py  # ペーパートレード検証レポート
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py             # ニュース NLP スコアリング
│   └── regime_detector.py      # 市場レジーム判定
├── monitoring/
│   ├── monitoring_db.py        # SQLite スキーマ + MonitoringDB ラッパー
│   ├── monitoring_engine.py    # 各 Monitor を束ねる Engine
│   ├── system_monitor.py       # システム状態・データ鮮度監視
│   ├── trade_monitor.py        # （未掲載）注文関連監視（コードベース参照）
│   ├── risk_monitor.py         # ドローダウン・ポジション監視
│   ├── kill_switch.py          # kill.flag 操作用ユーティリティ
│   └── alert_manager.py        # （未掲載）アラート通知管理
├── execution/
│   ├── execution_engine.py     # （参照）実行エンジン本体
│   ├── broker_factory.py       # Broker クライアント生成（Mock/実運用）
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   └── risk_manager.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py    # 候補選定・重み
│   ├── position_sizing.py      # 発注株数計算
│   └── risk_adjustment.py      # セクター制限・レジーム乗数
├── research/
│   ├── __init__.py
│   ├── factor_research.py      # モメンタム/バリュー/ボラティリティ計算
│   └── feature_exploration.py  # IC/統計サマリ等
└── utils/
    ├── __init__.py
    ├── logging_setup.py        # ログ設定ユーティリティ
    └── process_priority.py     # プロセス優先度/CPU affinity 設定
```

- `monitoring_db.py` に監視用テーブルのスキーマとマイグレーションロジックが含まれます。
- 実装の一部（例: TradeMonitor、AlertManager、ExecutionEngine の詳細など）は別ファイルに分割されています。各モジュール内の docstring を参照してください。

---

## 注意点 / 運用メモ

- 本番モード（KABUSYS_ENV=live）では設定ミスが重大事故につながるため `validate_config.py` による事前検証を強く推奨します。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で危険です（自動で kill.flag をクリアするため）。デフォルトは `0`。
- Logging: ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソールのみの出力になります。
- プロセス優先度: 起動スクリプトは開始直後に `set_process_priority("high")` を試みます。権限不足等で設定できない場合は警告ログが出ます。
- AI モジュールは OpenAI API 呼び出しを行うため、レート制限やエラーに対して実装側でリトライ＆フェイルセーフを用意していますが、API キーやコスト管理に注意してください。
- データの整合性確保のため、DB 書き込みではトランザクション（BEGIN/COMMIT/ROLLBACK）が使われる部分があります。

---

## よく使うコマンドまとめ

- .env を作る（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動（MONITOR_POLL_INTERVAL 秒でポーリング）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じてこの README をプロジェクトの状況に合わせて更新してください。さらに詳しい API や設計文書（PortfolioConstruction.md、StrategyModel.md 等）がある場合、それらを参照すると実装の背景と意図がより明確になります。

何か特定の部分について詳述が必要であれば教えてください。README を拡張してコマンド例、設定例、トラブルシュートなどを追加します。