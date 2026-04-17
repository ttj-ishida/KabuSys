# KabuSys

日本株自動売買システムのサンプル実装リポジトリ（KabuSys）。  
この README はコードベース（src/kabusys/**）の使い方、セットアップ、主要機能、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は次のとおりです。

- 戦略に基づく銘柄選定・ポジションサイズ計算（Portfolio construction）
- 発注管理（ExecutionEngine）とブローカー抽象化（paper/live切替）
- システム稼働監視（Monitoring）・リスク監視と Kill Switch
- 研究用ファクター計算 / 特徴量探索（Research）
- ニュースの NLP を使ったセンチメント評価（AI モジュール）
- ペーパートレードの検証レポート出力ツール

設計方針として、実行系と研究系・監視系で DB を分離したり（paper_trading 用 DB など）、外部 API 呼び出しは明示的に分離してフェイルセーフを保つようになっています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（実際の発注ロジックを別モジュールで実装）
  - BrokerClientFactory により実環境と Mock（paper_trading）を切替可能
  - Paper trading は本番 DB と分離（デフォルト: `data/paper_trading.db`）
- Monitoring
  - SystemMonitor: CPU/Memory/Disk、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件で `data/kill.flag` を書き ExecutionEngine に停止シグナル
  - Monitoring DB（SQLite）への永続化（`monitoring_db.py`）
- Research
  - ファクター計算（momentum / volatility / value など）
  - forward returns、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を LLM で評価し ai_scores に保存
  - regime_detector.score_regime: マクロセンチメント＋MA で市場レジーム判定
- ツール
  - .env 生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

---

## 前提 / 必要パッケージ

最低限必要な外部パッケージ（例）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証時に必要。任意）

pip でインストールする例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそれを利用してください）

---

## 環境変数（代表）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 既定値:
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / ...
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: paper_trading 時の約定挙動（`instant`/`partial`/`never`/`reject`）
- PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: `data/kill.flag`）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

環境変数はプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化）。

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

2. .env の作成（対話型ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードで入力することで `.env` を生成します。
   - 生成後は `python -m kabusys.validate_config` で検証してください。
   - 本番（KABUSYS_ENV=live）の場合は LINE トークンなど通知設定を確認してください。

3. データディレクトリ作成（自動で作られるが手動でも可）
   ```bash
   mkdir -p data
   ```

4. 必要に応じて DuckDB / SQLite DB を用意。初回起動時にテーブルが自動作成されます。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の作成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  # 警告もエラー扱いにする場合
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）起動
  - 通常起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作:
    - プロセス優先度を "high" に設定します（psutil を利用）。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と分離）。
    - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
    - 停止は KillSwitch による `data/kill.flag` や `stop_requested.flag` を使って行えます。

- 監視ループ起動（Monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使って監視ログを記録します。
  - 停止は `data/stop_requested.flag` を作成するとループが終了します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（ニューススコア / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定する必要があります。
  - news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB コネクションに書き込みます。

---

## 停止・Kill フラグの扱い

- run_execution / run_monitoring の両方でチェックする停止フラグ: data/stop_requested.flag
  - 管理者がこのファイルを作成すると各ループは検知して終了します。
- KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（`Settings.kill_flag_path` でパス変更可能）。
- ExecutionEngine の PID ファイル: `data/execution.pid`（デフォルト、PID_FILE_PATH で変更可能）
  - SystemMonitor はこの PID ファイルで実プロセス存否をチェックし、stale PID を検出すると削除してアラートに記録します。

---

## .env の例（抜粋）

.env に含める代表的な項目:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意: `.env` は機密情報を含むため Git にコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理・自動 .env ロード
  - config_setup.py          # 対話式 .env ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                # 発注関連（OrderManager, Engine 等）
    - order_manager.py
    - execution_engine.py
    - broker_factory.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - monitoring/
    - monitoring_db.py       # SQLite 永続層
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
  - data/ (runtime)
    - monitoring.db (SQLite, デフォルト)
    - paper_trading.db (paper_trading 用 DB)
    - kabusys.duckdb
    - execution.pid
    - kill.flag / stop_requested.flag

（上記は主要ファイルの抜粋です。実際の実装はさらに細かいモジュールに分かれています）

---

## 運用上の注意・ティップス

- KABUSYS_ENV の切替:
  - `paper_trading` は Mock ブローカーを使い、本番 DB と完全分離します。テスト運用は paper_trading 推奨。
  - `live` を使う場合は通知設定や Kill Switch の設定に注意してください（validate_config がチェックします）。
- Monitoring は監視用 DB（SQLITE_PATH）にログを書きます。監視はデフォルトで production sqlite_path を参照します。
- MONITOR_POLL_INTERVAL は秒数（正の整数）を環境変数で上書きできます。無効な値は 60 秒にフォールバックします。
- OpenAI を使う機能は API 呼び出しの失敗に対してリトライ・フェイルセーフ実装がされていますが、API キーの漏洩には十分注意してください。
- psutil を用いてプロセス優先度や CPU affinity を設定します。権限によっては設定が失敗する可能性があるためログを確認してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent にテーブル作成と簡単なカラム追加（マイグレーション）を行います。

---

## 開発・拡張ポイント（参考）

- Strategy / Execution の実装はモジュール分離されているため、ブローカー実装や戦略ロジックの差し替えが容易です。
- position_sizing や risk_adjustment は純粋関数として実装されておりユニットテストが書きやすい設計です。
- AI 関連は外部 API（OpenAI）依存のため、ユニットテスト時は `_call_openai_api` をモックすることを推奨します。

---

この README はコードベースの主要機能と基本的な運用手順をまとめたものです。追加で
- デプロイ手順（systemd / Docker / コンテナ化）、
- 詳細な設定項目説明（config/*.yaml の仕様）、
- API ドキュメント（ExecutionEngine の公開メソッド等）
が必要であれば、対象に合わせて別途記載します。必要な内容を教えてください。