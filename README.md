# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ兼実行スクリプト群）。  
この README はソースツリー（src/kabusys）に基づいて作成しています。

概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成などを記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・モニタリングを目的としたシステムです。  
主な役割は次のとおりです。

- 注文実行エンジン（ExecutionEngine）
  - 本番・ペーパートレードの分離、リスク管理、注文管理、約定の追跡
- 監視（Monitoring）
  - システム稼働状況、データ鮮度、注文の滞留や約定異常、ドローダウン監視
  - 必要に応じて Kill Switch（`data/kill.flag`）を書き込んで実行エンジンを停止
- ポートフォリオ構築（選定・重み付け・数量算出）
- リサーチ（ファクター計算、特徴量探索、IC 計算 等）
- AI（OpenAI を利用したニュースセンチメント、レジーム判定）
- 運用ツール（ペーパートレード検証レポート等）

設計上の特徴：
- 本番 DB とペーパートレード DB を分離（`KABUSYS_ENV=paper_trading` 時）
- .env による設定管理（interactive ウィザード・検証 CLI を提供）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB として使用
- ロギングは統一的にセットアップ（stdout + 日次ローテートファイル）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - ブローカークライアント抽象化（実ブローカー / MockBroker 切替）
  - リスク管理（ポジション上限、ドローダウンなど）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch による安全停止（kill.flag）
- Portfolio
  - 候補選定、等重・スコア加重の重み計算
  - ポジションサイジング（リスクベース、単元株丸め、集約キャップ）
  - セクター上限、レジーム乗数の適用
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - 将来リターン、IC、ファクター要約
- AI
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に書込
  - レジーム判定（ETF MA200 + マクロニュース）
- Tools
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- 設定支援
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## 必要条件・依存ライブラリ

以下は主要な依存例（requirements.txt は本リポジトリに含まれていないため、必要なものをインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合）
- 標準ライブラリ（sqlite3 等）

インストール例（venv を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数 / .env

自動で `.env` をロードする仕組みがあります（プロジェクトルートを基準に `.env` と `.env.local` を読み込み）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（一部、デフォルト値含む）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- OPENAI_API_KEY (AI 機能利用時)
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定方式
- KILL_FLAG_CLEAR_ON_START (0 | 1) — 本番で 1 にするのは危険

推奨: `python -m kabusys.config_setup` で対話的に `.env` を作成・更新してください。作成後は `python -m kabusys.validate_config` で検証できます。

例: 最小の .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. `.env` を作成（`python -m kabusys.config_setup` を推奨）
4. 設定を検証（`python -m kabusys.validate_config`）
5. 必要に応じてデータディレクトリを作成（ログ、DB 保存先などは自動作成されることが多い）

監視 DB・テーブルは起動スクリプトが初回実行時に自動作成・マイグレーションを行います（monitoring_db.init_monitoring_db を参照）。

---

## 実行方法・使い方

基本的にモジュールを直接実行します。

- ExecutionEngine を起動（本番 or ペーパートレード）
  - 本番（例）
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBroker を使い data/paper_trading.db に記録）
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中のプロセス優先度は高（high）に設定されます。起動時に `data/stop_requested.flag` が存在すると起動をスキップします。実行中は `data/execution.pid` に PID を書きます。

- Monitoring を起動
  - ポーリングで各種モニタを動作させます（デフォルト 60 秒間隔）。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（1 秒以上の整数）。
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 監視ループは `data/stop_requested.flag` の存在で終了します。監視は常に本番用の sqlite_path を使用します（監視のログは production の monitoring.db に残る想定）。

- Paper Trading 検証レポート
  - 過去期間のペーパートレード結果を評価する CLI:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定できます。

- .env 作成 / 設定検証
  - 対話ウィザード:
    ```bash
    python -m kabusys.config_setup
    ```
  - 検証:
    ```bash
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
    ```

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - ライブラリ関数として呼び出す設計です。簡単な呼び出し例（Python REPL やスクリプト）:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect('data/kabusys.duckdb')
    # target_date: datetime.date オブジェクト
    count = score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定（regime_detector）も同様に `score_regime(conn, target_date, api_key=...)` を呼びます。
  - 失敗時はフェイルセーフでデフォルト値（スコア 0.0 等）にフォールバックする設計です。

停止・強制停止関連:
- `data/stop_requested.flag`：run_monitoring / run_execution のポーリングループを終了させるために使われる内部停止フラグ（存在すると起動をスキップあるいは実行中に停止）。
- `data/kill.flag`：KillSwitch が書き込み、ExecutionEngine 側で検出すると安全停止へのトリガーとなります。`KILL_FLAG_CLEAR_ON_START=1` により起動時の自動クリアが可能（本番では推奨しない）。

ログ:
- `kabusys.utils.logging_setup.setup_logging` により stdout と `logs/<app_name>.log` に日次ローテートで出力されます（デフォルト保存先: `logs/`）。

---

## 設定の重要ポイント / 注意事項

- KABUSYS_ENV の値は `development`, `paper_trading`, `live` のいずれか。`live` は本番のため設定・アクセスに注意。
- Paper Trading モードは実際の発注を行わず MockBroker による記録を行う設計。データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に保存され、本番 DB と分離されます。
- OpenAI 使用時は API レート制限や通信エラーに対してリトライやフェイルセーフ実装がありますが、API キーと課金・利用方針には注意してください。
- ログディレクトリ作成・ファイル書込に失敗した場合はコンソール出力のみになります。権限やパスに注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルと役割の概観です（一部抜粋）。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数/.env の自動読み込み、Settings クラス（設定アクセス）
- src/kabusys/config_setup.py
  - .env 対話式ウィザード
- src/kabusys/validate_config.py
  - 設定検証 CLI
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト
- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- src/kabusys/utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度・CPU affinity 設定
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ・永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py ...
- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- src/kabusys/research/
  - factor_research.py, feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py, regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py

（上記はファイルの抜粋説明です。より詳細は各モジュールの docstring コメントを参照してください。）

---

## 開発・拡張のヒント

- DuckDB 接続を与えてリサーチ系関数を呼ぶ設計になっているため、データ整備（prices_daily / raw_financials / raw_news テーブル）を行えばローカルで解析が可能です。
- 設定項目は config/*.yaml と .env に分かれています。`validate_config` は YAML のパースチェックを行います（PyYAML が必要）。
- openai SDK のバージョン差分やレスポンス形式に備えて、news_nlp/regime_detector は厳密なバリデーションとリトライを実装しています。テスト時は API 呼び出し部分をモックできます（モジュール内の _call_openai_api をパッチ）。

---

## 参考コマンド一覧

- .env の作成ウィザード
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 監視プロセス起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 実行エンジン起動（ペーパートレード）
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの概要を伝えるためのまとめです。各モジュールの詳細な使用法・ API（関数の引数や返り値等）は、該当ソースファイルの docstring を参照してください。必要であれば各モジュールごとの詳細ドキュメントも作成します。