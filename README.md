# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・リサーチ・AI 補助機能を含むモジュール群を提供します。  
設計方針は「本番と調査機能の分離」「フェイルセーフ」「ルックアヘッドバイアス防止」です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 使い方（起動スクリプト・ツール）
- 環境変数 / .env の扱い
- ログ・データファイル・停止フラグ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援する Python パッケージです。以下の領域をカバーします。

- データ取得 / DuckDB を使った時系列データ分析（research）
- ファクター計算、特徴量探索
- ポートフォリオ構築（候補選定・重みづけ・ポジションサイジング）
- 発注実行エンジン（実ブローカ／モックブローカの切替）
- リスク監視・監視エンジン（Kill Switch を含む）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、レポート等）

設計上、発注処理と分析処理は分離され、Paper Trading（ペーパートレード）モードは本番 DB と分離されるようになっています。

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補フィルタ（スコア降順 / 上位N）
  - 重み計算（等金額・スコア加重）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（bull/neutral/bear に応じた資金乗数）
  - ポジションサイズ計算（risk_based / equal / score）
- 発注実行
  - ExecutionEngine（Execution 起動スクリプト）
  - BrokerClientFactory により実ブローカ or MockBroker を切替（KABUSYS_ENV=paper_trading）
  - Paper trading 用 DB 分離（デフォルト: data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス存続を監視して SQLite に記録
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウン監視
  - KillSwitch：重大リスクで data/kill.flag を書いて ExecutionEngine を停止
  - MonitoringEngine：一括ポーリング・アラート発行
- AI 機能
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF(1321) の MA200 乖離 + マクロ記事センチメントを合成して日次レジーム判定
- ユーティリティ
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

---

## 必要条件

- Python 3.10+
- 必要 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の内容検証時）
- SQLite（Python 標準 sqlite3 を使用）
- ネットワーク（API を利用する機能を使う場合）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# 任意で PyYAML を使う場合:
pip install PyYAML
```

プロジェクトに requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env ファイルを作成）

.env は手動で作るか、対話ウィザードを使用できます。

.env ウィザード:
```bash
python -m kabusys.config_setup
```
ウィザード終了後、作成された `.env` を確認し、必要なシークレット（J-Quants トークン、kabu API パスワード、OpenAI API キー等）を設定してください。

設定検証:
```bash
python -m kabusys.validate_config
# 警告を厳格エラー扱いにしたい場合:
python -m kabusys.validate_config --strict
```

自動 .env 読み込み: パッケージは起動時にプロジェクトルートの `.env` と `.env.local` を自動でロードします（OS環境変数 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方

主要な起動/ツールコマンド例。パッケージモードで実行します。

- 監視ループ起動（SystemMonitor をポーリング）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を上書き:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 実行エンジン起動（ExecutionEngine）
```bash
python -m kabusys.run_execution
```
  - KABUSYS_ENV=paper_trading のとき、MockBroker を使い paper_trading.db に記録（本番 DB と分離）
  - 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag や data/kill.flag を使う実装

- .env の対話的作成・更新
```bash
python -m kabusys.config_setup
```

- 設定検証
```bash
python -m kabusys.validate_config
```

- Paper Trading 検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report
# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを直接指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 機能（プログラムから呼ぶ）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- OpenAI を使う機能は環境変数 `OPENAI_API_KEY` を設定するか、関数に api_key を渡してください。
- `run_monitoring` は MONITOR_POLL_INTERVAL（秒）でポーリング可能（環境変数で上書き）。デフォルト 60 秒。
- `run_execution` は KABUSYS_ENV が `paper_trading` の場合、paper_trading 用 SQLite を使用します。

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs）
- OPENAI_API_KEY（AI 機能用）
- PAPER_FILL_MODE（instant | partial | never | reject）ペーパートレードの約定挙動
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番起動時の kill.flag 自動クリア: 0/1）

完全な取得ロジックやバリデーションは `kabusys.config.Settings` を参照してください。

---

## ログ・データファイル・停止フラグ

- ログ: デフォルト `logs/<app_name>.log`（TimedRotatingFileHandler、日次ローテ）
- SQLite（監視ログ）: デフォルト `data/monitoring.db`
- DuckDB（分析）: デフォルト `data/kabusys.duckdb`
- Paper Trading DB: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
- PID / フラグ:
  - `data/execution.pid`（ExecutionEngine の PID）
  - `data/stop_requested.flag`（run_monitoring/run_execution が監視する「停止要求」フラグ）
  - `data/kill.flag`（KillSwitch により書き込まれる停止フラグ）
- 注意: Kill Switch はリスクトリガー（ドローダウンなど）で `data/kill.flag` を書き、Execution 側で停止させる仕組みです。`KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に自動クリアされますが、本番では `0` 推奨。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python パッケージ構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン/ポジション上限監視
    - trade_monitor.py       — （発注監視）※実装参照
    - monitoring_engine.py   — 各 Monitor を束ねる
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （アラート送信）※実装参照
  - execution/
    - execution_engine.py    — 実行エンジン本体（EngineConfig / run_session 等）
    - broker_factory.py      — BrokerClient の生成（実・モック切替）
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
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py

（上は主要ファイルの抜粋です。詳しくは src/kabusys 以下を参照してください）

---

## トラブルシューティング / 注意点

- Python バージョン: 3.10 以上が必要です（`X | Y` 型ヒント等を使用）。
- .env 自動ロード: `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロードします。テスト時等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API: レート制限やネットワークエラーが起きうるため、API 呼び出しにはリトライとフォールバック（失敗時はスキップまたは中立値使用）が組み込まれています。API キーは `OPENAI_API_KEY` を設定してください。
- データ鮮度: SystemMonitor は prices_daily の最新日付を参照してデータ鮮度を判定します。DuckDB の prices_daily テーブルが更新されていることを確認してください。
- DB マイグレーション: `init_monitoring_db` は既存 DB に対する簡易マイグレーション（カラム追加）を行うことがあります。万が一のため DB のバックアップを推奨します。
- 本番稼働時: `KABUSYS_ENV=live` を設定すると注意喚起の検査が追加されます。LINE 等のアラート設定が未設定だとアラートが届きません。Kill Switch の自動クリア (`KILL_FLAG_CLEAR_ON_START`) は本番では `0` を推奨します。

---

README はここまでです。より詳細な仕様や各モジュールの使い方は該当モジュールの docstring を参照してください（例: kabusys/research/factor_research.py、kabusys/ai/news_nlp.py）。必要であれば各コンポーネントの詳細ドキュメント（API サーフェス、設定例、実行フロー）を別途作成します。