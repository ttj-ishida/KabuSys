# KabuSys

日本株自動売買システムのコードベース（モジュール群）の README。  
本ドキュメントはプロジェクトの概要、機能一覧、セットアップ手順、主要な使い方、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの一部実装です。  
主な機能は次の通りです：

- 実行エンジン（ExecutionEngine）による発注・注文管理・リスク制御
- 監視サブシステム（MonitoringEngine）によるプロセス・注文・リスク・データ鮮度監視
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- ニュースを用いた AI（LLM）によるセンチメントスコアリング & 市場レジーム判定
- Paper Trading 用の分離された DB と検証用レポート生成
- Streamlit を用いた監視ダッシュボード

設計思想の要点：
- 本番 DB と paper_trading（検証）DB を分離
- 外部 API 呼び出し（OpenAI 等）は明示的に API キーで制御
- フェイルセーフ（API 失敗時はスキップやデフォルト値を使用）
- ルックアヘッドバイアス回避（日時参照の取り扱いに注意）

---

## 機能一覧（抜粋）

- Execution
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時復旧（ブローカー照合）
  - RiskManager によるリスク制御（閾値・レート制限等）
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk/プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション数上限の検出、ダッシュボード更新
  - KillSwitch: 条件を満たした場合に flag ファイルを出力し ExecutionEngine を停止
  - AlertManager: LINE によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - DuckDB を用いたファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI
  - news_nlp.score_news: raw_news を LLM でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF 等の MA とマクロニュースを合成しレジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート出力

---

## セットアップ

必要な依存関係（代表例）：
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

インストール例（venv を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

環境変数・.env の自動読み込み：
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（Settings に定義されているもの）：
- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で参照
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の挙動（`instant` / `partial` / `never` / `reject`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT など（監視・運用用）

データディレクトリ：
- 既定の DB 等は `data/` 配下に置かれます（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）。
- 一時制御ファイル:
  - data/stop_requested.flag: run_* スクリプトがループ停止を検知するためのフラグ
  - data/kill.flag: KillSwitch による ExecutionEngine 停止トリガー
  - data/execution.pid: ExecutionEngine の PID ファイル

注意：Paper Trading 実行時は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB とは完全に分離されます。

---

## 使い方（主要コマンド）

※ 実行方法は、パッケージをインストールしている場合は `python -m kabusys.<module>`、開発環境であればリポジトリルートを PYTHONPATH に含めて `python src/kabusys/<file>.py` でも動作します。

1) 監視ループを起動（Monitoring）
```bash
# デフォルトのポーリング間隔 60 秒
python -m kabusys.run_monitoring

# 環境変数で間隔を上書き
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL が 0 以下・不正な場合はデフォルト（60 秒）にフォールバックします。
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用してログを永続化します。
- 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する仕様です。

2) 実行エンジンを起動（Execution）
```bash
# 本番 / development
KABUSYS_ENV=live python -m kabusys.run_execution

# Paper Trading（MockBroker を使用し data/paper_trading.db に記録）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Paper Trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
- 実行中に kill.flag（KillSwitch）や stop_requested.flag が書かれると順次停止します。

3) Streamlit 監視ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- read-only で monitoring DB に接続してダッシュボードを表示します。

4) Paper Trading 検証レポート
```bash
# デフォルト DB パス（環境変数で指定可）
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定する例
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を出力します。
- 成否判定の閾値はスクリプト内の定数で定義されています（例: 稼働率 >= 99%）。

5) AI 関連（ニューススコアリング / レジーム判定）
- OpenAI API を利用するため `OPENAI_API_KEY` を設定してください。
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を受け取る関数です。CLI ラッパーはありませんが、同様のモジュールから呼び出せます。

---

## 監視 DB（SQLite）について

- テーブル: system_status, trade_logs, positions, risk_logs, dashboard を作成します（init_monitoring_db）。
- マイグレーション: `dashboard` に `peak_value` カラムが無い場合、また `trade_logs` に `latency_ms` が無い場合は自動でカラム追加します（冪等）。
- MonitoringDB クラスを通じてログの記録・取得を行います（ログ書き込みはコミットされます）。

---

## 実装上の注意点 / 運用メモ

- PID ファイル管理: SystemMonitor は pid ファイルの存在とプロセス生存確認を行い、stale（古い）PID を検出した場合は削除してアラートを送ります。
- KillSwitch: RiskMonitor の判定（ドローダウン超過やポジション上限超過）により `data/kill.flag` が書き込まれると ExecutionEngine 停止のトリガーとなります（冪等に書き込み）。
- Paper Trading: 実際のブローカー呼び出しを伴わずローカル DB に記録するため、本番 DB を汚染しません。PAPER_FILL_MODE で約定挙動を調整できます。
- LLM 呼び出しのリトライ: news_nlp / regime_detector ではネットワーク断・429・5xx 等に対して指数バックオフでリトライし、最終的に失敗してもフェイルセーフ（0.0 等）で継続します。
- Process priority / CPU affinity: run_* スクリプト起動時にプロセス優先度を `high` に設定するユーティリティが呼ばれます（psutil を使用）。権限が無い場合は警告に留まります。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル構成です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み / Settings クラス
  - run_monitoring.py              — システム監視ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 用永続化層（MonitoringDB）
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory 等の実装が想定されます)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                          — 実行時データ (DB, PID, flags) を配置する既定パス

---

## 例：簡単な起動フロー（ローカル開発）

1. 仮想環境を作成・有効化し依存をインストール
2. `.env` または環境変数を設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
3. DuckDB / SQLite のファイルが存在しない場合は必要に応じて初期化
4. 監視を起動（別ターミナルで）:
   - `python -m kabusys.run_monitoring`
5. 実行エンジンを起動:
   - `python -m kabusys.run_execution`
6. Streamlit ダッシュボードで状況確認:
   - `streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db`
7. Paper Trading の検証:
   - `KABUSYS_ENV=paper_trading python -m kabusys.run_execution`
   - 終了後 `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

---

必要であれば、README に追加する内容（例：API の詳細仕様、DB スキーマの完全な列挙、Development / Deployment の運用手順、Unit test／CI 設定の説明など）を教えてください。README を拡張して作成します。