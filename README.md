# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視コンポーネント群を含む Python パッケージです。本 README はコードベース（src/kabusys 以下）の主要な使い方、設定、構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 市場データ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注ロジック・ブローカー連携（execution）
- 監視・アラート・ダッシュボード（monitoring）
- ニュース NLP / レジーム判定等の AI 補助（ai）
- 運用補助ツール（tools）

設計方針の要点：
- DuckDB / SQLite を使ったローカル DB ベース（運用データと paper_trading は分離可能）
- AI（OpenAI）を使う処理は API キーを明示的に渡すか環境変数で指定
- 自動ロードされる .env ファイル（プロジェクトルートの .env / .env.local）から設定を取得可能
- 実行中プロセスの優先度・CPU affinity を設定するユーティリティあり

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注セッション（ブローカー抽象化、リスク管理、リコンサイル）
  - paper_trading モード：MockBrokerClient を用いた完全分離（データは data/paper_trading.db）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - LINE 通知（AlertManager）と kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC 算出、統計サマリ
- AI
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA + マクロニュース LLM）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+ を推奨（使用しているライブラリに依存）
- 仮想環境（venv / pyenv 等）を推奨

依存パッケージ（代表例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（pip）
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil requests openai streamlit
```

環境変数の設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数より優先度は低い）。
- 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

最低限必要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- OPENAI_API_KEY — OpenAI を使う機能で必要（AI 機能を使う場合）
- 他はデフォルト値が設定されているものが多い（下記参照）

例: .env（抜粋）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## 主要な環境変数とデフォルト（Settings モジュールに基づく）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録する
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI を使う機能で必須（news_nlp / regime_detector）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: "1" で実行開始時に kill.flag を削除
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring スクリプトで使用。デフォルト 60）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（%）

---

## 使い方（実行例）

1. ExecutionEngine を起動（本番/開発/紙取引により挙動が変わる）
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録します。

2. Monitoring（ポーリングループ）を起動
```
python -m kabusys.run_monitoring
```
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
- 実行開始時にプロセス優先度を high に設定しようとします（psutil の権限に依存）。

3. Streamlit ダッシュボード（ローカルで監視状況を確認）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

4. Paper Trading 検証レポート出力
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB: data/paper_trading.db。--db で別パス指定可。
```

5. AI 機能（ニューススコア / レジーム検出）
- OPENAI_API_KEY を設定し、該当関数を呼ぶ（score_news / score_regime）。これらは DuckDB 接続と target_date を受け取って実行します。

注意点
- 実運用時は systemd や supervisor 等でプロセス管理することを推奨します。
- ExecutionEngine は起動時に kill.flag をチェック・削除する設定が可能（Settings.kill_flag_clear_on_start）。

---

## 監視 DB（SQLite）スキーマ

init_monitoring_db() により作成されるテーブル（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 固定行, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

これらは MonitoringDB クラスで読み書きするユーティリティが提供されています。

---

## ディレクトリ構成（src/kabusys の主なファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定管理（.env 自動読み込み含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング
    - regime_detector.py — マーケットレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（MonitoringDB）
    - system_monitor.py — システム監視（CPU/メモリ/データ鮮度など）
    - trade_monitor.py — 注文滞留 / 約定価格異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理（Execution 停止シグナル）
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py — 発注ステートマシンの外向き API
    - reconciler.py — 起動時の自動復旧 / リコンシリエーション
    - （その他：broker_factory, execution_engine, order_repository 等が存在）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

（省略されたファイル群も多くありますが、上記が主要コンポーネントです）

---

## 実践的な運用メモ・注意事項

- paper_trading モードは本番 DB と完全に分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は Monitoring 用の本番 sqlite_path を常に使用します（KABUSYS_ENV に依存しない）。
- PID / kill.flag を使ったプロセス連携あり（実行制御のためのファイルに書き込みます）。PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）。
- OpenAI を使う機能は API のレート制限やエラーに対してリトライ・フェイルセーフが組み込まれていますが、API キー・課金に注意してください。
- .env のパースはシェルの export 文・クォート・インラインコメント等をある程度扱える独自実装になっています。
- CPU 優先度設定や CPU affinity は psutil と OS の権限に依存します。アクセス拒否時はログに WARN を出して続行します。

---

## よく使うコマンド（まとめ）

- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- （AI を使用する際は OPENAI_API_KEY を設定）

---

必要であれば、README に含める環境変数の完全一覧、systemd ユニット例、テスト手順、または各モジュールの API リファレンス（関数 / クラス説明）を追加で作成できます。どの情報を優先して追記しましょうか？