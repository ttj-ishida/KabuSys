# KabuSys

日本株自動売買システムの一部モジュール群（リサーチ・ポートフォリオ構築・実行エンジン補助・監視・AI 補助など）。

---  

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数（必須 / 任意）
- 運用メモ・注意点
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するユーティリティ群を集めたパッケージです。  
このリポジトリには、下記の機能を提供するモジュール群が含まれます（DB 操作、ファクター計算、ポートフォリオ構築、発注支援、監視、AI を使ったニュース解析など）。  
設計方針としては、可能な限り副作用を抑えた純粋関数と、DB / API への接続を明示的に受け取る実装を採用しています。

---

## 主な機能（機能一覧）

- 環境設定
  - 対話式ウィザードで `.env` を生成 / 更新（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- Execution / Monitoring
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し paper DB に分離
  - System Monitor ポーリングスクリプト（kabusys.run_monitoring）
    - 監視用 SQLite（monitoring.db）へ状態を保存
- 監視関連
  - SystemMonitor（システム負荷・データ鮮度監視）
  - TradeMonitor（発注ログ等の監視）
  - RiskMonitor（ドローダウン・ポジション数監視、Kill Switch 判定）
  - MonitoringEngine（複数 Monitor を束ねてポーリング）
  - MonitoringDB（SQLite のテーブル作成 / 永続化ラッパー）
- ポートフォリオ構築（純関数）
  - 候補選定、重み計算、セクターキャップ、レジーム乗数、ポジションサイズ計算
- リサーチ / ファクター計算（DuckDB を利用）
  - モメンタム、ボラティリティ、バリュー等のファクター計算（prices_daily, raw_financials 参照）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）連携
  - ニュース NLP（raw_news を集約して LLM でセンチメントを算出、ai_scores に保存）
  - 市場レジーム判定（ETF MA 乖離 + マクロセンチメントを合成）
  - 失敗時はフェイルセーフ（部分失敗でも既存データを保護する実装）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10+（| 型注釈を使用しているため）
- OS: Linux / macOS / Windows（プロセス優先度などは OS に依存して挙動が変わります）

例: 仮想環境を作成して依存を入れる

```bash
git clone <this-repo>
cd <this-repo>
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
```

依存パッケージ（最低限）をインストール:

```bash
pip install duckdb psutil openai
# 監視や検証で YAML を検証したい場合は:
pip install pyyaml
```

（プロジェクトに requirements.txt / pyproject がある場合はそれに従ってください。上記は本 README の参照環境に基づく最低依存例です。）

初期設定 (.env) の生成:

```bash
python -m kabusys.config_setup
# 対話式にプロンプトが出ます。完了後 .env を生成します。
```

設定検証:

```bash
python -m kabusys.validate_config
# --strict をつけると warning も失敗扱いになります
```

データディレクトリ:
- デフォルトで使用する DB / PID / フラグファイル等は `data/` 配下に置かれます（例: data/monitoring.db, data/kabusys.duckdb, data/execution.pid）。
- ログはデフォルト `logs/` に出力されます（kabusys.utils.logging_setup を使用）。

---

## 使い方

主な実行コマンド（モジュールを直接実行）:

- 環境ウィザード（.env 作成 / 更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution エンジンを起動
  - 本番 / ペーパーは KABUSYS_ENV による切り替え:
    - KABUSYS_ENV=paper_trading の場合は paper DB に分離して MockBroker を使います。
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring を起動（ポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30秒間隔
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート（CLI）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB の指定は PAPER_TRADING_SQLITE_PATH 環境変数か --db オプション
  ```

- AI 関連（プログラムから呼び出す例）
  - news_nlp（ニュースをスコアして ai_scores に書き込む）
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数で与えるか第3引数で渡す
    score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
  - regime_detector（市場レジーム判定）
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```

停止・Kill:
- 実行系の停止フラグ: `data/stop_requested.flag` が存在すると run_execution / run_monitoring のループが終了します（run_execution は起動検査時に既にあれば起動を抑止します）。
- Kill Switch: `data/kill.flag` を監視により作成すると、ExecutionEngine に停止を促す仕組みがあります（KillSwitch クラス）。
- Execution 停止 PID: `data/execution.pid` に PID を出力する運用になっています。

ログ:
- ログは `logs/` 以下に保存され日毎にローテートされます（`kabusys.utils.logging_setup.setup_logging`）。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用 / 動作制御:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite (paper_trading 用)
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の fill モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする（開発用、0/1）

（validate_config.py にも必須・推奨項目の一覧があります）

---

## 運用メモ / 注意点

- Monitoring は環境にかかわらず `sqlite_path`（本番監視 DB）を使用します。Execution は `KABUSYS_ENV=paper_trading` のときに paper 用 DB を使用して本番 DB と分離します。
- `KABUSYS_ENV=live` 設定は本番運用に直結します。LINE 通知や kill フラグ運用など、設定を慎重に確認してから使用してください（validate_config は live 時のガードも持っています）。
- OpenAI 連携:
  - API 呼び出しはリトライ処理や JSON バリデーションを実装していますが、API キーの漏洩やコストに注意してください。
  - レスポンスの形式は厳密な JSON を期待していますが、不正なレスポンスは安全にスキップされます。
- ログディレクトリ作成に失敗した場合はコンソールログのみで継続します。
- プロセス優先度（set_process_priority）はプラットフォーム依存です。権限不足のときは警告を出してスキップされます。
- データベースマイグレーション:
  - monitoring_db.init_monitoring_db() は既存スキーマにカラムがない場合に ALTER TABLE で追加を行う処理が含まれており、冪等に実行できます。

---

## 代表的なファイル・ディレクトリ構成

（簡潔化したツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数・設定管理
    - config_setup.py             — .env ウィザード
    - validate_config.py          — 設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (参照あり)
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (参照あり)
    - execution/                   — Execution 系（Broker, Engine, OrderManager 等）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

- data/    — 実行時に利用する DB / フラグ / pid（例: data/monitoring.db, data/kabusys.duckdb, data/kill.flag, data/stop_requested.flag）
- logs/    — ログ（デフォルト）
- config/  — 設定テンプレート YAML（system_config.yaml など。生成スクリプトや例がある場合があります）

---

この README はコードベースの主要な使い方と運用上の注意点をまとめたものです。  
実行前に `python -m kabusys.config_setup` → `python -m kabusys.validate_config` を実行して設定漏れや環境の問題を事前に検出することを強く推奨します。必要があれば、利用する OS / デプロイ環境に応じた追加手順（サービス化 / systemd / Supervisor の設定等）を行ってください。