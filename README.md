# KabuSys

日本株向けの自動売買 / リサーチ基盤（モジュール群）の README。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・AI ニューススコアリング・調査用ユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したモジュール群です。主な役割は以下の通りです。

- 価格データや財務データを使ったファクター計算（research）
- ポートフォリオ構築（portfolio）
- 注文管理 / 発注エンジン（execution）
- システム稼働・注文状態・リスクを監視する仕組み（monitoring）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ai）
- Paper Trading の検証・レポート生成ツール（tools）
- 環境変数/設定の読み込み・ウィザード・検証ツール（config*, validate_config）

設計方針として、DB（SQLite / DuckDB）を使った分析・ログ保存、OpenAI 呼び出し時のリトライとバリデーション、プロセス優先度やログ管理の共通化などが実装されています。

---

## 主な機能一覧

- config_setup: 対話式で .env を作成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: 起動前に環境変数や config/*.yaml の整合性を検証（python -m kabusys.validate_config）
- run_execution: 発注エンジン ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` では MockBroker を使用し paper_trading DB に記録
- run_monitoring: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録・アラート評価
- monitoring_engine: 複数の Monitor（System / Trade / Risk）を束ねるエンジン
- Kill Switch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る
- AI ニュース NLP: raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存
- regime_detector: マクロセンチメントと ETF の MA 乖離を合成して market_regime を判定
- research: momentum / volatility / value ファクター、forward returns、IC 計算、統計サマリー
- portfolio: 候補選定、重み計算、セクターキャップ適用、ポジションサイズ計算
- tools.paper_verification_report: Paper Trading DB から検証レポートを生成

---

## 依存関係（例）

主なランタイム依存パッケージ（環境や用途により増減します）:

- python >= 3.10（型注釈に | を使用）
- duckdb
- psutil
- openai
- PyYAML（validate_config 内の YAML 検証に optional）
- その他（標準ライブラリのみで動く部分も多い）

実際はプロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。

インストール例:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートに合わせる。

2. Python 仮想環境を作成し、依存をインストールする。
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし用意されていれば
   ```

3. 初期 `.env` を作成（対話式ウィザード推奨）。
   ```bash
   python -m kabusys.config_setup
   ```
   重要な環境変数（最低限設定が必要なもの）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - OPENAI_API_KEY: AI 機能を使う場合必要
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用: デフォルト data/paper_trading.db）
   - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）

4. 設定検証（任意）:
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

5. データディレクトリ作成（.env に指定したパスに応じて自動生成されることもあるが、手動で作ると安全）:
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド例）

- 監視プロセス起動（デフォルトポーリング間隔 60秒。MONITOR_POLL_INTERVAL で上書き可能）
  ```bash
  python -m kabusys.run_monitoring
  # または短い間隔にする例
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  注意:
  - Monitoring は環境にかかわらず本番用の sqlite_path (Settings.sqlite_path) を使用します。
  - 停止方法: プロジェクトルートにある `data/stop_requested.flag` を作成するとループが終了します。

- 発注エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
  動作:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い `data/paper_trading.db` に記録（本番 DB と分離）。
  - 起動時には `data/execution.pid` を使って PID 管理。
  - 停止: `data/stop_requested.flag` による検知で停止する仕組みがあります。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI（ニュース NLP / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定してから呼び出してください。
  - 例: Python スクリプトや REPL から:
    ```py
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    # duckdb 接続を生成し、target_date を指定して呼び出す
    ```

---

## 重要な挙動・フラグ類

- stop_requested.flag
  - 監視・実行スクリプトはプロジェクト内 `data/stop_requested.flag` の存在をチェックして自ら終了します（外部から安全に停止させるため）。

- kill.flag
  - KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine に停止シグナル（緊急停止）を送ります。`KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に自動クリアされますが、本番では `0` を推奨します。

- PID ファイル
  - ExecutionEngine は `data/execution.pid` を PID 管理に使用します。

- ログ
  - 共通ロギング設定により stdout とファイル（logs/<app_name>.log）へ出力します。ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。

- DB
  - DuckDB（分析用）: デフォルト `data/kabusys.duckdb`
  - SQLite（監視ログ）: デフォルト `data/monitoring.db`
  - Paper trading 用 SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading時に使用）

---

## 環境変数の主な一覧

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要/任意:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定モード)
- OPENAI_API_KEY (AI 機能を使用する場合)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログディレクトリ)
- KILL_FLAG_CLEAR_ON_START (0/1)
- PID_FILE_PATH / KILL_FLAG_PATH などは Settings 経由で上書き可

詳しくは `src/kabusys/config.py` と `src/kabusys/validate_config.py` を参照してください。

---

## ディレクトリ構成（主なファイル／モジュール）

以下は src/kabusys 以下の主要なファイル・パッケージ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定の読み込みと Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py           — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py    — 市場レジーム判定
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ・永続化層
    - system_monitor.py
    - trade_monitor.py      — （trade_monitor の存在を前提）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （アラート送信管理の想定）
  - execution/
    - execution_engine.py   — 実行エンジン（EngineConfig 等）
    - broker_factory.py     — BrokerClientFactory
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                   — デフォルトの DB / flag 等を置く想定ディレクトリ（リポジトリには含めないのが推奨）

（実際の repository ではさらに細分化されています。上は主要モジュールの抜粋です）

---

## 運用上の注意点

- 本番モード（KABUSYS_ENV=live）では設定ミスが重大な損失に繋がるため、`validate_config` で設定チェックを必ず行ってください。
- `KILL_FLAG_CLEAR_ON_START=1` は開発時に便利ですが本番では危険（kill.flag が不意にクリアされる）ため `0` を推奨します。
- Monitoring は常に本番用の sqlite_path を使用する設計になっています（開発環境でも監視 DB の意図しない上書きに注意）。
- OpenAI API を使うモジュールは API 呼び出しの失敗をフェイルセーフに処理しますが、API キーの漏洩に注意してください。
- DuckDB / SQLite はファイルロックやバックアップに注意。長期稼働環境では定期バックアップを推奨します。

---

## よくある操作例（まとめ）

- .env を作る / 更新する:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config --strict
  ```

- 監視開始:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（ペーパートレード）:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。README に載せきれない詳細（各モジュールの API、DB スキーマ、実行フロー詳細など）はソースコード内の docstring を参照してください。追加で「導入手順の自動化」「テスト実行例」「CI 設定」などを README に追記したい場合は指示ください。