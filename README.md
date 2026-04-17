# KabuSys

日本株自動売買システムのサブセット実装。ポートフォリオ構築・ポジションサイズ計算・監視・実行エンジン補助・AI を用いたニュースセンチメント/レジーム判定・研究用ファクター計算などのユーティリティ群を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ／ツール群です。本リポジトリには次の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）の起動補助スクリプト
- 監視（MonitoringEngine）と各種モニタ（システム・注文・リスク）
- 監視ダッシュボード（Streamlit）
- Paper Trading 用検証レポート生成ツール
- ポートフォリオ構築、ポジションサイズ決定・リスク調整
- 研究用ファクター計算・特徴量探索ユーティリティ
- ニュース NLP（OpenAI を用いたセンチメントスコアリング）と市場レジーム判定

設計上の要点：
- DuckDB / SQLite を用いたデータ永続化（監視用は SQLite）
- Paper Trading は本番 DB と分離（既定: data/paper_trading.db）
- 環境変数/.env による設定（自動ロード機能あり）
- OpenAI API 呼び出しは冗長性と安全性を考慮した実装（リトライ・バリデーション）

---

## 主な機能一覧

- 監視（monitoring）  
  - system_monitor: CPU/メモリ/ディスク、実行プロセス PID、株価データ鮮度を監視しログ保管
  - trade_monitor: 注文滞留・約定価格異常を検出してリスクログ記録
  - risk_monitor: ドローダウンやポジション数限界を検出して kill.flag 生成
  - alert_manager: LINE Messaging API へプッシュ通知（クールダウン管理あり）
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

- 実行（execution）  
  - ExecutionEngine 起動スクリプト（run_execution.py）: 環境に応じて MockBroker を使用する（paper_trading）
  - Reconciler: 再起動後の注文状態・ポジション突合

- Paper Trading / 検証  
  - tools.paper_verification_report: Paper Trading の SQLite を読み検証レポートを生成

- ポートフォリオ関連（portfolio）  
  - 銘柄選定、等重/スコア加重、セクター上限適用、レジーム乗数、株数算出（単元丸め・資金配分）

- 研究（research）  
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン計算、IC 計算、統計サマリ

- AI（ai）  
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとの ai_score を書き込み
  - regime_detector.score_regime: ETF（1321）MA 乖離とマクロニュースを合成して市場レジーム判定

---

## 必要条件（主な依存パッケージ）

最低限（抜粋）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3（標準ライブラリ）
- その他（プロジェクトにより追加）

（実際の運用では requirements.txt を用意して pip install -r で管理してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際は requirements.txt があればそれを使う）
4. data ディレクトリを作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例: .env の最小例
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=（通知を使う場合）
LINE_USER_ID=（通知を使う場合）
```

環境変数の読み込み仕様:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local をロードします。
- OS 環境変数 > .env.local > .env の優先順位で適用されます。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定動作）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

---

## 使い方（実行例）

以下はプロジェクトルートからの実行例です。Python パスが src を含むことを前提とするか、モジュール実行を利用してください。

1. 監視（MonitoringEngine）の起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更可能
   - 注意: Monitoring は KABUSYS_ENV にかかわらず設定された sqlite_path を使用します

2. 実行エンジンの起動（ExecutionEngine の補助スクリプト）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）が使われます
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します
   - 実行中は同フラグを作成するとエンジンが停止されます

3. 監視ダッシュボード（Streamlit）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - もしくは streamlit run path/to/src/kabusys/monitoring/streamlit_dashboard.py -- --db /absolute/path

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI / レジーム処理の呼び出し例（Python から）
   - news_nlp の呼び出し例:
     ```
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
     ```
   - regime_detector の呼び出し例:
     ```
     from datetime import date
     import duckdb
     from kabusys.ai.regime_detector import score_regime

     conn = duckdb.connect("data/kabusys.duckdb")
     score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
     ```

---

## 停止・フラグ周り

- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクトの data/stop_requested.flag を監視しています。
  - これを作成するとループを抜けて安全に終了します。
  - 場所:
    - run_monitoring: package ルート相対の data/stop_requested.flag（run スクリプト内で決定）
    - run_execution: プロジェクトルート/data/stop_requested.flag

- kill.flag
  - KillSwitch（RiskMonitor の判定）によって data/kill.flag が書き込まれると ExecutionEngine に停止シグナルが送られます（Execution 側でのチェックは組み込みや設計に依存）。
  - KillSwitch は冪等で既存ファイルがあれば再書き込みしません。
  - Settings.kill_flag_clear_on_start を利用して起動時にクリアするオプションがあります。

- PID ファイル
  - 実行プロセスは data/execution.pid を参照/生成することがあります。古い PID が残っていると stale PID と見なされ削除されることがあります。

---

## ディレクトリ構成

（提供されたソースに基づく主要ファイル・モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                       — 設定/環境変数読み込み
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 監視 DB 層（スキーマ初期化・操作）
    - system_monitor.py              — システム/データ鮮度監視
    - trade_monitor.py               — 注文監視（滞留・約定異常）
    - risk_monitor.py                — ドローダウン / ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - alert_manager.py               — LINE への通知
    - monitoring_engine.py           — 複数モニタを束ねるエンジン
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - execution/
    - reconciler.py                  — 起動時リコンシリエーション
    - order_manager.py               — 発注・状態管理ロジック
    - (その他: broker_factory, execution_engine, order_repository 等)
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
    - news_nlp.py                     — ニュース NLP（OpenAI）
    - regime_detector.py              — 市場レジーム判定（OpenAI + MA）
    - __init__.py
  - utils/
    - process_priority.py             — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/ (ランタイムで使用するファイル群)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 動作上の注意 / 運用メモ

- 監視（monitoring）は監視 DB のパス（SQLITE_PATH）を使用します。実運用環境でのパス設定に注意してください。
- Paper Trading は本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 利用時は APIKey の管理を厳重に（環境変数で設定）。API 失敗時はフェイルセーフでスコアをスキップまたは既定値にフォールバックする実装となっていますが、ログを必ず確認してください。
- process priority / CPU affinity の設定はプラットフォーム依存です。権限がない場合は警告でスキップされます（psutil が利用）。

---

## 貢献・拡張のヒント

- requirements.txt を整備して依存関係を固定する
- tests を追加して各 pure function（portfolio, research 等）を網羅する
- ExecutionEngine 側の起動/停止の公開インタフェースを明確化し、外部からの graceful stop を統一する
- ダッシュボードの UI を拡充してアラートの履歴表示やログダウンロード機能を追加する

---

必要であれば、README に含める具体的な .env.example、requirements.txt の推奨内容、または各モジュールの簡易 API ドキュメント（関数シグネチャ例）を追記します。どの追加情報が必要か教えてください。