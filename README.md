# KabuSys

日本株自動売買システムのコードベース（抜粋）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・検証・監視を支援する Python ベースのシステムです。  
主な機能は以下を含みます：

- シグナル → 注文発行 → 注文状態管理（ExecutionEngine）
- 注文・約定・ポジションの永続化（SQLite）
- モニタリング（リソース・プロセス・注文滞留・リスク）とアラート送信（LINE）
- Paper Trading 用の隔離された DB / Mock ブローカー
- Research 用のファクター計算（DuckDB を用いた時系列計算）
- ニュース NLP（OpenAI を用いたニュースセンチメント評価）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 検証レポート生成ツール

設計方針の特徴：
- DB は監視用（SQLite）と分析用（DuckDB）を分離
- Paper Trading は本番 DB と完全に分離される（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しは失敗時にフォールバックし、システム全体の停止を招かない設計

---

## 機能一覧（抜粋）

- Execution
  - ブローカークライアント（実口座 or Mock）
  - OrderManager（注文作成・同期・キャンセルなど）
  - Reconciler（起動時に OrderSent の再照合とポジション差分確認）
  - RiskManager（注文制限、レート制限、ドローダウン等）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、PID・データ鮮度確認）
  - TradeMonitor（滞留注文検出、約定異常検出）
  - RiskMonitor（ドローダウン、ポジション上限検出）
  - KillSwitch（リスクトリガーで ExecutionEngine を停止する flag 書込）
  - AlertManager（LINE によるプッシュ通知、クールダウン管理）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio construction
  - 候補選定、重み付け（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ決定（単元丸め、総額スケーリング）
- Research
  - ファクター計算（Momentum/Volatility/Value 等） — DuckDB を利用
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース NLP（OpenAI で記事ごとの銘柄センチメント算出）
  - レジーム判定（MA200 とマクロニュースの LLM スコアを合成）
- ツール
  - paper_verification_report（Paper Trading 検証レポート生成）

---

## 前提 / 必要環境

- Python 3.9+
- pip
- システムでの sqlite3 は標準ライブラリに含まれます
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

（実際の運用では requirements.txt を用意して pip install -r で管理してください。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. data ディレクトリ（デフォルト DB 保存先）を作成
   - mkdir -p data
5. 環境変数・.env の準備
   - リポジトリルートに `.env` を置くと自動で読み込まれます（.env.local も読み込み可）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

推奨（.env の例）
```
# .env (例)
KABUSYS_ENV=development           # development | paper_trading | live
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
PAPER_FILL_MODE=instant          # instant | partial | never | reject
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（主要スクリプト）

注: パッケージを直接参照して実行する場合、ルートから PYTHONPATH を src に通すか `python -m` で実行します。

- ExecutionEngine を起動（本番 or paper_trading を Settings.env で切替）
  - 実行コマンド例:
    - PYTHONPATH=src python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録され、本番 DB と分離されます。
    - 起動前に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中に `data/stop_requested.flag` を作成するとエンジンは順次停止します。
    - ExecutionEngine の PID は `data/execution.pid`（デフォルト）に書き込まれます。

- Monitoring（常時ポーリング）を起動
  - 実行コマンド例:
    - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。不正値または <=0 の場合は 60 にフォールバック。
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を利用して監視ログ（SQLite）を書き込みます（Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用）。
    - 停止は `data/stop_requested.flag` を作成することで行います。

- Streamlit ダッシュボード（監視可視化）
  - 実行コマンド例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開き、ダッシュボードに必要な表を表示します。

- Paper Trading 検証レポート生成ツール
  - 実行コマンド例:
    - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - または DB パスを明示: --db /path/to/data/paper_trading.db
  - 主要指標:
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど
  - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API を使用するため `OPENAI_API_KEY` を設定してください。
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 失敗時はフォールバック処理（例: macro_sentiment=0.0）を行う設計です。

---

## 停止・フラグ運用

- 共通停止フラグ（run_execution / run_monitoring が監視）
  - data/stop_requested.flag を作成すると各プロセスはループ中に検知して終了します。
- ExecutionEngine の緊急停止（KillSwitch）
  - KillSwitch は監視ルール（ドローダウン超過、ポジション上限等）で `data/kill.flag` を書き込み、これを検知した ExecutionEngine は安全停止します。  
  - KillSwitch は理由テキストをファイルに書き込みます。起動時にクリーンアップ（削除）を行う設定（Settings.kill_flag_clear_on_start）があります。

---

## 環境設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（Settings.env）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 利用（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（未設定なら送信はスキップ）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

Settings モジュールはルートの `.env` / `.env.local` を自動でロードします（既存 OS 環境変数を保護）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）
    - regime_detector.py    — レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py      — 監視ログ DB 層（SQLite）
    - system_monitor.py     — システム監視
    - trade_monitor.py      — 注文監視
    - risk_monitor.py       — ドローダウン等リスク監視
    - kill_switch.py        — KillSwitch（kill.flag 操作）
    - alert_manager.py      — LINE 通知
    - monitoring_engine.py  — 各モニタの統合ポーリングエンジン
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                   — （ブローカー API / engine / order_repository 等）
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み
    - position_sizing.py    — 株数決定 / スケール処理
    - risk_adjustment.py    — セクター・レジーム調整
  - research/
    - factor_research.py    — ファクター計算（DuckDB）
    - feature_exploration.py— IC / ランク / 統計サマリ
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - data/                   — デフォルトの DB / flag 保存場所（リポジトリ外でも可）
    - monitoring.db (デフォルト)
    - paper_trading.db (paper)
    - kabusys.duckdb

（実際のリポジトリには上記に加えて execution の詳細実装、data パイプライン、その他モジュールが含まれます。）

---

## 運用上の注意 / ヒント

- Paper Trading は本番 DB と完全分離されています。運用時は env を誤らないよう注意してください（KABUSYS_ENV）。
- OpenAI API 利用はコストとレイテンシが発生します。APIキー管理とレート制限に注意してください。
- Monitoring はデフォルトで本番 sqlite_path を使用します（KABUSYS_ENV に関わらず）。
- process_priority（psutil）や cpu_affinity の設定は権限や OS に依存して失敗する場合があるためログを確認してください。
- DuckDB への書き込みは executemany などのバージョン依存の挙動に注意（コード内に互換性考慮あり）。
- 長時間運用するプロセス（Execution / Monitoring）はログ監視と flag ベースの graceful shutdown を組み合わせることを推奨します。

---

README は以上です。必要であれば次の内容を追加できます：
- 実際の起動例の systemd ユニットファイル例
- CI / テスト実行方法
- 具体的な .env.example ファイル
- 実装済みブローカーや Mock の詳細仕様

どれを追加しましょうか？