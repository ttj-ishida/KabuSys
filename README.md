# KabuSys

日本株自動売買システムの一部（ライブラリ + 起動スクリプト群）。  
このリポジトリは、注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニュース評価などのモジュール群を含みます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・コマンド例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数・設定のポイント

---

## プロジェクト概要

KabuSys は日本株の自動売買システム用ライブラリ群と起動スクリプト群です。  
主な目的は以下です。

- 市場・銘柄のリサーチ（ファクター計算・特徴量解析）
- ポートフォリオ構築（銘柄選定、重み付け、株数決定）
- ExecutionEngine による発注（本番 / ペーパートレードを切り替え可能）
- 監視モジュールによるシステム安定性・注文状態の監視、Kill Switch 発動
- ニュースを LLM（OpenAI）で評価して AI スコアを計算する機能
- ペーパートレードの検証レポート生成ツール

---

## 主な機能一覧

- config: 環境変数の読み込み（.env / .env.local 自動ロード）、Settings クラス
- config_setup: 対話式ウィザードで .env を生成・更新
- validate_config: .env や config/*.yaml を事前検証する CLI
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じてペーパー/本番切替）
  - ペーパートレード時は MockBrokerClient を使用し、別 DB に記録（data/paper_trading.db）
- run_monitoring.py: SystemMonitor のポーリングループ起動（監視用プロセス）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60s）
  - 監視は常に production の sqlite_path を使用
- monitoring:
  - monitoring_db: SQLite テーブル作成・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine: 監視ロジック
- portfolio:
  - 銘柄選定、重み付け、ポジションサイズ計算、セクター上限、レジーム乗数
- research:
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索、IC 計算など（DuckDB 使用）
- ai:
  - news_nlp: raw_news を集約して OpenAI へ投げ、銘柄ごとにセンチメントスコアを ai_scores に書き込む
  - regime_detector: ETF とマクロ記事を組み合わせて市場レジーム判定を行う
- tools:
  - paper_verification_report: ペーパートレード記録を集計して検証レポートを生成

---

## セットアップ手順

前提: Python 3.9+（型アノテーションの表記から 3.9+ を想定）。必要なパッケージは以下の通り（プロジェクトによっては追加依存がある場合があります）。

必須（主なもの）:
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証をしたい場合）
- その他（標準ライブラリ: sqlite3, pathlib, logging 等）

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install duckdb psutil openai pyyaml
```

.env の初期作成（対話式ウィザード）:

```bash
python -m kabusys.config_setup
```

作成後、設定を検証:

```bash
python -m kabusys.validate_config
# --strict を付けると警告も失敗扱いになります
python -m kabusys.validate_config --strict
```

ログディレクトリはデフォルトで `logs/`。書き込み権限を用意してください。

データディレクトリ（デフォルト）:
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- Paper trading SQLite: data/paper_trading.db

必要に応じて .env で上書きできます。

---

## 使い方

基本的にモジュールは library として利用できますが、いくつかの CLI / 起動スクリプトが用意されています。

1. .env 作成（対話式ウィザード）

```bash
python -m kabusys.config_setup
```

2. 設定検証

```bash
python -m kabusys.validate_config
```

3. ExecutionEngine（注文エンジン）の起動

- 本番・ペーパートレードは KABUSYS_ENV 環境変数で切替:
  - development / paper_trading / live
- ペーパートレード時は設定により MockBrokerClient を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。

起動:

```bash
python -m kabusys.run_execution
```

停止:
- `data/stop_requested.flag` ファイルや `data/kill.flag`（KillSwitch）など、フラグファイルで停止を制御します。
- ExecutionEngine は起動時に `data/execution.pid`（デフォルト）に PID を書きます。

4. Monitoring（監視プロセス）の起動

- ポーリング間隔は環境変数で変更可能:

```bash
export MONITOR_POLL_INTERVAL=30  # 秒
python -m kabusys.run_monitoring
```

- 監視は production の sqlite_path を使います（KABUSYS_ENV に依らず監視 DB は sqlite_path）。

5. Paper Trading 検証レポート生成

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

6. AI 関連機能（ライブラリ関数として使用）

- ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（kabusys.duckdb）と OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

これらは CLI が組み込まれていないためスクリプトや cron から Python 呼び出しで利用します。例:

```python
import duckdb, datetime
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, datetime.date(2026, 4, 1), api_key="sk-...")
print("written:", n_written)
```

---

## 主要な設定・環境変数

必須（少なくとも設定・準備が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な環境変数（デフォルト値を併記）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API 用キー（ai モジュールを使う場合）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動消去（本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルトは data/execution.pid / data/kill.flag（Settings を参照）

注意:
- run_monitoring は監視用 DB（sqlite_path）を環境にかかわらず使用します（監視ログは production DB に残す想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用します（発注記録を本番 DB と分離）。
- Kill Switch（kill.flag）は RiskMonitor 等から評価され、条件を満たすと書き込まれます。ExecutionEngine は kill.flag を監視して停止します。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールと役割です（抜粋）。

- kabusys/
  - __init__.py: パッケージ定義（__version__ 等）
  - config.py: 環境変数の自動読み込み、Settings クラス（設定参照用）
  - config_setup.py: .env を対話的に作るウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: 一貫したログ設定（stdout + 日次ローテートファイル）
    - process_priority.py: プロセス優先度 / CPU affinity を OS 間で吸収して設定
  - monitoring/
    - monitoring_db.py: SQLite のテーブル定義・CRUD（初期化・マイグレーション含む）
    - system_monitor.py: CPU/メモリ/ディスク/プロセス存在やデータ鮮度の監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - trade_monitor.py: （注文関連監視。実装参照）
    - kill_switch.py: フラグファイルによる停止制御
    - monitoring_engine.py: 複数モニタの統合ポーリングループ
    - alert_manager.py:（アラート送信管理。実装参照）
  - execution/: ExecutionEngine や OrderManager / RiskManager / Reconciler 等（起動時に参照）
  - portfolio/
    - portfolio_builder.py: 候補選定、等分・スコア加重の重み計算
    - position_sizing.py: 株数決定、単元丸め、aggregate cap スケーリング
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py: raw_news を LLM で評価して ai_scores に格納する処理
    - regime_detector.py: ETF とマクロ記事で市場レジームを判定、market_regime テーブルへ格納
  - tools/
    - paper_verification_report.py: ペーパートレード DB を集計して検証結果を出力

（※ 一部ファイルはここに抜粋しているもののみで、実際の機能はさらに多くのサブモジュールで構成されます）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の管理に注意し、JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD を漏洩しないこと。
- KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨。誤って自動クリアされると Kill Switch による停止が無効化される可能性があります。
- ログはデフォルトで logs/ に出力されます。ログローテーションは日次（30日保持）。
- ペーパートレード用 DB は本番 DB と分離しています（PAPER_TRADING_SQLITE_PATH）。検証時は間違って本番 DB を上書きしないよう注意してください。
- AI（OpenAI）を使う機能は API キーと API 利用制限（レート・コスト）に注意して運用してください。news_nlp や regime_detector はリトライ・フェイルセーフを備えていますが、コストは発生します。
- monitoring の init では簡易マイグレーション（カラム追加）を行います。既存 DB と互換性が保たれていますが、本番運用前にバックアップを推奨します。

---

README は以上です。詳細な API や ExecutionEngine / OrderManager 等の実装を確認する場合は該当モジュールの docstring やコードコメントを参照してください。必要であれば README にコマンド例や .env のサンプル（秘密情報はマスク）を追加で挿入します。どの情報がさらに必要か教えてください。