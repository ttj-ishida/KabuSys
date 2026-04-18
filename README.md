# KabuSys

日本株自動売買システムの Python パッケージ群（ライブラリ + 起動スクリプト群）。  
このリポジトリには、発注エンジン、監視用ループ、ポートフォリオ構築、リサーチ（DuckDB ベース）、AI ベースのニュース解析などの実装が含まれます。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成されます。

- execution: 発注・リスク管理・オーダー管理を担う ExecutionEngine（本番 / ペーパートレード対応）
- monitoring: システム稼働監視、取引監視、リスク監視、Kill Switch（フラグファイル）などの自動監視
- portfolio: 銘柄選定・重み算出・ポジションサイズ計算・セクター制限
- research: DuckDB を使ったファクター算出・特徴量探索
- ai: OpenAI（gpt-4o-mini など）を使ったニュースセンチメント・レジーム判定
- utils: ロギング設定・プロセス優先度設定などのユーティリティ
- tools: レポート生成などのユーティリティスクリプト
- config: 環境変数管理・自動読み込み・設定検証ウィザード

設計上のポイント:
- 本番 DB（監視用 SQLite）とペーパートレード用 DB は分離されています（KABUSYS_ENV に依存）。
- DuckDB は分析・リサーチ用に使用します（prices_daily / raw_financials 等）。
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0.0 など）で動作します。
- .env の自動読み込みと対話式ウィザード、設定検証 CLI を提供します。

---

## 機能一覧

- ExecutionEngine
  - 本番 / ペーパートレード（MockBroker）切替
  - リスク管理（最大ポジション率、回路遮断、ドローダウン監視など）
  - PID ファイル管理（data/execution.pid 等）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 発注プロセス稼働チェック
  - TradeMonitor: 注文の滞留、異常約定検知（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、risk_logs への記録
  - KillSwitch: 条件により data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ

- Portfolio
  - 候補選定（スコア順）、等金額／スコア加重配分
  - 単元丸め・ポジションサイズ計算（risk_based 等）
  - セクター集中制限、レジーム乗数

- Research / Tools
  - DuckDB を使ったファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

- AI
  - ニュース NLP による銘柄センチメント生成（OpenAI 回り込み、バッチ送信・リトライ）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## 前提 / 依存関係

- Python 3.10+
- 推奨パッケージ（少なくとも以下をインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の中身検証を行う場合、任意）
- SQLite（標準ライブラリ sqlite3 を使用）
- (任意) その他、requirements.txt がある場合はそれに従ってください。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 環境を準備（仮想環境推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成（ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは J-Quants トークン、kabu API パスワード、ログレベル、DB パス等を対話的に設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等の作成（通常はスクリプトが自動作成するが手動で準備することも可）
   - デフォルト DB/ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログディレクトリ: logs/

---

## 使い方

- 起動スクリプト（CLI）

  - ExecutionEngine を起動:
    ```
    python -m kabusys.run_execution
    ```
    - KABUSYS_ENV によって動作が切り替わります:
      - development: 発注なし（開発）
      - paper_trading: MockBrokerclient を使用、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用
      - live: 本番ブローカーを使用
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中に data/stop_requested.flag を作成すると安全に停止します（ループが検知して engine.stop() を呼び出します）。

  - Monitoring を起動:
    ```
    python -m kabusys.run_monitoring
    ```
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）。
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（monitoring DB）を使用します。
    - 終了は data/stop_requested.flag の作成、または Ctrl+C。

- 設定ウィザード / 検証
  - .env 作成:
    ```
    python -m kabusys.config_setup
    ```
  - 設定検証:
    ```
    python -m kabusys.validate_config
    ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を使う場合
  python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite
  ```

- AI モジュール（ライブラリとして呼び出す）
  - ニューススコア生成:
    ```
    from kabusys.ai.news_nlp import score_news
    # score_news(conn, target_date, api_key=None)
    ```
    - API キーは引数または環境変数 OPENAI_API_KEY を使用します。

  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    # score_regime(conn, target_date, api_key=None)
    ```

- 停止・Kill Switch
  - Monitoring や CLI が Kill 判定をすると data/kill.flag を書き込みます（Settings.kill_flag_path、デフォルト data/kill.flag）。
  - Execution 起動時に kill_flag_clear_on_start が 1 に設定されていると自動クリアされます（本番では 0 推奨）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

（完全なキーやデフォルト値は kabusys.config.Settings を参照してください）

---

## ログ / DB / フラグについて

- ログ:
  - 標準出力（stdout）とファイル（日次ローテーション）に出力されます。
  - デフォルトログディレクトリ: logs/
  - ログファイル名はアプリ名（例: execution.log, monitoring.log）

- DB:
  - DuckDB: 分析用（prices_daily, raw_financials 等）
  - SQLite: 監視ログ・トレードログ（monitoring.db）およびペーパートレード用 DB（paper_trading.db）

- フラグ / PID:
  - data/stop_requested.flag: run_execution / run_monitoring の外部停止用（存在検知で安全終了）
  - data/kill.flag: KillSwitch による ExecutionEngine 停止指示
  - data/execution.pid: ExecutionEngine の PID ファイル（設定により場所変更可能）

---

## ディレクトリ構成（主要ファイル）

プロジェクトルートの src/kabusys 以下の代表的なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ループ起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/
    - (ExecutionEngine, BrokerFactory, OrderManager, RiskManager, 等...)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
  - data/                    — 既定の data/ 配下に DB / pid / flag を置く想定
  - tools/
    - paper_verification_report.py

（実際のファイルはリポジトリの src/kabusys 配下を参照してください）

---

## 開発者向けメモ / 注意点

- Settings は自動でプロジェクトルートを検出して .env をロードします（CWD に依存しない）。
- run_monitoring は MONITOR_POLL_INTERVAL を参照します。0 以下や不正な値が指定された場合はデフォルト 60 秒にフォールバックします。
- Monitoring は monitoring DB を使用するため、Monitoring のテーブル作成（マイグレーション）は init_monitoring_db が担います（冪等）。
- Paper trading と本番は DB を分離しており、ペーパートレードでは MockBroker を用いて data/paper_trading.db に記録します。
- OpenAI の呼び出しはリトライ実装あり（429/接続エラー/タイムアウト/5xx 等を対象）。API キーは環境変数か引数で渡してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0（デフォルト）にすることを強く推奨します。

---

## よく使うコマンドまとめ

- .env 作成（対話式）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードの主要点をまとめたもので、より詳細な挙動や設計思想は各モジュール（特に execution/, monitoring/, ai/, research/ 以下）の docstring / コメントを参照してください。必要であれば README に追加したい情報（例: 起動例、環境変数の完全一覧、運用手順など）を教えてください。