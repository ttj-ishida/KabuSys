# KabuSys

日本株自動売買システムのコアライブラリ群と起動 / 運用用スクリプト群を含むリポジトリです。  
この README はコードベース（src/kabusys 以下）の主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株向けの自動売買エンジン（ExecutionEngine）と監視コンポーネント（Monitoring）、および研究用ユーティリティ群（ファクター計算、ポートフォリオ構築、AI を用いたニュース評価など）を提供します。  
設計方針の要点：

- 本番 / ペーパートレードを分離（環境変数 `KABUSYS_ENV` により切替）
- DuckDB を分析用途に、SQLite を監視 / 発注履歴などの永続化に使用
- OpenAI を使ったニュース NLP / レジーム判定コンポーネントを内包（API キー必須）
- .env ベースでの環境設定、対話式ウィザードと検証ツールを提供
- ロギング・プロセス優先度設定など運用に必要なユーティリティを同梱

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（本番 / paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（監視ログ蓄積・Kill Switch 連携）
- 設定管理 / ツール
  - config_setup.py — .env 対話式ウィザード（初期作成・更新）
  - validate_config.py — 環境設定・config/*.yaml の事前検証
- 監視
  - monitoring/monitoring_engine.py — 各種 Monitor（System / Trade / Risk）を束ねる
  - monitoring/monitoring_db.py — 監視ログ用 SQLite スキーマ・読み書き
  - monitoring/kill_switch.py — kill.flag による ExecutionEngine 停止機構
- 発注・実行関連（Execution）
  - execution/* — ブローカークライアント生成、OrderManager、RiskManager、ExecutionEngine 等（実行系の心臓部）
- ポートフォリオ構築
  - portfolio/* — 候補選定、重み付け、ポジションサイズ計算、セクター上限など純粋関数群
- 研究（Research）
  - research/* — ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算
- AI（OpenAI）
  - ai/news_nlp.py — raw_news を集約して LLM でセンチメントを評価し ai_scores に書き込む
  - ai/regime_detector.py — ETF の MA とマクロセンチメントを合成して市場レジーム判定
- ユーティリティ
  - utils/logging_setup.py — 統一的なロギング設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- 運用ツール
  - tools/paper_verification_report.py — ペーパートレード DB を基に合否判定の検証レポート生成

---

## 要件（依存ライブラリ）

主な依存（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — validate_config で config/*.yaml の内容検証をする場合

インストール例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実際は requirements.txt / poetry 等を用意している場合はそれに従ってください。）

---

## セットアップ手順（推奨順）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 初期環境変数の作成（対話式ウィザード推奨）

  - 対話式で .env を作る:
    ```
    python -m kabusys.config_setup
    ```
    これにより .env を生成または更新できます。

5. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # 警告も厳格に FAIL 扱いにしたい場合
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリ作成（data, logs など）:
   - 多くのコードは `data/` や `logs/` を参照します。必要に応じて作成してください。
     ```
     mkdir -p data logs
     ```

7.（任意）DuckDB / SQLite に必要なデータを投入
   - research / ai モジュールは prices_daily, raw_news 等のテーブルを期待します。データロード手順は別途用意してください。

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用・設定:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文成立動作）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- Kill / Stop フラグ等:
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

.env は絶対に Git にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine の起動（実行系）
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録します（PAPER_TRADING_SQLITE_PATH を参照）。

- Monitoring の起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 監視は本番 sqlite_path を使います（環境にかかわらず）。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング（Python API）
  - ニュース NLP をプログラムから呼ぶ例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - OpenAI API キーは引数で与えるか環境変数 `OPENAI_API_KEY` を利用します。

- 研究用モジュール（Python API）
  - 例: モメンタム計算
    ```python
    from kabusys.research import calc_momentum
    from datetime import date
    import duckdb

    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, target_date=date(2026,4,1))
    ```

- ログ設定ユーティリティ（スクリプト内で利用）
  ```python
  from kabusys.utils.logging_setup import setup_logging
  setup_logging(app_name="execution")
  ```

---

## 運用上のポイント

- stop / kill の仕組み
  - run_execution/run_monitoring は `data/stop_requested.flag`（または `data/kill.flag`）の存在を見て停止・シグナル動作を行います。フラグの作成/削除でプロセスの制御ができます。
  - KillSwitch（監視からの自動停止）は `data/kill.flag` を作成します。`KILL_FLAG_CLEAR_ON_START` を必要に応じて確認してください（本番では自動クリアは推奨されません）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は起動時に必要なテーブルと最小限のマイグレーション（カラム追加）を行います。DuckDB / SQLite に期待するテーブルが存在することを確認してください。

- ログ
  - デフォルトは `logs/<app_name>.log` に日次ローテーションで出力されます。log ディレクトリが作れない場合はコンソール出力のみになります。

- 権限
  - `psutil` を使ったプロセス優先度設定・CPU affinity 設定は権限不足により失敗することがあります（実行時に警告が出ますが動作は継続します）。

---

## ディレクトリ構成（抜粋）

```
src/kabusys/
├── __init__.py
├── config.py                    # 環境変数 / 設定読み込みロジック
├── config_setup.py              # .env 対話式ウィザード
├── validate_config.py           # 設定検証 CLI
├── run_execution.py             # ExecutionEngine 起動スクリプト
├── run_monitoring.py            # SystemMonitor ポーリング起動スクリプト
├── tools/
│   └── paper_verification_report.py
├── utils/
│   ├── logging_setup.py
│   └── process_priority.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── monitoring_engine.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   └── alert_manager.py
├── execution/
│   ├── execution_engine.py
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── broker_factory.py
│   ├── reconciler.py
│   └── risk_manager.py
├── portfolio/
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── news_nlp.py
│   └── regime_detector.py
└── data/                         # 実際にはリポジトリに含まれない（runtime 用）
    ├── monitoring.db
    ├── paper_trading.db
    ├── kabusys.duckdb
    ├── execution.pid
    ├── stop_requested.flag
    └── kill.flag
```

- 各モジュールは docstring とコメントに実装 / 使用上の注意を書いています。API を呼ぶ際はそれらを参照してください。

---

## よくある操作例

- 監視ループを 30 秒間隔で起動（環境変数で上書き）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード DB を使って Execution を起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Kill Switch を手動で解除（起動時に自動クリアしない設定の場合）:
  ```
  rm -f data/kill.flag
  ```

---

## 開発上のメモ / 注意事項

- .env の自動ロード:
  - `config.py` はプロジェクトルート（.git または pyproject.toml がある場所）を探し、`.env` → `.env.local` の順に自動で読み込みます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本番環境 (`KABUSYS_ENV=live`) 設定時は LINE 通知設定や kill flag の取り扱いなどを慎重に確認してください（validate_config に警告チェックあり）。
- OpenAI を使う機能は外部 API に依存するため、キー管理とレート制限に注意してください。AI 呼び出しはリトライやフォールバックを持つ実装ですが、適切なモニタリングが必要です。

---

README はここまでです。必要であれば次の追加を作成できます：

- 具体的な開発用セットアップ（テストデータの生成スクリプト、Docker-compose 等）
- 各モジュール（ExecutionEngine / MonitoringEngine / AI）の API 使用例・設計ドキュメント抜粋
- requirements.txt / poetry 設定ファイル

どの情報を優先して追加しますか？