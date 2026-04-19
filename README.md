# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）です。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン、監視・アラート、研究用ユーティリティ、AI を用いたニュース解析などのコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール群を提供します。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ計算）
- 研究用ファクター計算（momentum / value / volatility 等）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント解析）
- Paper Trading（ペーパートレード）に対応する分離された DB
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、.env ウィザード、設定検証）

設計上の注意点：
- 環境変数 / .env を中心に設定を管理します（`kabusys.config.Settings`）。
- Paper Trading 環境は実運用 DB と完全分離されます（`data/paper_trading.db` 等）。
- AI 機能は OpenAI API キー（OPENAI_API_KEY）が必要です。

---

## 主な機能一覧

- 実行・発注
  - run_execution: ExecutionEngine を起動（`python -m kabusys.run_execution`）
  - Paper Trading では MockBroker を使用し、専用 SQLite に記録

- 監視
  - run_monitoring: SystemMonitor を定期実行（ポーリング）し監視ログを記録（`python -m kabusys.run_monitoring`）
  - RiskMonitor によるドローダウン・ポジション上限監視、KillSwitch による停止フラグ出力
  - AlertManager 経由で通知（LINE 等の統合はトークン設定に依存）

- ポートフォリオ構築
  - select_candidates / calc_equal_weights / calc_score_weights
  - apply_sector_cap / calc_regime_multiplier
  - calc_position_sizes（リスクベース、等配分、スコア配分）

- 研究（research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary

- AI（ニュース解析・レジーム検出）
  - news_nlp.score_news: raw_news を OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースを使って市場レジーム判定

- CLI ユーティリティ
  - config_setup: .env の対話式ウィザード（`python -m kabusys.config_setup`）
  - validate_config: 起動前の設定検証（`python -m kabusys.validate_config`）
  - tools.paper_verification_report: Paper Trading の検証レポート出力

---

## セットアップ手順

1. ソースをクローン / 取得

2. Python 環境を用意（推奨: venv）
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     pip install --upgrade pip
     ```

3. 必要なパッケージをインストール（プロジェクトに requirements.txt が無い場合は下記を目安に）
   - 必須（動作に必須）:
     - duckdb
     - psutil
   - AI 機能を使う場合:
     - openai
   - 設定検証で YAML を使う場合（任意）:
     - PyYAML
   - 例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```

4. 環境変数 (.env) を準備
   - 対話式ウィザードで生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を作成して必要な値を設定します（例は次節）。

5. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # 厳密モード（警告も FAIL）
   python -m kabusys.validate_config --strict
   ```

6. データ・ログディレクトリの確認
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/<app_name>.log

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

ランタイム用（監視・実行制御）:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

例: .env（config_setup が生成する内容に近い）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...
PAPER_FILL_MODE=instant
```

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）起動
  - 通常:
    ```bash
    python -m kabusys.run_execution
    ```
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中に同フラグが作成されると Engine 側で停止処理を行います。
    - PID は `data/execution.pid` に保存されます。

- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使って監視ログを記録します。

- Paper Trading 検証レポート出力
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコアリング / レジーム検出）
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - モジュールを呼び出す例（Python REPL やスクリプト内で）:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 運用上の注意

- Kill Switch / Stop フラグ
  - `data/kill.flag` — KillSwitch が書き込む停止トリガ（Execution 停止を要求）
  - `data/stop_requested.flag` — run_execution / run_monitoring の外部停止要求フラグ（存在すればループを抜けます）
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険。デフォルトは 0。

- ログ
  - デフォルトで stdout とファイル出力（logs/<app_name>.log）を併用します。
  - ログファイルは日次ローテート（30 日保持）。

- DB マイグレーション
  - monitoring の初期化関数は既存 DB にカラム追加等の簡易マイグレーション処理を行います（冪等）。

- プロセス優先度
  - 起動スクリプトは起動時にプロセス優先度を "high" に設定しようとします（権限によりスキップされる場合あり）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数 / .env 自動ロードと Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI 経由）
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite 永続化層（監視ログ）
  - system_monitor.py        — システム / データ鮮度監視
  - trade_monitor.py         — 発注ログ監視（ファイル内存在）
  - risk_monitor.py          — ドローダウン / ポジション上限監視
  - kill_switch.py           — Kill Switch 実装
  - monitoring_engine.py     — 複数 Monitor を束ねるエンジン
  - alert_manager.py         — （アラート送信ロジック）
- execution/
  - execution_engine.py      — ExecutionEngine 本体
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
- monitoring/
  - monitoring_db.py
- utils/
  - logging_setup.py         — ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

（上記は主要ファイルの抜粋です。実ファイルの詳細はソースを参照してください。）

---

## よくある操作例

- .env を新規作成して検証・起動まで:
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  python -m kabusys.run_monitoring &
  python -m kabusys.run_execution &
  ```

- Paper Trading レポート作成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-30
  ```

- AI 関連を実行する前のチェック:
  - OPENAI_API_KEY を設定
  - DuckDB 内に raw_news / news_symbols / ai_scores 等のテーブルが必要

---

## 開発 / 貢献

- コードのスタイルは PEP8 に準拠しています。ユニットテストや CI を追加すると良いでしょう。
- .env は機密情報を含むので絶対に Git にコミットしないでください。
- 新しい設定項目を追加する際は `kabusys.config.Settings` と `config_setup.py`、`validate_config.py` を合わせて更新してください。

---

この README はリポジトリ内の主要モジュール（実行スクリプト、監視、ポートフォリオ、研究、AI、ユーティリティ）に基づいて作成しています。さらに詳細な API ドキュメントや運用手順が必要であれば、その対象モジュールごとに別途ドキュメントを作成します。必要な箇所を教えてください。