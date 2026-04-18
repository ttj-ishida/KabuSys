# KabuSys

日本株自動売買システムのコアライブラリ（README）。  
このドキュメントはリポジトリ配下の主要スクリプト／モジュールの概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（発注エンジン）を支えるツール群です。  
主な機能は以下のとおりです。

- 発注実行（ExecutionEngine） — 本番 / ペーパートレードの切替、リスク管理、注文管理
- 監視（Monitoring） — システム状態・データ鮮度・取引ログ監視、Kill Switch（停止フラグ）発動
- ポートフォリオ構築 — 候補選定、重み計算、ポジションサイズ計算、セクター制限
- リサーチ / ファクター計算 — モメンタム、ボラティリティ、バリュー等のファクター計算
- AI ユーティリティ — ニュースを LLM（OpenAI）でセンチメント評価してスコア化、レジーム判定
- ユーティリティ群 — 設定ウィザード、設定検証ツール、ログ設定、プロセス優先度設定
- 運用ツール — ペーパートレード検証レポート生成など

設計上の特徴：
- DuckDB（分析用）と SQLite（監視/ペーパートレード用）を併用
- .env による環境変数管理（自動ロード機能あり）
- 本番/ペーパーを明確に分離（ペーパー時は専用 SQLite に書き込み）
- OpenAI を用いた自然言語処理機能を提供（環境変数 OPENAI_API_KEY を使用）

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV に応じて MockBroker を使い分け（paper_trading では専用 DB に記録）。
  - 停止フラグ（data/stop_requested.flag）を監視し、安全に停止。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。監視間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト60秒）。
  - 監視ログを SQLite に永続化。
- config_setup.py
  - 対話式ウィザードで .env を作成／更新。
- validate_config.py
  - 必須環境変数や config/*.yaml の存在/パースを検証。--strict オプションあり。
- tools/paper_verification_report.py
  - ペーパートレード DB を解析し検証レポートを出力（稼働率、注文成功率、レイテンシ等）。
- ai/news_nlp.py / ai/regime_detector.py
  - ニュースを LLM でスコアリングし ai_scores に書き込む、ETF とマクロニュースを組み合わせてレジーム判定。
- portfolio/*
  - 候補選定、重み計算、ポジションサイズ決定、セクターキャップ、レジーム係数の計算。
- research/*
  - DuckDB を使ったファクター計算、将来リターン、IC 計算、統計サマリー。
- utils/*
  - ログ設定、プロセス優先度 / CPU affinity 設定などの共通ユーティリティ。
- monitoring/*
  - MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager などの監視ロジック。

---

## セットアップ手順

前提：
- Python 3.10+ を推奨（型記法で | を使用）
- Git などの基本的ツール

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール
   必要なパッケージ（抜粋）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config の検証で推奨）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

   ※ sqlite3 は Python 標準ライブラリに含まれています。

4. .env の準備
   - 対話式ウィザードを使う：
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合はプロジェクトルートに `.env` を置く。（下記「環境変数」参照）

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリ作成（ログ / data）
   - ログ: `logs/`
   - データ: `data/`（SQLite / pid / フラグ類）
   多くの箇所で自動作成されますが、権限等に注意してください。

---

## 環境変数（主なもの）

主な環境変数（.env に設定）：
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
- PID_FILE_PATH, KILL_FLAG_PATH: パス上書き
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用、デフォルト 60）

自動ロード：
- プロジェクトルートにある `.env` と（存在すれば）`.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env の最小例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要コマンド）

各スクリプトはモジュールとして実行できます（モジュールの __main__ がエントリポイントになっています）。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録します。
  - 起動時に優先度を高く設定します（utils.process_priority）。
  - 停止フラグファイル data/stop_requested.flag を監視して終了します。
  - デフォルト PID ファイル: data/execution.pid（Settings で上書き可能）。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒です。環境変数 MONITOR_POLL_INTERVAL で変更できます。
  - 監視は常に（KABUSYS_ENV に依らず）本番用の sqlite_path を使用してログを残します。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db` で SQLite パスを直接指定可能。

- ライブラリ呼び出し（例）
  - AI スコア生成（コードから使用）
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) の戻り値
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```

ログ：
- setup_logging() により `logs/<app_name>.log` が日次ローテーションで保存されます。`LOG_DIR` または引数で変更可能。

停止 / Kill Switch：
- kill.flag（デフォルト：data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch）。
- 監視側が条件を満たすと kill.flag を書き込み、通知します。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内 `src/kabusys` の主要なファイル／ディレクトリ構成の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         (存在する前提の監視コード群)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         (存在する前提)
  - execution/
    - execution_engine.py     (実際の ExecutionEngine 実装)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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
  - data/                     — 実行時に生成されることが多い（SQLite / pid / フラグ / duckdb ファイル）
  - logs/                     — ログファイル出力先（デフォルト）

（注）上記はリポジトリ内の主要ファイルを抜粋したもので、実際のファイル一覧は差分があり得ます。

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では `.env` を厳重に管理し、`KILL_FLAG_CLEAR_ON_START=0` を推奨します。
- LINE 通知を使う場合は `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` を設定してください（本番で未設定だと警告）。
- OpenAI を使う機能は API キーが必要。レート制限やコストを考慮して運用してください。
- ログディレクトリ / data ディレクトリは実行ユーザに書き込み権限があることを確認してください。
- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を利用）。誤って本番 DB に書き込まないよう注意してください。
- validate_config.py で起動前チェックを行い、警告・エラーを解消してから本番環境で稼働させてください。

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt   # もし requirements.txt があれば
  pip install duckdb psutil openai pyyaml
  ```

- 初期設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定の検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 発注エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベース（src/kabusys）に基づく概要説明です。追加の運用手順やデプロイ方法（systemd / Docker / コンテナ化など）は運用ポリシーに合わせて別途整備してください。質問や追記してほしい項目があれば教えてください。