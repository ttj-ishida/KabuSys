# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ・起動スクリプト・ツール群）

この README はリポジトリ内の主要スクリプトとモジュールに基づいて作成した利用ガイドです。プロジェクト全体の概観、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究基盤です。主な役割は以下の通りです。

- 実際の発注（ExecutionEngine）またはペーパートレード（MockBrokerClient）による戦略の実行
- システム状態・注文・リスクの監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 研究用ファクター計算・特徴量解析（DuckDBを利用）
- ニュースの NLP によるセンチメント評価（OpenAI を利用可能）
- 設定ウィザード・検証ツール・ペーパートレード検証レポート生成ツール

設計上の特徴：
- 設定は .env / 環境変数に依存（config_setup.py で対話的に作成可）
- Monitoring や Execution の DB は sqlite/duckdb を使用（パスは環境変数で指定可能）
- OpenAI 連携はオプション（APIキーは環境変数で設定）

---

## 機能一覧

主な機能（抜粋）：

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（本番 / ペーパートレード切替対応）
  - run_monitoring.py: SystemMonitor（監視ループ）起動（ポーリング）
- 設定管理
  - config_setup.py: .env の対話式ウィザード（初期設定）
  - validate_config.py: .env と config/*.yaml の事前検証ツール
- 監視
  - monitoring_engine.py: 各種 Monitor（System / Trade / Risk）を束ねる
  - monitoring_db.py: 監視ログ用 SQLite スキーマ & 永続化 API
  - kill_switch.py: 条件満足時に kill.flag を書く（Execution 停止トリガ）
- ポートフォリオ構築（純粋関数）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- 研究用
  - research.factor_research: モメンタム / ボラティリティ / バリュー等の計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC（スピアマン）など
- AI（OpenAI）
  - ai.news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores に書込
  - ai.regime_detector: 市場レジーム判定（MA200 + マクロセンチメント）
- ツール
  - tools.paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## 必要条件 / 依存

推奨 Python バージョン: 3.10+

主要依存ライブラリ（機能により不要なものあり）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML (validate_config の YAML 検証を行う場合)
- その他、ロギング等は標準ライブラリで動作

インストール例（仮）:
```bash
pip install duckdb psutil openai PyYAML
```
※ 実際はプロジェクトに requirements.txt がある場合はそちらを使ってください。

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 仮想環境を作成して依存をインストール
3. 初期環境変数（.env）の作成（推奨: 対話式ウィザードを使う）

対話式で .env を作成する:
```bash
python -m kabusys.config_setup
```
ウィザードは次のような主要項目を設定します（デフォルト値は括弧内）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)

4. 設定の検証（.env と config/*.yaml のチェック）
```bash
python -m kabusys.validate_config
# 警告をエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリの作成（必要に応じて）
- ログディレクトリ: `logs/`（デフォルト） — setup_logging が自動作成を試みます
- DB ディレクトリ: `data/`（SQLite/DuckDB のデフォルトパスは `data/*`）

注意:
- 初回起動時、監視 DB（monitoring.db）は init_monitoring_db により自動生成されます。
- `KABUSYS_ENV=paper_trading` の場合、Execution は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用します（本番 DB と分離）。

---

## 使い方

基本的な実行方法（各モジュールはパッケージモードで起動します）:

- ExecutionEngine を起動（本番／ペーパーは KABUSYS_ENV に依存）:
```bash
python -m kabusys.run_execution
```
- System Monitor を起動（システム状態・データ鮮度のポーリング）:
```bash
python -m kabusys.run_monitoring
```

- 設定ウィザード（.env 作成）:
```bash
python -m kabusys.config_setup
```

- 設定検証:
```bash
python -m kabusys.validate_config
```

- ペーパートレード検証レポート出力:
```bash
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
```
（`--db` を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を使用）

重要な環境変数（抜粋）とデフォルト:
- KABUSYS_ENV: execution モード ("development", "paper_trading", "live") — デフォルト "development"
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

監視・停止フロー:
- run_monitoring と run_execution はそれぞれ `data/stop_requested.flag` の存在を監視してループを終了（stop フラグで安全に停止）
  - `run_monitoring` は _STOP_FLAG = ../data/stop_requested.flag をチェック
  - `run_execution` も同様に起動中に STOP フラグを見て停止
- KillSwitch（監視 -> 実行停止トリガ）は `data/kill.flag` を書き込み、Execution 側での追加停止トリガとして機能
  - `KILL_FLAG_CLEAR_ON_START=1` を使うと起動時に kill.flag を自動でクリア（本番は注意: デフォルトは 0）

ログ:
- ログはコンソール出力 (stdout) とファイル出力（logs/<app_name>.log）に出力されます（デイリーローテーション、30日保持）。
- ログディレクトリは環境変数 `LOG_DIR` またはデフォルト `logs/` を使用。

プロセス優先度:
- 起動スクリプトは start 時に set_process_priority("high") を呼びます（psutil を使用）。権限やプラットフォームによっては設定に失敗する場合があります（警告で続行）。

AI 関連:
- `kabusys.ai.news_nlp.score_news`：DuckDB の raw_news / news_symbols を参照し OpenAI API に問い合わせて ai_scores に書き込む
  - OpenAI API キーは `OPENAI_API_KEY` または関数引数で渡す
  - エラー耐性（リトライ・部分成功保護）を備えています
- `kabusys.ai.regime_detector.score_regime`：ETF 1321 の MA200 とマクロセンチメントを合成して market_regime に書き込む

---

## 開発者向けメモ / トラブルシュート

- ログ出力に失敗する場合は `LOG_DIR` の書き込み権限を確認してください。ログディレクトリの作成に失敗するとコンソール出力のみになります。
- psutil の一部 API はプラットフォーム依存です。Windows/Linux/macOS の差分は process_priority モジュールで吸収していますが、権限不足で AccessDenied 例外が出る場合は警告で処理が続行されます。
- DuckDB / SQLite のパスが存在しない親ディレクトリでも起動時に自動作成されるケースがありますが、事前に data/ を作成しておくと安心です。
- validate_config は PyYAML が無い場合でも動作しますが、config/*.yaml のパース検証はスキップされます（警告が出ます）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュール構成（src/kabusys ベース）です。実際の追加モジュールやファイルはリポジトリによって異なる場合があります。

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                 # 環境変数 / .env 自動ロード・Settings
   ├─ config_setup.py           # .env 対話式ウィザード
   ├─ validate_config.py        # 設定検証 CLI
   ├─ run_execution.py          # ExecutionEngine 起動スクリプト
   ├─ run_monitoring.py         # SystemMonitor 起動スクリプト
   ├─ tools/
   │  └─ paper_verification_report.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ monitoring/
   │  ├─ monitoring_db.py
   │  ├─ monitoring_engine.py
   │  ├─ system_monitor.py
   │  ├─ trade_monitor.py        # （存在参照あり）
   │  ├─ risk_monitor.py
   │  ├─ kill_switch.py
   │  └─ alert_manager.py        # （存在参照あり）
   ├─ portfolio/
   │  ├─ __init__.py
   │  ├─ portfolio_builder.py
   │  ├─ position_sizing.py
   │  └─ risk_adjustment.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ utils/
   │  ├─ __init__.py
   │  ├─ logging_setup.py
   │  └─ process_priority.py
   └─ ... (execution/, data/, strategy/ など他モジュール)
```

各モジュールは概ね「純粋関数」か「I/O 層（DB の読み書き）」に分かれており、ユニットテストやモック差替えがしやすい設計になっています。

---

## 付録：よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい具体的な情報（例: requirements.txt の内容、実運用時の systemd / Supervisor 用起動例、各種 config/*.yaml のサンプル等）があれば教えてください。必要に応じて追記します。