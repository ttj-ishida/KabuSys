# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（実発注/ペーパートレード切替）、監視・アラート、LLM を使ったニュース NLP／レジーム判定などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 主要機能

- 発注実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し、専用の SQLite DB に記録
  - 発注・注文管理・リスク管理・照合（reconciler）を含む

- 監視（Monitoring）
  - system / trade / risk をポーリングして監視
  - Kill Switch（条件発動で `data/kill.flag` を書き込み ExecutionEngine を停止）
  - 監視ログは SQLite に永続化（monitoring DB）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースの株数決定
  - セクターキャップ、レジーム乗数などのリスク調整ロジック

- AI（OpenAI 統合）
  - ニュースのセンチメントを LLM で評価して ai_scores に保存
  - マクロニュース + ETF MA による市場レジーム判定

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

---

## 前提・依存ライブラリ

主な依存（必須 / 推奨）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML の検証を行いたい場合）

（正式な requirements.txt は本リポジトリに添付されていないため、環境に合わせてインストールしてください）
例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置し、作業ディレクトリをプロジェクトルートにする。

2. Python 仮想環境を作成・有効化して依存をインストール（上記参照）。

3. 対話式で .env を作成:
```bash
python -m kabusys.config_setup
```
ウィザードが .env を生成します（デフォルト: `./.env`）。重要な環境変数例:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH（監視 DB、デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: `data/paper_trading.db`）
- OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証:
```bash
python -m kabusys.validate_config      # 警告は表示のみ
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

5. ログディレクトリ（デフォルト `logs/`）や `data/` ディレクトリは起動時に自動作成されることが多いですが、権限などで作れない場合は事前に作成してください。

---

## 実行方法

すべての起動スクリプトはモジュールとして実行できます（プロジェクトルートで実行してください）。

- 監視ループを起動（Monitoring）
```bash
python -m kabusys.run_monitoring
```
オプション:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
- 監視は Settings に依存する sqlite_path（monitoring DB）を使用します（環境に関わらず本番 sqlite_path を参照する設計）。

停止:
- プロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが検知して終了します（run_monitoring が使用する停止フラグ）。
- ExecutionEngine 停止用には `data/kill.flag` を KillSwitch が書き込みます（条件により自動で発生）。

- 発注エンジンを起動（Execution）
```bash
# 本番（注意: 実際に注文が発行されます）
KABUSYS_ENV=live python -m kabusys.run_execution

# ペーパートレード（MockBroker を使用し DB は data/paper_trading.db）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
ポイント:
- Execution 起動時は `set_process_priority("high")` を呼びプロセス優先度設定を試みます（権限や OS により無視されることがあります）。
- `KABUSYS_ENV=paper_trading` のとき、MockBrokerClient が使われ、発注記録は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ分離されます。本番データベースと混ざりません。
- 起動前に `data/kill.flag` が存在する場合、エンジンを起動せず終了します（安全措置）。`KILL_FLAG_CLEAR_ON_START=1` で起動時に自動クリアする設定もありますが、本番では 0 を推奨。

- Paper Trading 検証レポートを生成
```bash
# デフォルト DB パスまたは環境変数 PAPER_TRADING_SQLITE_PATH を使用
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

---

## 環境変数（主要）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API base URL（デフォルト local）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）

PAPER_FILL_MODE（ペーパートレードの約定挙動）:
- instant / partial / never / reject

PID / Flag ファイル（デフォルトパス）:
- data/execution.pid（Execution の PID）
- data/kill.flag（Kill Switch が書き込む停止フラグ）
- data/stop_requested.flag（監視/実行の外部停止用フラグ）

---

## 使い方（ライブラリ関数の例）

- 研究（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,4,10))
```

- ポートフォリオ構築
```python
from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

candidates = select_candidates(buy_signals, max_positions=10)
weights = calc_score_weights(candidates)
shares = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, ...)
```

- AI（ニューススコアリング）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
```

- レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
```

---

## ログと監視

- ログは `kabusys.utils.logging_setup.setup_logging()` により統一設定されます。
  - コンソール（stdout）出力および日次ローテーションでファイル出力（デフォルト `logs/<app_name>.log`、30日保持）。
  - LOG_DIR 環境変数や引数で変更可能。
  - LOG_LEVEL でログレベルを制御。

- 監視エンジンは `kabusys.monitoring.monitoring_engine.MonitoringEngine` により複数モニタを束ね、アラート送信や kill switch 評価を行います。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に配置されています。主なファイル・フォルダ:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_monitoring.py                — SystemMonitor ポーリングループ
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (※存在する想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※存在する想定)
  - execution/
    - execution_engine.py (※存在する想定)
    - broker_factory.py (※存在する想定)
    - order_manager.py (※存在する想定)
    - order_repository.py (※存在する想定)
    - reconciler.py (※存在する想定)
    - risk_manager.py (※存在する想定)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                             — 実行時生成 / DB / flag ファイル（例: data/monitoring.db, data/paper_trading.db, data/kill.flag）

（注: README は提示されたコードベースの主要ファイルに基づく概要です。実際のリポジトリにはここに記載のない補助モジュールが存在する場合があります）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では `validate_config` の出力をよく確認し、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値に注意してください。
- `KILL_FLAG_CLEAR_ON_START=1` は開発時の利便性を高めますが、本番では自動クリアを無効（0）にすることを推奨します（Kill Switch を確実に有効にするため）。
- OpenAI API を使う処理は API 料金やレート制限に注意してください。失敗時はフェイルセーフで続行する実装ですが、運用ポリシーを検討してください。
- ログや DB の保存先（`LOG_DIR`, `DUCKDB_PATH`, `SQLITE_PATH`）は運用環境（ディスク容量、バックアップ、権限）に応じて適切に設定してください。

---

必要であれば、README に以下を追加できます:
- 開発用に推奨される requirements.txt / poetry 設定例
- CI / デプロイ手順（Systemd ユニットや Dockerfile のサンプル）
- それぞれのコンポーネント（ExecutionEngine / MonitoringEngine / AI）の詳細な図やシーケンス図

要望があれば具体的な追加内容（例: systemd ユニット例や Dockerfile）を作成します。