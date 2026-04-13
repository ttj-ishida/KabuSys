# KabuSys

日本株向け自動売買システムのモジュール群です。本リポジトリはトレード実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース解析など、プロダクション運用を想定したコンポーネント群から構成されています。

以下はコードベースに基づく README（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買向けに設計されたモジュール式システムです。主な責務は以下のとおりです。

- 実行エンジン（ExecutionEngine）による注文生成・発注（実ブローカー or モック）
- 監視（MonitoringEngine）によるプロセス／注文／リスクの定期チェックとアラート送信（LINE）
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、リスク調整、株数決定）
- リサーチ（ファクター計算、特徴量探索、IC 等）
- AI モジュール（ニュースの NLP スコアリング、マーケットレジーム判定）
- 検証ツール（Paper Trading の検証レポート生成）
- Streamlit ベースの監視ダッシュボード

設計方針として、可能な限り純粋関数（副作用を持たない）を採用し、DB は DuckDB / SQLite を利用してローカル永続化します。Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と完全分離されるようになっています。

---

## 機能一覧

- 実行（run_execution.py）
  - 本番／Paper Trading 切り替え（環境変数 `KABUSYS_ENV`）
  - Broker クライアントの抽象化（BrokerClientFactory）
  - RiskManager、OrderManager、Reconciler による運用管理
- 監視（run_monitoring.py / monitoring モジュール）
  - SystemMonitor：CPU・メモリ・ディスク、Execution プロセス、データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン、ポジション上限の監視（kill.flag の発行）
  - AlertManager：LINE へのプッシュ通知（クールダウンあり）
  - Streamlit ダッシュボード（監視状況の可視化）
- AI（ai モジュール）
  - news_nlp: OpenAI を用いたニュース記事のセンチメント集約・ai_scores への書込み
  - regime_detector: MA200 とマクロニュースセンチメントの合成で市場レジーム判定
- ポートフォリオ（portfolio モジュール）
  - 候補選定、等配分・スコア配分、セクター上限適用、レジーム乗数、株数計算（単元丸め、aggregate cap）
- リサーチ（research モジュール）
  - calc_momentum / calc_volatility / calc_value などのファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、統計サマリー
- ツール
  - paper_verification_report: Paper Trading DB を集計し PASS/FAIL で簡易検証レポート出力
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 操作
  - config: .env 自動読み込み、Settings クラスによる環境変数管理
  - monitoring_db: 監視用 SQLite スキーマと読み書き API

---

## 必要条件（例）

- Python 3.10+
- 以下の主要パッケージ（一部機能で必要）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準で Python に同梱）

requirements.txt があれば pip install -r requirements.txt を推奨します。なければ手動でインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. 仮想環境を作成して依存をインストールします（上記参照）。

3. 環境変数設定
   - ルートに `.env` / `.env.local` を配置すると、`kabusys.config` がプロジェクトルート（.git または pyproject.toml を検知）から自動読み込みします（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY（AI 機能利用時）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - PID_FILE_PATH（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - MONITOR_POLL_INTERVAL（run_monitoring 起動時のポーリング間隔秒。デフォルト: 60）

5. データディレクトリ
   - デフォルトの DB や PID ファイルは `data/` に置かれます。必要に応じてディレクトリを作成してください。

---

## 簡単な .env 例

ルートに `.env` を作ると便利です（機密情報は管理に注意）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
```

---

## 使い方（実行方法）

- 監視ループを起動する（監視は MONITOR_POLL_INTERVAL で間隔を指定可能）:

```bash
python -m kabusys.run_monitoring
# または MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 実行エンジンを起動する（本番 or paper_trading は KABUSYS_ENV で切替）:

```bash
# 本番（環境変数で切替）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
# または
python -m kabusys.run_execution
```

- Paper Trading 検証レポートを生成する:

```bash
# デフォルト DB を参照
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- Streamlit ダッシュボード（監視 DB を読み取り専用で表示）:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI モジュールを直接呼ぶ（プログラム内から）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キーを引数または環境変数 `OPENAI_API_KEY` で渡してください。

---

## 主要な挙動・注意点

- Monitoring は常に（KABUSYS_ENV に依存せず）監視用の sqlite_path（デフォルト: data/monitoring.db）を使用します。
- run_execution は Paper Trading の場合、`PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と完全分離します。
- config モジュールはプロジェクトルートを自動探索して `.env` / `.env.local` を読み込みます。OS 環境変数は上書きされません（ただし .env.local は override=True で設定される）。
- `MONITOR_POLL_INTERVAL`（run_monitoring）の値が 1 未満や不正な場合はデフォルト 60 秒にフォールバックします。
- process_prioriy（高優先度設定）を起動時に試みますが、権限不足などで失敗した場合はログに警告を出し続行します。
- OpenAI 呼び出しはエラー時にリトライやフォールバック処理を行い、致命的な例外を上位に投げない設計（フェイルセーフ）になっています。
- monitoring_db.init_monitoring_db は冪等実行可能で、既存 DB に対する簡単なスキーママイグレーション（カラム追加）処理が含まれます。

---

## ディレクトリ構成

大まかな構成は下記の通りです（本 README の解析対象ファイルを反映）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite スキーマ & DB ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py     —（参照あり。実装ファイルは本断片に一部）
      - execution_engine.py    —（参照あり。実装ファイルは本断片に一部）
      - reconciler.py
      - broker_factory.py
      - broker_api.py
      - order_record.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - pipeline.py             — get_last_price_date 等（参照）
      - stats.py                — zscore_normalize 等（参照）
    - utils/
      - __init__.py
      - process_priority.py

- data/ (推奨)
  - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
  - monitoring.db (デフォルト: data/monitoring.db)
  - paper_trading.db (Paper Trading 用デフォルト: data/paper_trading.db)
  - execution.pid
  - kill.flag

---

## 開発メモ / 運用メモ

- Paper Trading は本番 DB を汚染しないために `PAPER_TRADING_SQLITE_PATH` を用いる点に注意してください。
- AI 機能（news_nlp / regime_detector）は OpenAI API に依存します。API Key がないと ValueError を投げるため、単体テストや CI ではモックしてください（モジュール内で API 呼び出し関数を差し替え可能）。
- `monitoring_db.init_monitoring_db` は既存 DB に対する簡易マイグレーションを行いますが、複雑なスキーマ変更が必要な場合は別途マイグレーション手順を用意してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。実運用では read-only URI でアクセスすることを想定しています。

---

この README はコード断片に基づいて自動生成したものです。実際の実行には環境（Broker 実装、DB の初期データ、API キー等）の準備が必要です。必要に応じて README を補完してください。