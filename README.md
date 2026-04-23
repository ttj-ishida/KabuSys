# KabuSys

日本株向け自動売買システム（ライブラリ/実行スクリプト群）

このリポジトリは、シグナル生成、ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視・アラート、研究用ユーティリティ、そして OpenAI を用いたニュース解析 / レジーム判定などを含むモジュール群で構成されています。

---

## 主な機能

- ExecutionEngine（発注実行）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - 発注の管理、リスク制御、リコンサイル処理
- Monitoring（監視）
  - システム・プロセス状態、データ鮮度、トレード状態の定期チェック
  - Kill Switch（条件に応じて ExecutionEngine を停止するフラグ生成）
  - 監視結果の永続化（SQLite）
- Portfolio construction（ポートフォリオ構築）
  - 候補選定、等配分 / スコア配分、リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - forward returns / IC（情報係数） / 統計サマリ
- AI（OpenAI を利用）
  - ニュースのセンチメント解析（news_nlp）
  - 市場レジーム判定（regime_detector）
- ユーティリティ
  - ロギング設定、プロセス優先度設定、設定ウィザード / 検証 CLI
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 前提条件

- Python 3.10 以上（型ヒントに `|` を使用）
- 推奨（主要）依存パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML （config 検証時に YAML を検査する場合に必要）
- SQLite（標準ライブラリに含まれます）

インストール例（仮の requirements を使う場合）:
```
pip install duckdb psutil openai PyYAML
```

実環境では requirements.txt / Poetry 等で依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンして、作業ディレクトリをプロジェクトルートにします。
2. Python 仮想環境を作成して依存をインストールします（上記参照）。
3. 環境変数（.env）を作成します。対話式ウィザードを使うと簡単です：

実行:
```
python -m kabusys.config_setup
```
ウィザードは `.env` を生成します。必須項目（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）は設定してください。

4. 設定を検証します：
```
python -m kabusys.validate_config
# 厳格モード（警告も失敗扱い）
python -m kabusys.validate_config --strict
```

重要な環境変数（主要）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の fill モード: instant|partial|never|reject）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能を使う場合）
- KILL_FLAG_CLEAR_ON_START（起動時に Kill Flag を自動クリアするか。0/1）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

最小 `.env` サンプル（実運用時は必ずシークレット値を設定してください）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方

### 実行（ExecutionEngine）

- 起動スクリプト:
```
python -m kabusys.run_execution
```

動作のポイント:
- KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します。本番 DB と分離されます。
- 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
- 実行中に `data/stop_requested.flag` を作成すると、エンジンが安全に停止します。
- PID ファイル: `data/execution.pid`（Settings.pid_file_path で上書き可）

### 監視（Monitoring）

- 起動スクリプト:
```
python -m kabusys.run_monitoring
```

動作のポイント:
- 監視ループはデフォルト 60 秒ごとにポーリングします。`MONITOR_POLL_INTERVAL` 環境変数で上書き可能。
- 監視は常に本番の sqlite_path を使用して監視データを記録します（環境に関係なく）。
- 停止フラグ: 上位プロジェクトの `data/stop_requested.flag` を監視し、存在時に監視ループを終了します。
- Kill Switch（条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側で検知して停止します）。

### Paper Trading 検証レポート

- SQLite（ペーパートレード用 DB）から検証レポートを生成します:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB ファイルを明示したい場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

出力される主な指標:
- 稼働率（uptime）
- 注文成功率・送信率
- レイテンシ（avg/max/P95）
- リスク却下数（risk_logs）

### AI 機能（プログラム的に利用）

ニューススコアリング / レジーム判定はライブラリ API 経由で使用します（OpenAI API キーが必要）。
例（簡単な使用例）:
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
```
同様に `kabusys.ai.regime_detector.score_regime` を使ってレジーム判定を行えます。

---

## 停止・Kill フラグの運用

- 停止（全体/監視）用フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring のループ停止用（存在で停止）
- Kill Switch（監視が判定して書き込む）:
  - data/kill.flag — KillSwitch が条件に応じて書き込み。ExecutionEngine はこのフラグを検出して停止します。
- 起動時の Kill Flag 自動クリア:
  - 環境変数 `KILL_FLAG_CLEAR_ON_START=1` を有効にすると起動時に kill.flag を自動で削除します（本番では推奨されません）。

---

## ディレクトリ構成 (抜粋)

プロジェクト内の主なファイル・ディレクトリ（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env の自動読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ (発注エンジン関連)
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py ...
  - monitoring/
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_db.py — SQLite テーブル初期化 + 永続化 API
    - alert_manager.py (アラート送信管理)
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
  - tools/
    - paper_verification_report.py

ログ・データ等はデフォルトでプロジェクトルートの `logs/` / `data/` 配下に生成されます（環境変数で上書き可）。

---

## 注意点 / 運用上のヒント

- 本番モード（KABUSYS_ENV=live）では実際に発注が行われます。デプロイ前に必ず validate_config を実行して設定を確認してください。
- ペーパートレード（paper_trading）は本番 DB と分離され、MockBrokerClient を使用します。`PAPER_TRADING_SQLITE_PATH` で DB を指定できます。
- OpenAI API を使う機能は API 利用料金とレート制限に注意してください。news_nlp ではリトライ／バックオフを実装していますが、運用ルールを整えてください。
- ログは `logs/<app_name>.log` に日次ローテーションで保存されます。`LOG_DIR` 環境変数で変更可能です。
- プロセス優先度設定は psutil を利用し、プラットフォーム差異を吸収します。権限不足で設定できない場合は警告が出ます。
- DuckDB は研究・集計向けに利用されます。大量データを扱う場合は適切なファイル配置とバックアップを検討してください。

---

この README はコードベースから抜粋した主要概念と使い方をまとめたものです。各モジュールの詳細な仕様・設計ドキュメント（StrategyModel.md / PortfolioConstruction.md 等）が別途存在する想定です。実装詳細や運用ルールはそれらのドキュメントやコード内の docstring を参照してください。