# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは取引エンジン、モニタリング、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などのコンポーネントを含みます。以下はコードベースに基づく README（日本語）です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（実行例）
- 主要環境変数（.env）
- 停止 / キルフラグ
- ディレクトリ構成（主要ファイル解説）

---

## プロジェクト概要

KabuSys は、以下の目的を持ったモジュール群から構成される自動売買プラットフォームです。

- シグナル → 発注 → 注文管理 → 約定管理 を行う ExecutionEngine（実取引/ペーパー取引対応）
- システム状態・注文異常・ドローダウン等を監視してアラート／キルスイッチを発動する Monitoring
- ポートフォリオ選定・配分・ポジションサイジングを行う Portfolio モジュール（純粋関数）
- DuckDB を用いたファクター計算や将来リターン分析を行う Research
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価や、マクロニュースに基づく市場レジーム判定（AIモジュール）
- 運用支援ツール（ストリームリットダッシュボード、paper trading 検証レポート等）

設計上、多くのコンポーネントは外部 DB（SQLite / DuckDB）や環境変数で挙動が制御され、テスト容易性や安全性（ペーパー取引の DB 分離、フェイルセーフな API リトライ等）に配慮されています。

---

## 主な機能一覧

- Execution
  - 本番／ペーパー取引モード切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（実ブローカー / Mock）
  - リコンシリエーション（再起動後の注文同期）
  - リスク管理（Rate limit, max position 等）
- Monitoring
  - システムリソース監視（CPU/Memory/Disk）
  - データ鮮度チェック（DuckDB の最終価格日）
  - 注文滞留・約定価格異常検出
  - ドローダウン監視・ポジション上限監視（KillSwitch と連携）
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（監視データ表示）
- Portfolio
  - 候補選定、等金額/スコア加重配分、リスクベース配分
  - セクターキャップ適用、レジーム乗数
  - 株数決定（単元丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター算出（DuckDB 上で完結）
  - 将来リターン、IC（情報係数）、統計サマリー
- AI
  - ニュース記事を LLM でセンチメント化して ai_scores に保存（news_nlp.score_news）
  - マクロニュース + ETF MA を合成して市場レジーム判定（regime_detector.score_regime）
- ユーティリティ
  - プロセス優先度・CPU affinity の設定ユーティリティ
  - .env 自動読み込み（プロジェクトルート検出）

---

## セットアップ手順

1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主要依存:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （実際の requirements.txt がある場合はそれを利用してください。）

3. リポジトリルートに `data/` ディレクトリを用意
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに `.env` を置くことで自動ロードされます（.git または pyproject.toml をルート検出の基準にします）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要に応じて OpenAI の API キーを設定（AI 機能を使う場合）
   - export OPENAI_API_KEY="sk-..."

6. データベース
   - デフォルトで以下パスを使用します（必要に応じて環境変数で上書き可）:
     - SQLite（監視用）: data/monitoring.db
     - DuckDB: data/kabusys.duckdb
     - Paper Trading SQLite: data/paper_trading.db

7. 実行前に kill/stop フラグを確認して不要なフラグは削除
   - data/kill.flag, data/stop_requested.flag

---

## 使い方（実行例）

※ ここでは主要な実行コマンドと挙動を示します。

1. 実行エンジン起動（本番 / ペーパー）
   - 本番モード（デフォルト、KABUSYS_ENV=live を想定）
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - ペーパー取引モード（MockBroker, DB は data/paper_trading.db）
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - run_execution は ExecutionEngine をバックグラウンドスレッドで動かし、data/execution.pid に PID を書く等の管理を行います。
   - 起動時に data/stop_requested.flag が存在すると起動せず終了します（安全措置）。

2. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト: 60）
     - export MONITOR_POLL_INTERVAL=30
   - run_monitoring は monitoring 用 DB（Settings.sqlite_path、デフォルト data/monitoring.db）に接続し、SystemMonitor を定期実行します。
   - 監視は Settings に関わらず「本番 sqlite_path（data/monitoring.db）」を使用します（設計上の注意）。

3. Streamlit ダッシュボード（監視結果の可視化）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI 関連（ライブラリ関数として利用）
   - ニューススコア付与:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="sk-...")
   - レジームスコア:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="sk-...")
   - 注意: API コールはコストとレート制限の考慮が必要。OPENAI_API_KEY 環境変数でキーを渡せます。

---

## 主要環境変数（.env）

設定は環境変数から読み込まれ、Settings クラスでアクセスします。主なキー:

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- OPENAI_API_KEY — AI 機能で使用
- PAPER_FILL_MODE — paper_trading の約定挙動
  - 値: instant | partial | never | reject
  - デフォルト: instant
- PAPER_TRADING_SQLITE_PATH — ペーパー取引用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか ("1" で有効)
- LOG_LEVEL — DEBUG/INFO/...
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を検出）から `.env` を自動ロードします。
- `.env.local` は `.env` で未設定のキーを上書きする形で読み込まれます。
- 自動読み込みを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env の内容の一例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development
- PAPER_FILL_MODE=instant
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

---

## 停止 / キルフラグ

- stop_requested.flag
  - path: data/stop_requested.flag
  - run_execution と run_monitoring はループ内でこのファイルの存在をチェックし、存在すれば安全にシャットダウンします。
  - 管理運用で外部から「停止」を指示するために利用します（ファイル作成で停止要求）。

- kill.flag
  - path: デフォルト data/kill.flag（Settings.kill_flag_path）
  - KillSwitch が危険事象（例: ドローダウン超過、ポジション数上限超過）を検出した場合に書き込まれ、ExecutionEngine 側で検出・停止トリガーとなります。
  - KillSwitch は既存ファイルがあれば書き直しません（冪等）。

- PID ファイル
  - ExecutionEngine は data/execution.pid（Settings.pid_file_path）等に PID を書きます。SystemMonitor はこの PID を見てプロセスが生存しているか判定します。stale PID は自動で削除され、リスクログに記録されます。

---

## DB とスキーマ（監視用）

監視サブシステムは monitoring_db モジュールで以下テーブルを初期化します（冪等）:

- system_status (cpu, memory, disk, process_ok, recorded_at)
- trade_logs (発注イベントログ、latency_ms カラムあり)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (リスクイベント)
- dashboard (単一行 id=1: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

monitoring_db.init_monitoring_db() は既存 DB のマイグレーション（カラム追加）も行います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割（抜粋）です。

- kabusys/
  - __init__.py — パッケージ定義（version）
  - config.py — 環境変数/設定管理（Settings クラス、自動 .env ロード）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - run_execution.py — ExecutionEngine 起動スクリプト
    - order_manager.py — 発注の高レベル API（状態遷移制御）
    - reconciler.py — 再起動後の照合 (order/position)
    - order_repository.py, order_record.py, broker_factory 等（注文永続化/ブローカー抽象）
  - monitoring/
    - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
    - monitoring_db.py — SQLite ベースの監視データ永続化層
    - system_monitor.py — CPU/メモリ/DuckDB データ鮮度チェック等
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成ロジック
    - alert_manager.py — LINE push 通知ラッパ
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数計算（リスクベース等）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — raw_news を LLM に問い合わせて ai_scores に書き込む
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力ユーティリティ

（上記は代表的なファイルであり、細かいモジュールはフォルダ内を参照してください。）

---

## 運用上の注意点 / ベストプラクティス

- 環境分離
  - ペーパー取引時は必ず KABUSYS_ENV=paper_trading を指定してください。Mock ブローカーと専用 SQLite（PAPER_TRADING_SQLITE_PATH）に切り分けられます。
- .env の扱い
  - CI/デプロイでは OS 環境変数を優先し、`.env` に重要なシークレットを置かないことを推奨します。
- AI 呼び出し
  - OpenAI の呼び出しはコストとレート制限に注意。news_nlp/regime_detector はリトライやフォールバック（API失敗時は中立値採用）を実装していますが、運用設計で呼び出し頻度を管理してください。
- フェイルセーフ
  - 多くの部分で「フェイルオープン/フォールバック」を取り入れており、API 失敗時に例外を上位に伝播させず運用継続する設計です。ただし異常積み重ねによる運用リスクは監視してください。
- ロギング & アラート
  - LOG_LEVEL を適切に設定し、AlertManager（LINE）を設定しておくと早期検知に役立ちます。

---

この README はコードベースの主要な使い方と設計上のポイントをまとめたものです。実装の詳細や拡張、テスト方法は各モジュール内の docstring やコメントを参照してください。必要であればサンプル .env.example や起動スクリプトのユーティリティ（systemd ユニット等）も追記できます。