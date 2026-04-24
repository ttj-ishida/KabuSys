# KabuSys

日本株自動売買システムの実装骨組み（ライブラリ＋起動スクリプト群）。

このリポジトリは、シグナル生成やポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュースセンチメント評価などを含む自動売買システムのコア部分を提供します。実運用（live）・ペーパートレード（paper_trading）・開発（development）の切り替えに対応しています。

## 主な特徴（機能一覧）

- ExecutionEngine（発注エンジン）
  - 本番/ペーパートレードモード切替
  - ブローカークライアントファクトリで実環境 or モックに対応
  - リスク管理（Rate limit / max_position / drawdown など）

- Monitoring（監視）
  - System / Trade / Risk の各モニタリング
  - SQLite に監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）を永続化
  - Kill Switch（条件に応じて data/kill.flag を書き出し発注エンジン停止）

- Portfolio construction
  - 候補銘柄選定、等金額／スコア加重、セクターキャップ適用、レジーム乗数
  - ポジション・サイズ計算（単元株丸め、aggregate cap 対応）

- Research / Data
  - DuckDB を使ったファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン・IC（情報係数）計算、特徴量サマリ

- AI 関連
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート出力ツール

## 前提（推奨環境）

- Python 3.9+
- 必要パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で推奨）
- SQLite（Python 標準ライブラリで利用）
- ネットワーク接続（本番で外部 API を使う場合）

（requirements.txt はリポジトリに含まれている場合はそちらを参照してください）

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

## セットアップ手順

1. リポジトリをクローン/配置する。

2. Python 仮想環境を作成して依存をインストールする（任意）。
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -U pip
   python -m pip install duckdb psutil openai PyYAML
   ```

3. .env を作成する
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動で配置し、必須キーを設定してください（例は下記）。

4. 設定検証を実行:
   ```bash
   python -m kabusys.validate_config
   # 警告も厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. DB ファイル等は起動時に自動作成される場合があります（config のパスに依存）。デフォルト:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading 時)

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値を含む）:
- KABUSYS_ENV: execution モード (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant|partial|never|reject） — デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — デフォルト: 60
- KILL_FLAG_CLEAR_ON_START: 本番起動時に kill.flag を自動クリアするか（0/1） — デフォルト: 0

注意: .env.example を参考に .env を作成してください。config_setup により簡単に生成できます。

## 使い方（起動・停止）

### 1) 設定の初期化・検証
- .env を対話式で作成:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定を自動検証:
  ```bash
  python -m kabusys.validate_config
  ```

### 2) ExecutionEngine（発注エンジン）起動
- デフォルト（設定に従う）で起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite に記録されます（production DB と分離）。
  - 起動時に data/execution.pid へ PID を書きます（設定によりパス変更可）。
  - 停止は監視プロセスが data/kill.flag を書くか、手動でエンジンの停止処理を行ってください。run_execution は data/stop_requested.flag の存在も確認して起動を中断/停止します。

### 3) Monitoring（監視）起動
- 監視ループを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。
- 停止:
  - プロジェクトルートの data/stop_requested.flag を作成すると監視ループは検知して終了します。
  - KillSwitch（条件を満たすと data/kill.flag を書く）による ExecutionEngine 停止も可能。

### 4) Paper Trading 検証レポート
- レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。

## ログ

- ロギングは共通ユーティリティを通じて設定されます（kabusys.utils.logging_setup.setup_logging）。
- デフォルト出力:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- app_name 例: "execution", "monitoring"

## データベース（概観）

- DuckDB（分析用）: prices_daily, raw_financials, raw_news, market_regime, ai_scores などを想定
- SQLite（監視ログ / 発注履歴）:
  - system_status: システム状態監視
  - trade_logs: 発注・約定ログ（latency_ms を含む）
  - positions: 現在ポジション
  - risk_logs: リスクアラートログ
  - dashboard: 集計情報（portfolio_value 等）

init_monitoring_db() によりテーブルは冪等的に作成・マイグレーションされます。

## 安全上の注意

- KABUSYS_ENV=live は本番モードです。LINE トークンや kill flag 設定等を慎重に扱ってください。
- KILL_FLAG_CLEAR_ON_START=1 は本番では危険（自動で kill.flag をクリアしてしまう）ため、production では 0 を推奨します。
- .env を Git に含めないでください（機密情報が含まれるため）。

## 主要なモジュール / ファイル一覧（ディレクトリ構成）

リポジトリの主要な構成（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py         — .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       (コード内参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       (コード内参照)
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（コード内参照）
    - broker_factory.py     — ブローカークライアントの生成
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
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                   — 実行時に使用されるデータディレクトリ（logs, DB, pid, flags 等）

（注）一部ファイルは README に記載していない補助的なモジュールや TODO を含みます。上記は主要な機能単位に整理した一覧です。

## 開発者向けメモ

- 自動的に .env を読み込む仕組みがあり、プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- Logging、プロセス優先度設定などは共通ユーティリティにまとめられています。
- DuckDB を使った分析・研究用コードは外部副作用（発注等）を持たない設計になっています。
- AI 周りの呼び出しはリトライや入力サイズ制限、JSON 検証など、実運用に配慮した実装が施されています。

---

上記で足りない点や、実際の起動方法（systemd/Upstart/cron などの運用方法）、あるいは特定モジュールの詳細ドキュメントが必要であれば教えてください。README を運用ルールやデプロイ手順に合わせてカスタマイズできます。