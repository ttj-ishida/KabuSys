# KabuSys

日本株自動売買システムの一部を含むコードベースの README。  
このドキュメントは、プロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および研究用モジュール群を提供するプロジェクトです。  
主な機能は次の通りです。

- 日次・ポーリングベースのシステム監視（SystemMonitor / MonitoringEngine）
- ExecutionEngine を用いた発注処理（本番 / ペーパートレード対応）
- ポートフォリオ構築（候補選定・重み付け・単元丸め）
- ファクター計算・特徴量解析（DuckDB ベース）
- ニュースの NLP スコアリング / 市場レジーム判定（OpenAI を利用）
- 監視ログ保存（SQLite）と分析用レポート生成ツール

設計方針としては、ロジックの分離（純粋関数群 vs DBアクセス層）、本番とペーパートレードの分離、LLM 呼び出しの堅牢化（リトライ、検証）などを重視しています。

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動ロード（プロジェクトルート検出）、設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 実行/監視
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV によるペーパートレード分離）
  - run_monitoring.py: SystemMonitor のポーリング起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 監視関連
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブル
  - MonitoringEngine: 各モニタを束ねてポーリングし、KillSwitch・Alert に連携
  - RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch 実装
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - ポジションサイジング（リスクベース等）
  - セクター制約・レジーム乗数
- 研究用
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）統合
  - news_nlp: ニュース記事を LLM でセンチメント化して ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを用いた日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポート生成

---

## 要件（例）

必須パッケージ（抜粋、バージョンは適宜選定してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証のため、任意）
- （標準ライブラリ: sqlite3, logging, threading など）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

プロジェクトに requirements.txt がある場合はそちらを使ってください。

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境作成・パッケージインストール（上記参照）
3. .env の作成（おすすめ: 対話式ウィザードを使用）

対話式で .env を作成する:

```bash
python -m kabusys.config_setup
```

ウィザードは `.env`（プロジェクトルート）を作成または更新します。`.env` は絶対にコミットしないでください。

4. 設定検証

```bash
# 警告は許容する場合
python -m kabusys.validate_config

# 警告もエラー扱いにする（CI 等）
python -m kabusys.validate_config --strict
```

5. データディレクトリ等の作成（必要に応じて）

デフォルトでは次のパスが使用されます（Settings クラス参照）:

- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- PID / Flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
- ログディレクトリ: logs/

これらは .env 内で上書きできます。

---

## 環境変数（主要）

必須:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨・主要:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使い paper_trading.db に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/...
- LOG_DIR: ログ保存ディレクトリ
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: ペーパートレードの約定ルール（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

注意:
- .env の自動ロードはプロジェクトルート検出（.git または pyproject.toml）に依存します。
- テストや CI で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（起動 / コマンド）

一般的な起動例を示します。いずれもプロジェクトルートで実行することを想定しています。

- ExecutionEngine を起動（本番 / ペーパートレード共通エントリ）:

```bash
python -m kabusys.run_execution
```

- SystemMonitor を定期実行（ポーリング）:

```bash
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で上書き（秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

run_monitoring の挙動:
- 常に Settings.sqlite_path（監視 DB）を使用（KABUSYS_ENV に依存せず本番 DB を参照する設計）。
- 停止フラグファイル `data/stop_requested.flag` が存在するとループを抜けて終了します。

run_execution の挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録します。本番 DB と分離されます。
- 起動時に停止フラグ `data/stop_requested.flag` が存在すると起動せず終了します。
- 実行中に停止フラグが作成されると ExecutionEngine に停止シグナルを送ります。
- PID ファイルは `data/execution.pid`（デフォルト）に書き込まれます。

- 設定ウィザード（.env 作成）:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- Paper Trading 検証レポート生成:

```bash
python -m kabusys.tools.paper_verification_report
# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

---

## ロギング

- ログ設定は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で行われます。  
- デフォルトはコンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）です。
- ログレベルは環境変数 `LOG_LEVEL` または引数で制御できます。
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで動作します。

---

## Kill Switch / 停止制御

- Kill Switch: `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch は RiskMonitor 等の結果に基づいて条件を評価し、必要に応じて kill.flag を作成します。
- stop_requested.flag: `data/stop_requested.flag` は run_monitoring / run_execution のループを抜けさせるための外部停止要求フラグです（手動で作成/削除可能）。
- Execution 起動時に kill.flag をクリアするオプションとして `KILL_FLAG_CLEAR_ON_START`（環境変数、0/1）があります。※本番では 0 を推奨します。

---

## ディレクトリ構成（主なファイル・モジュール）

以下は `src/kabusys` をルートとした主要ファイル・ディレクトリの概要です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（monitoring 用テーブル）
    - monitoring_engine.py   — 各モニタを束ねる Poller
    - system_monitor.py      — システム・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - (trade_monitor.py 等)
  - execution/                — 発注関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF）
  - tools/
    - paper_verification_report.py

注: 上記は主要モジュールの抜粋です。実際のディレクトリにはさらに補助モジュール・実装ファイルがあります。

---

## 開発・運用上の注意

- .env は機密情報を含むため、決して VCS にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- KABUSYS_ENV が `live` に設定されている場合は設定検証で警告が出ます。本番での誤設定に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。1 秒未満や 0 は無効でデフォルトにフォールバックします。
- AI 関連機能を利用する場合は `OPENAI_API_KEY` を設定してください。API 呼び出しはリトライやフォールバックを備えていますが、API 利用コストやレート制限に注意してください。
- SQLite / DuckDB のパスは Settings で制御できます。運用環境でのバックアップやディスク容量監視を怠らないでください。
- `psutil` を使ってプロセス優先度を変更します。権限不足で警告が出る場合がありますが、安全にフォールバックします。

---

## 参考コマンドまとめ

- 仮想環境作成 / 依存インストール:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

- .env ウィザード:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- 実行:

```bash
python -m kabusys.run_execution
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- レポート:

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

---

もし README に追加してほしい内容（例: デプロイ手順、Dockerfile 例、CI 設定、具体的な設定例やサンプル .env、各モジュールの API ドキュメントなど）があれば教えてください。必要に応じて追記して詳細化します。