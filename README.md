# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README（日本語）

概要、主要機能、セットアップと実行手順、ディレクトリ構成を記載しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。  
主要な関心事を分離したモジュール設計により、以下を提供します。

- 発注エンジン（ExecutionEngine）とブローカ抽象（本番 / ペーパートレード切替）
- システム監視（Monitoring）：リスク監視、プロセス生存確認、アラート連携等
- ポートフォリオ構築（候補選定・重み計算・単元丸めなど）
- リサーチ（ファクター計算、将来リターン・IC 計算、特徴量解析）
- AI 補助モジュール（ニュースのセンチメントスコアリング、レジーム判定）
- 開発用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計ポリシーの一例：DB 書き込みは明示的に行い、ルックアヘッドバイアスを避けるために現在時刻を直接参照しない実装が採られています。

---

## 主な機能一覧

- 実行（Execution）
  - run_execution: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBroker を利用し DB を分離。
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）等を統合。

- 監視（Monitoring）
  - run_monitoring: SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス生存）などを周期的にチェック。
  - Kill Switch: 異常条件で `data/kill.flag` を書き込んで Execution を停止可能。
  - MonitoringDB: system_status / trade_logs / risk_logs / positions / dashboard の永続化。

- ポートフォリオ構築
  - 候補選定（スコア降順）、等金額・スコア重み配分、セクターキャップ適用、ポジションサイズ算出（単元株丸め含む）。

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Spearman）やファクター統計サマリ

- AI（LLM）連携
  - ニュース NLP（news_nlp.score_news）: OpenAI を用いて銘柄ごとにセンチメントスコアを生成して ai_scores に保存
  - レジーム判定（regime_detector.score_regime）: ETF の MA とマクロニュースを統合して 'bull'/'neutral'/'bear' 判定

- 開発ツール
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート（tools/paper_verification_report）

---

## 前提（Requirements）

- Python 3.10+
- 必須ライブラリ（pip インストール）
  - duckdb
  - psutil
  - openai
- 推奨／オプション
  - PyYAML（config/*.yaml の構文チェック用）
- ローカル開発では仮想環境（venv / poetry 等）を推奨

例（pip でのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # requirements.txt を用意している場合
# または最小: pip install duckdb psutil openai
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を有効化する。

2. 環境変数（.env）の作成。対話式ウィザードを推奨：
```bash
python -m kabusys.config_setup
```
ウィザード実行後、`.env` が生成されます。生成後は設定検証を実行してください。

3. 設定検証
```bash
python -m kabusys.validate_config
# 警告も FAIL とする場合:
python -m kabusys.validate_config --strict
```

4. データディレクトリ作成（必要に応じて）
デフォルトで以下パスを使用します（いずれも .env で上書き可能）:
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db

monitoring / execution の起動時に自動で親ディレクトリを作成する処理が入っていますが、手動で用意しておくと権限トラブルを回避できます。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live

- データベース
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、default: data/paper_trading.db)

- ログ / 動作
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (ログファイル置き場、default: logs/)
  - PID_FILE_PATH (ExecutionEngine の PID ファイル、default: data/execution.pid)
  - KILL_FLAG_PATH (kill.flag のパス、default: data/kill.flag)

- AI
  - OPENAI_API_KEY

- 監視ループ
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject

自動 .env ロードは既定で有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 起動 / 使い方

- 監視を起動（デフォルト 60 秒間隔。MONITOR_POLL_INTERVAL で上書き可能）
```bash
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
注意: Monitoring は KABUSYS_ENV に関係なく本番の `SQLITE_PATH` を使用して監視データを記録します。

- 実行エンジンを起動
```bash
# 本番想定（KABUSYS_ENV=live）
KABUSYS_ENV=live python -m kabusys.run_execution

# ペーパートレード
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
# paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録され、本番 DB と分離されます
```

- 停止 / フラグ制御
  - 実行中プロセスを外部から止めたい場合はプロジェクトの data ディレクトリに `stop_requested.flag` を作成すると、run_monitoring/run_execution のループが検知して終了します（スクリプト内の `_STOP_FLAG` を参照）。
  - Kill Switch（自動停止条件）発動時は `data/kill.flag` が書き込まれ、ExecutionEngine 起動時に検出することで発注停止や起動ブロックを行います。

- Paper Trading 検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db PATH を使って別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可
```

- .env ウィザード（設定作成）
```bash
python -m kabusys.config_setup
```

- 設定検証
```bash
python -m kabusys.validate_config
```

---

## ライブラリ / プログラム的利用（例）

- news_nlp の呼び出し（DuckDB 接続を与えて使用）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
```

- リサーチ関数利用
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
# DuckDB 接続を渡して、target_date に対するファクターを取得
```

- ポートフォリオ関数（純粋関数なのでユニットテストが容易）
```python
from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
```

---

## ログ設定

全起動スクリプトは共通のログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用します。  
- コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`
- 保持期間は 30 日（デフォルト）

---

## ディレクトリ構成（抜粋）

（src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py         — （trade 監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （アラート送信の管理）
  - execution/
    - execution_engine.py      — ExecutionEngine コア
    - broker_factory.py
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
    - news_nlp.py
    - regime_detector.py

（上記以外にも data/、logs/、config/*.yaml などをプロジェクトルートに置く想定です）

---

## 注意事項 / トラブルシューティング

- Monitoring はデフォルトで本番の `SQLITE_PATH` を使用します。テスト目的で別の DB を使いたい場合は環境変数でパスを変更してください。
- `KABUSYS_ENV=paper_trading` は paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使って本番 DB とデータを分離します。ペーパートレード用 DB のパスを必ず確認してください。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。利用制限・コストに注意してください。API 呼び出しはリトライ・フェイルセーフを持ちますが、失敗時は 0.0 等のフォールバック挙動になります。
- ログディレクトリ作成に失敗するとファイルロギングは無効化され、コンソールログのみになります。パーミッション等を確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番環境では危険（自動クリアされるため）。validate_config が警告します。

---

## ライセンス / バージョン

パッケージ version は `kabusys.__version__` で管理（現状 "0.1.0"）。

ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（本リポジトリに LICENSE を含めることを推奨します）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。詳細な各モジュールの設計、パラメータチューニング方針、運用手順はプロジェクト内のドキュメント（例えば PortfolioConstruction.md、StrategyModel.md 等）を参照してください。必要に応じて README を拡張しますので、追加で盛り込みたい項目があれば教えてください。