# KabuSys

日本株自動売買システムの一部実装（ライブラリ + CLI / 実行スクリプト群）。

このリポジトリには、実行エンジン、監視（Monitoring）、ポートフォリオ構築・サイズ計算、リサーチ（ファクター計算）、AI 補助（ニュースセンチメント・レジーム判定）、および運用ツールが含まれます。

---

## 概要

KabuSys は日本株アルゴリズム運用のためのモジュール群です。主な責務は次のとおりです。

- 実行エンジン（ExecutionEngine）を通じたブローカー発注管理（OrderManager / Reconciler 等）
- 取引・システム状態の監視（Monitoring：SystemMonitor / TradeMonitor / RiskMonitor / AlertManager 等）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・セクター制約など）
- ファクター計算・研究用ユーティリティ（DuckDB を用いた prices_daily/raw_financials 参照）
- ニュース NLP（OpenAI を用いたセンチメント評価）・市場レジーム判定
- 運用向けユーティリティ（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計方針として、DB（SQLite / DuckDB）をデータ永続化・分析に用い、本番・PaperTrading を分離できるように設計されています。AI 呼び出しは OpenAI（gpt-4o-mini 等）を想定しますが、API キーが未設定でもフェイルセーフに動作するよう考慮されています。

---

## 主な機能一覧

- 実行（run_execution.py）
  - KABUSYS_ENV により本番 / paper_trading を切替可能。
  - Paper Trading 時は MockBrokerClient を使用し、別 DB（data/paper_trading.db）へ記録。
  - 起動時にプロセス優先度を設定（psutil 経由）。

- 監視（run_monitoring.py + MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク、PID ファイル、データ鮮度を監視して monitoring DB に記録。
  - TradeMonitor: 滞留注文・約定異常価格の検出とログ化。
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新とリスクイベント記録。
  - KillSwitch: しきい値超過時に flag ファイル（data/kill.flag）を書き ExecutionEngine に停止指示。
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン機能あり）。
  - Streamlit ダッシュボード（簡易 GUI）で監視データを表示。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（スコア順）、等金額配分 / スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（リスクベース / weight ベース）、単元株丸め、aggregate cap

- 研究（kabusys.research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（kabusys.ai）
  - ニュース NLP（raw_news → ai_scores）: OpenAI でセンチメントを算出し ai_scores に格納
  - レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成）

- 運用ツール（kabusys.tools）
  - Paper Trading 検証レポート生成スクリプト（期間指定で指標を集計・判定）

---

## セットアップ手順

前提：
- Python 3.9+（互換性に応じて適宜）
- SQLite は標準で利用可能
- DuckDB、psutil、requests、openai、streamlit などのパッケージが必要

推奨: 仮想環境を作成してからインストールしてください。

例（venv + pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

※ 追加でアプリ実行に必要なパッケージがあれば適宜インストールしてください。

.env の自動読み込み:
- プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順、.env.local は上書き）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の環境変数（一部）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信に必要）
- その他は Settings クラスのプロパティを参照（下記に主なキーとデフォルトを示します）。

主な設定（環境変数）とデフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）

例 .env:
```
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

注意:
- プロセス優先度設定（psutil）や CPU affinity は OS により権限が必要な場合があります。権限不足なら警告を出してスキップします。

---

## 使い方

主要なエントリポイントと実行例。

1. 監視ループを起動（常駐）
```bash
python -m kabusys.run_monitoring
# または環境変数でポーリング間隔を調整
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。1 未満や負の値は無視されデフォルト 60 秒が使われます。
- monitoring は KABUSYS_ENV にかかわらず `Settings.sqlite_path`（デフォルト data/monitoring.db）を使用します。

2. 実行エンジン（ExecutionEngine）を起動
```bash
# 本番設定（KABUSYS_ENV=live）
KABUSYS_ENV=live python -m kabusys.run_execution

# Paper Trading
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- paper_trading の場合は `Settings.paper_sqlite_path`（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離されます。
- 起動時に PID ファイル（デフォルト data/execution.pid）が書かれ、Monitoring の SystemMonitor がそれを参照してプロセス監視を行います。
- ExecutionEngine は起動時に Reconciler を使って未解決注文の突合せを行います。

3. Streamlit 監視ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 読み取り専用で monitoring DB を開き、Overview / Positions / Orders / System タブを表示します。

4. Paper Trading 検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- 様々な運用指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を計算し PASS/FAIL を出力します。

5. AI 機能
- ニュースセンチメント（kabusys.ai.score_news）やレジーム判定（kabusys.ai.regime_detector.score_regime）は OpenAI API キー（OPENAI_API_KEY）が必要です。キー未指定時は ValueError が発生します。
- API 呼び出しはリトライやフォールバック（失敗時は中立値）などの耐障害設計が組み込まれています。

---

## 運用上の留意点

- PID ファイル・kill.flag:
  - ExecutionEngine は起動時に PID を data/execution.pid に書きます。SystemMonitor は PID の有無でプロセス稼働の有無を判断します。
  - KillSwitch は条件を満たすと data/kill.flag を作成します。ExecutionEngine はこのファイルを検知して安全シャットダウンするような実装を想定しています（ExecutionEngine 側の実装を確認してください）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（列追加）を行います。既存 DB に対して冪等に実行できます。
- Paper Trading:
  - paper_trading 環境ではブローカー呼び出しは Mock に切替え、本番 DB とは別 DB を用いることでテストと本番を分離します。
- プロセス優先度・CPU affinity:
  - set_process_priority / set_cpu_affinity は psutil を利用します。OS による差分（Windows / POSIX）を吸収しますが、権限不足や未サポート OS の場合は警告が出てスキップされます。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要モジュールとファイルの概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロード・Settings クラス
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py        (参照: プロジェクト内に存在)
    - execution_engine.py        (参照: 実行ロジック)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
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
    - news_nlp.py                 — ニュースセンチメント評価（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - __init__.py
    - paper_verification_report.py

（上記に示したファイルの中にはさらに依存・補助モジュールが含まれます。実行前に必要なモジュールを確認のうえインストールしてください。）

---

## 追加情報 / トラブルシュート

- .env のパースは shell スタイルの簡易サポートがあり、クォートやエスケープ、コメント行に対応しています。ただし特殊なケースは想定外の挙動になる恐れがあります。
- DuckDB / SQLite の接続はファイルパスを Settings で指定します。並列での書き込みやファイルロックに注意してください。
- OpenAI 呼び出しはリトライ・バックオフが組み込まれていますが、API 料金やレート制限には注意してください。
- psutil の機能（nice, cpu_affinity 等）は実行環境の権限に依存します（root や管理者権限が必要な場合があります）。

---

必要に応じて README を拡張します。特にデプロイ手順、Systemd ユニットファイル、CI/CD、テストの実行方法、ExecutionEngine の詳細な起動オプション等が必要であれば教えてください。