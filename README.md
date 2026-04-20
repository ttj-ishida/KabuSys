# KabuSys

日本株向け自動売買 / 研究プラットフォームのサブセット実装です。本リポジトリは実行エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などの主要モジュールを含みます。

> 注意: 本 README は提供されたソースコードに基づき作成しています。実行には適切な環境変数や外部依存が必要です。実運用前に必ず設定検証（validate_config）を行ってください。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- ExecutionEngine: 発注・注文管理・リスク制御を行うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文ログ・リスク状況のポーリング監視とアラート / Kill Switch
- Portfolio: 銘柄選定・重み算出・株数決定（純粋関数群）
- Research: DuckDB 上の時系列データからファクター計算・特徴量解析を行う機能
- AI: ニュースを LLM（OpenAI）でスコアリング、マクロニュースを用いた市場レジーム判定
- ユーティリティ: .env ウィザード、設定検証、ログ設定、プロセス優先度制御 など

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を使用）
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可）

- 設定関連
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env および config/*.yaml の事前検証 CLI

- 監視・運用
  - MonitoringEngine（system/trade/risk の統合監視、Kill Switch 判定）
  - Kill Switch（リスク条件により ExecutionEngine 停止フラグを書き込む）
  - monitoring_db: 監視 / ログ永続化（SQLite）

- 研究・分析
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - research.feature_exploration: 将来リターン計算、IC（スピアマン）など

- AI
  - ai.news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書き込み（OpenAI 必須）
  - ai.regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定 / 等分配・スコア加重
  - portfolio.position_sizing: 単元株丸め、利用可能現金に合わせたスケールダウン
  - portfolio.risk_adjustment: セクター上限・レジーム乗数

---

## 必要な依存パッケージ（例）

少なくとも以下が必要になります（バージョンはコードの動作状況に合わせて調整してください）。

- Python 3.9+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- （オプション）PyYAML — validate_config が YAML 内容チェックを行う場合

インストール例（仮の requirements）:
```
pip install duckdb psutil openai pyyaml
```

パッケージ化されている場合はプロジェクトルートで:
```
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化（推奨）
3. 依存パッケージをインストール（上記参照）
4. 環境変数の準備
   - 対話式ウィザードで .env を作成するのが簡単です：

     ```
     python -m kabusys.config_setup
     ```

   - 必須環境変数（最小セット）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - AI 機能を使う場合:
     - OPENAI_API_KEY

   - その他の主要変数（デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO / DEBUG / ...
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）

   - 例（.env の抜粋）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     OPENAI_API_KEY=sk-...
     LOG_LEVEL=INFO
     ```

5. データディレクトリの作成（必要に応じて）
```
mkdir -p data logs
```

---

## 使い方

### 設定の対話式作成
```
python -m kabusys.config_setup
```
ウィザードに沿って .env を作成します。完了後は validate_config で検証してください。

### 設定検証
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

### ExecutionEngine の起動
- 本番・開発・ペーパートレードは KABUSYS_ENV によって切替
- ペーパートレード時は設定に従い MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録されます

```
# 例: ペーパートレードで起動
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- エンジンは `data/execution.pid` に PID を書きます。
- 終了要求は監視側から `kill.flag` を書き込むか、外部で停止フラグを書きます（下記参照）。

### Monitoring の起動
SystemMonitor のポーリングループを起動します。ポーリング間隔はデフォルト 60 秒、環境変数で上書き可。

```
# ポーリング間隔を 30 秒に変更して起動
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 監視は sqlite（監視 DB）へ書き込みます（monitoring は本番 sqlite_path を使用）。
- 停止用フラグ: プロジェクトの data/stop_requested.flag を作成するとループが検出して終了します。

### 強制停止（Kill / Stop）
- Kill Switch: 監視がリスク閾値を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側で検出して安全停止する仕組みです。
- 外部からプロセスを完全に止めたい場合は `data/stop_requested.flag` を作成すると run_monitoring / run_execution が検出して終わります（それぞれが参照するファイルパスはコード内で定義されています）。

### Paper Trading 検証レポート生成
ペーパートレードログ（デフォルト: data/paper_trading.db）から検証レポートを出力します。

```
# 全期間
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB を直接指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### AI / リサーチ機能の利用（ライブラリとして）
Python から直接インポートして利用できます。例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
```

- OpenAI を利用する場合は OPENAI_API_KEY を環境変数に設定するか、api_key 引数を渡してください。
- AI 関連は外部 API 呼び出しであるため、API レート制限やエラーに対してリトライやフォールバック処理が実装されています。

---

## 注意点 / 運用メモ

- Logging: all 起動スクリプトは共通の logging_setup を使用します。ログは `logs/<app_name>.log`（日次ローテート）と stdout に出力されます。
- process_priority: 起動時にプロセス優先度を "high" に設定しようとします（psutil が必要）。権限不足等で失敗する可能性があり、その場合は警告ログを出します。
- DB マイグレーション: monitoring_db.init_monitoring_db は簡単なスキーマ作成とマイグレーション（カラム追加）を行います。既存データに対して冪等で実行できます。
- データ鮮度: SystemMonitor は DuckDB を参照してデータ鮮度チェックを行います（デフォルトで 3 日を許容）。
- ペーパートレードと本番は DB を分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- .env は Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成の抜粋です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py       — CPU/メモリ/プロセス/データ鮮度監視
    - trade_monitor.py        — （省略: trade 監視）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - alert_manager.py        — （省略: アラート送信）
  - execution/
    - execution_engine.py     — ExecutionEngine（起動・セッション管理）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文永続化
    - reconciler.py           — 発注整合処理
    - risk_manager.py         — 実行時リスク制御
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI + ETF）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記のうち一部ファイルは抜粋説明のため省略しています。実際のファイル一覧はリポジトリを参照してください。）

---

## よくある運用コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加したい項目（例: 詳細な設定例、systemd / Supervisor 用のユニット定義、詳細なログの読み方、テスト手順など）があれば知らせてください。必要に応じて追記します。