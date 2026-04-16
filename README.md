# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ユーティリティ群をまとめたコードベースです。本リポジトリには実行エンジン、モニタリング、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュース NLP / レジーム判定、運用用ツール類が含まれます。

以下はこのコードベースの概要、主要機能、ローカルセットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

主な目的
- 自動売買（ExecutionEngine）とその安全運転（リスク管理、再同期）
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor）、アラート通知（LINE）
- ポートフォリオ構築、ポジションサイズ計算などの純粋関数群
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）
- OpenAI を用いたニュースのセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）
- 運用／検証ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針（抜粋）
- DB 周りは sqlite（監視用）・DuckDB（時系列・リサーチ用）を使用
- Paper Trading は本番 DB と分離（data/paper_trading.db）
- 環境変数 / .env による設定（.env.local の上書き対応）
- LLM 呼び出しはフェイルセーフ（エラー時はスコア 0 等で継続）
- ルックアヘッドバイアス回避の設計（API 呼び出しや日付参照の扱い）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - BrokerClientFactory による本番／モック切替（KABUSYS_ENV=paper_trading）
  - Reconciler（注文状態・ポジションの突合）
  - OrderManager / OrderRepository（注文管理・永続化）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件により ExecutionEngine に停止シグナル（data/kill.flag）
  - AlertManager: LINE push によるアラート通知
  - MonitoringEngine: 上記モニタの統合ポーリングループ
  - Streamlit ダッシュボード（監視情報の可視化）

- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC 計算、統計サマリ
  - 候補選定・重み計算・ポジションサイズ決定・セクターキャップ・レジーム乗数

- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores に格納
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して market_regime を決定

- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`
  - Streamlit ダッシュボード起動スクリプト

---

## 前提 / 必要パッケージ

（実行環境の Python バージョンは型アノテーションから Python 3.10+ を想定）

必要な主要パッケージ（pip インストール例）
- duckdb
- psutil
- openai
- requests
- streamlit

推奨インストール（仮想環境内で）
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai requests streamlit
```

sqlite3 は標準ライブラリに含まれています。

---

## 設定（環境変数）

- 自動ロード
  - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）
  - 自動読み込みを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 代表的な環境変数（キーとデフォルト / 必須）
  - 必須:
    - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
    - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - 任意 / デフォルトあり:
    - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
    - LOG_LEVEL — ログレベル ("INFO" 等、デフォルト: INFO)
    - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE — paper_trading 時の約定モード ("instant" | "partial" | "never" | "reject")（デフォルト: "instant"）
    - PID_FILE_PATH — execution.pid（デフォルト: data/execution.pid）
    - KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
    - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag をクリアするか（"1" で有効）
    - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（数値）
    - OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）

例（.env）
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順（ローカル開発向け）

1. レポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. `.env` / `.env.local` を作成して必要な環境変数を設定
5. data ディレクトリを作成（初回）
   ```bash
   mkdir -p data
   ```
6. DuckDB / SQLite の初期化は各モジュールが自動で行います（init_monitoring_db が必要テーブルを作成します）。

---

## 使い方（主要コマンド）

- ExecutionEngine（実行エンジン）起動
  - 通常起動（デフォルトの KABUSYS_ENV に従う）
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper Trading（環境変数で切り替え）
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - 実行前に `data/stop_requested.flag` が存在すると起動をスキップします。
    - プロセス優先度を上げる処理が行われます（set_process_priority）。
    - 実行中は `data/execution.pid` に PID が記録されます（監視処理が stale PID を検出すると削除・アラート）。

- Monitoring（監視ループ）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き（デフォルト: 60）
  - 監視は常に production（本番）用 sqlite_path を使用する設計（KABUSYS_ENV に依存せず）

- Streamlit ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - オプション `--from`, `--to`（YYYY-MM-DD）で期間フィルタ、`--db` で database パスを指定可能

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも `OPENAI_API_KEY` の設定が必要（引数で直接渡すことも可能）

---

## 停止・リスタートの操作

- 監視ループ / 実行エンジンの両方は `data/stop_requested.flag` を検知すると安全に終了します。停止させたい場合はこのフラグファイルを作成してください。
- ExecutionEngine に対して強制停止（運用上の停止判断）は `data/kill.flag` に理由テキストを書き込む KillSwitch によって行われます（KillSwitch は条件を満たすと書き込み、ExecutionEngine は起動中にこのフラグを検知して停止します）。
- kill.flag を手動でクリアするにはファイルを削除してください（KillSwitch.clear() も同じ処理）。

---

## データベース（監視用）スキーマ概要

monitoring_db.init_monitoring_db により作成される主要テーブル（冪等）:
- system_status: CPU/メモリ/ディスク/プロセス状態 の履歴
- trade_logs: 注文イベントログ（latency_ms カラムあり）
- positions: 現在の保有ポジション
- risk_logs: リスク関連イベント（重複抑制機能あり）
- dashboard: ダッシュボード集計（単一行 id=1 を保持）
- いくつかのマイグレーション（peak_value や latency_ms カラム追加）を自動適用

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージ情報（バージョン等）
- config.py — 環境変数 / .env 読み込みと Settings クラス（アプリ設定）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py — 注文の外向き API（OrderManager）
  - reconciler.py — 起動時の自動リコンシリエーション
  - （その他 Broker 周り・OrderRepository 等の実装ファイル）
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化層（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - alert_manager.py — LINE Push によるアラート送信
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算（リスクベース / 等分配 等）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum, volatility, value）
  - feature_exploration.py — 将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py — ニュースの LLM センチメントスコアリング（ai_scores へ書込）
  - regime_detector.py — レジーム判定（ma200 + マクロニュース）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他
- data/ — 実行時に生成される SQLite / pid / flag などのファイルを格納する想定ディレクトリ

---

## 開発 / テスト時の注意点

- Settings クラスは環境値の検証を行います（無効な値は例外を出します）。テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動 .env ロードを抑制可能。
- OpenAI を利用するモジュールは、API 呼び出しを簡単にモックできるように内部の API 呼び出し関数を分離しています（ユニットテストで差し替え可能）。
- DuckDB を使ったリサーチ機能は SQL を主体とし、外部 API にはアクセスしない想定になっています（prices_daily / raw_financials だけ参照）。
- monitoring_db.init_monitoring_db は冪等（何度呼んでも安全）であり、既存 DB に対するいくつかのマイグレーション処理も含みます。

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai requests streamlit
  ```

- Execution 起動
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング間隔を 30 秒にする例）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容は主要な使い方・設定・コード構成にフォーカスしています。実運用での接続先ブローカー実装や細かな設定値、セキュリティ（API キー管理）などは別途運用手順書を作成してください。必要であれば README にサンプル .env.example を追記したり、各モジュールの使用例（コードスニペット）を追加します。希望があれば追記します。