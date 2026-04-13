# KabuSys

日本株自動売買システムのサブパッケージ群（ポートフォリオ構築、ファクター研究、実行エンジン、監視、AI 補助等）。この README はリポジトリ内の主要なスクリプト・モジュールの使い方、セットアップ、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ兼実行基盤です。以下の機能群を提供します。

- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リスク調整（セクター上限、レジーム乗数）
- ファクター計算・研究（モメンタム、バリュー、ボラティリティ、IC 計算等）
- 実行エンジン（Order 管理、ブローカーとの同期・リコンシリエーション）
- 監視（システム状態、注文滞留、ドローダウン等の定期チェック、LINE 通知）
- AI 支援（ニュース NLP によるセンチメント評価、レジーム判定）
- 開発 / 運用ユーティリティ（Streamlit ダッシュボード、検証レポート生成）

設計方針として、主要なアルゴリズムは純粋関数（副作用なし）で実装され、DB は DuckDB / SQLite を利用します。OpenAI API による処理は明示的な API キー指定が必要で、失敗時はフェイルセーフで継続するよう実装されています。

---

## 主な機能一覧

- portfolio/
  - 候補選定 (select_candidates)
  - 等金額・スコア重み (calc_equal_weights, calc_score_weights)
  - ポジションサイズ決定（単元株丸め、リスクベース等）(calc_position_sizes)
  - セクターキャップ、レジーム乗数 (apply_sector_cap, calc_regime_multiplier)
- research/
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 研究ユーティリティ: calc_forward_returns, calc_ic, factor_summary
- execution/
  - Order 管理、OrderRepository、Reconciler（起動時の自動リコンシリエーション）
  - BrokerFactory を通した本番 / Paper Trading 切替
- monitoring/
  - SystemMonitor, TradeMonitor, RiskMonitor（定期チェック）
  - MonitoringEngine（監視ループ）
  - AlertManager（LINE 通知）
  - KillSwitch（フラグファイルで Execution 停止）
  - streamlit_dashboard（監視ダッシュボード）
- ai/
  - news_nlp.score_news（ニュースを LLM でスコア化して ai_scores に書き込み）
  - regime_detector.score_regime（MA とマクロ NLP を組合せてレジーム判定）
- tools/
  - paper_verification_report（Paper Trading 検証レポート生成）

---

## 必要な依存パッケージ（例）

プロジェクトは以下のパッケージに依存します（環境や機能により追加で必要になる場合があります）。

- python >= 3.9
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（仮の requirements.txt を想定）:

```bash
pip install duckdb psutil requests openai streamlit
```

プロジェクトに requirements.txt がある場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を準備します。

2. 依存パッケージをインストールします（上記参照）。

3. データディレクトリを作成します（デフォルトは data/）。

```bash
mkdir -p data
```

4. 環境変数を設定します。開発ではルートに `.env` を置くことで自動読み込みされます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須例（.env の例）:

```
# API / 認証
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...

# OpenAI（AI 機能を使う場合）
OPENAI_API_KEY=...

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live

# DB パス（必要に応じて）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# その他
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant  # instant|partial|never|reject
```

注意:
- `KABUSYS_ENV` が `paper_trading` の場合、ExecutionEngine は MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` に記録します（本番 DB と分離）。
- 監視（monitoring）は、`KABUSYS_ENV` にかかわらず常に `SQLITE_PATH` を使用します（本番監視 DB を想定）。

---

## 主要スクリプト / 使い方

パッケージとしてモジュールを直接実行できます（例: python -m kabusys.run_monitoring）。以下は主要な起動方法の例です。

- 監視ループ（SystemMonitor のポーリング。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に上書き可能。デフォルト 60 秒）

```bash
python -m kabusys.run_monitoring
# または環境変数で間隔を指定
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 実行エンジン起動（ExecutionEngine。`KABUSYS_ENV=paper_trading` の場合は paper DB を使用）

```bash
python -m kabusys.run_execution
# Paper trading で起動
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Streamlit 監視ダッシュボード（読み取り専用で monitoring DB を開く）

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成ツール

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を直接指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI 関連（プログラムから呼ぶ）

news_nlp.score_news や regime_detector.score_regime はプログラムから呼び出して使用します。OpenAI API を使うには `OPENAI_API_KEY` を環境変数に設定するか、関数引数で API キーを渡してください。例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,4,10), api_key=None)  # env OPENAI_API_KEY を使用
```

---

## 主な環境変数（まとめ）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能で必要)
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- データベース / パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- Paper Trading の挙動
  - PAPER_FILL_MODE: instant|partial|never|reject (デフォルト: instant)
- 監視関連しきい値（デフォルト値）
  - CPU_THRESHOLD_PCT (デフォルト: 90.0)
  - MEMORY_THRESHOLD_PCT (デフォルト: 85.0)
  - DISK_THRESHOLD_PCT (デフォルト: 90.0)
- モニタリング間隔
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない

---

## 注意事項 / 運用メモ

- 監視（Monitoring）は環境にかかわらず `SQLITE_PATH` を使う設計です（監視は本番 DB を想定）。一方で ExecutionEngine は `KABUSYS_ENV=paper_trading` の場合 `PAPER_TRADING_SQLITE_PATH` を使用して DB を分離します。
- 起動時、プロセスは set_process_priority("high") を試みます。権限や OS により失敗する場合はログのみ出力されます。
- OpenAI を利用する機能は外部 API 呼び出しのため、API 制限・課金・レイテンシ・失敗を考慮して設定してください。モジュール内でリトライやバックオフが実装されていますが、運用時はキーやコスト管理に注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、既存テーブルにカラムがない場合は ALTER を行う簡易的なマイグレーションを含みます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py              — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py                  — ニュースを LLM でスコア化して ai_scores に書き込み
  - regime_detector.py           — レジーム判定（MA + マクロ NLP）
  - __init__.py
- monitoring/
  - monitoring_db.py             — SQLite を使った永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
  - __init__.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（ブローカー関連、OrderRepository 等）
- tools/
  - paper_verification_report.py
  - __init__.py
- research/（上記）
- その他: data/ に各 DB ファイル（duckdb / sqlite）を配置する想定

---

## 開発・貢献

バグ報告や機能追加の提案は issue を作成してください。テストや CI、スタイルガイド（flake8/black 等）の導入も推奨します。AI / ブローカー連携周りは外部依存が大きいためモックを用いた単体テストを推奨します（モジュール上で外部呼び出しを行う関数は差し替え可能な設計にしています）。

---

この README はコードベースから主要点を抜粋してまとめています。実運用時は `.env.example`（存在する場合）を参考に環境変数を設定し、まずはローカルで Paper Trading モードで各機能を検証してください。