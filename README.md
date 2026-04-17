# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋実行スクリプト）。  
このリポジトリは、取引実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ/ファクター計算、AI を使ったニューススコアリング等の機能を含みます。

---

## プロジェクト概要

KabuSys は次を目的としたコンポーネント群です。

- 取引シグナルに基づく自動発注（ExecutionEngine）
- 発注・約定の記録とリスク管理（OrderRepository / RiskManager）
- システム稼働状態・注文異常の常時監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター調整）
- DuckDB を使った時系列データ処理・ファクター算出（research モジュール）
- OpenAI を使ったニュースセンチメント評価・市場レジーム判定（ai モジュール）
- Paper Trading 向けの分離された DB と検証用ユーティリティ

---

## 主な機能一覧

- Execution
  - 実際のブローカーまたは Paper Trading（モック）での発注実行
  - 再起動時のリコンシリエーション（Reconciler）
  - 注文状態遷移を管理する OrderManager / OrderRepository
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）監視
  - データ鮮度チェック（DuckDB の prices_daily）
  - 注文滞留や異常約定価格の検出
  - ダッシュボード用の SQLite 永続化（monitoring.db）
  - LINE 通知（AlertManager）やキルスイッチ（kill.flag）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（純粋関数）
  - 候補選定・等重／スコア重み・リスクベースのポジションサイズ計算
  - セクター上限・レジーム乗数の適用
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続ベース）
  - 将来リターン・IC・統計サマリー等の分析ユーティリティ
- AI
  - ニュースを OpenAI に渡して銘柄単位のセンチメント（ai_scores）を作成
  - ETF（1321）MA とマクロニュースを合成した市場レジーム判定
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - .env 読み込みロジック（自動ロード / .env.local 優先等）

---

## 前提・依存

- Python 3.10+
  - 型注釈で `X | None` 等を使用しているため 3.10 以上を推奨
- 必要なライブラリ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ）
- （任意）仮想環境の利用を推奨

例: 必要パッケージのインストール（requirements.txt がある場合はそちらを使用）
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
# または
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動
2. 仮想環境を作成して有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルトで自動ロード有効）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. 重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
   - KABUSYS_ENV: environment — `development` / `paper_trading` / `live`（デフォルト: development）
     - `paper_trading` の場合、MockBroker を使い DB は data/paper_trading.db に記録されます（本番 DB と分離）
   - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - LOG_LEVEL: DEBUG/INFO/...
   - その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値 など

6. データディレクトリの作成
```
mkdir -p data
```
（実行スクリプトは必要に応じてファイルを作成します）

---

## 使い方

以下は主な実行方法の例です。プロジェクトルートで実行してください。

- ExecutionEngine を起動（ブローカーに接続して取引を行う）
  - 本番 / 開発 / paper_trading は環境変数 KABUSYS_ENV で切り替え
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 注意:
    - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限が必要な場合あり）。
    - Paper trading の場合、`PAPER_TRADING_SQLITE_PATH` で指定した DB に記録され、本番DBとは分離されます。
    - 停止はプロセス終了、あるいは監視側から kill.flag を書くことで行います（下記参照）。

- Monitoring を起動（ポーリングループ）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。不正値はデフォルトにフォールバックします。
  - 動作:
    - sqlite（monitoring DB）に system_status / trade_logs / risk_logs / positions / dashboard を記録します。
    - duckdb（時系列データ）を参照してデータ鮮度チェックを行います。
    - data/stop_requested.flag を置くとモニタが検知してループを終了します。

- 監視ダッシュボード（Streamlit）
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で SQLite を開きます。MonitoringEngine が先に動いている必要があります。

- Paper Trading 検証レポート生成
  - コマンド:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - --db PATH: SQLite DB パス（省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
    - 期間フィルタを指定すると該当期間の集計を行います。

- AI モジュール（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡すと ai_scores テーブルへ書き込みます。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡すと market_regime テーブルへ書き込みます。
  - 両者とも API キーが引数で渡されない場合は環境変数 OPENAI_API_KEY を参照します。
  - 実行例（Python REPL 内）:
    ```py
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```

- キルスイッチ / 停止フラグ
  - kill.flag:
    - KillSwitch は条件成立時に `data/kill.flag` に理由を書き込み、ExecutionEngine 側で停止を促します。
    - KillSwitch を手動で発動する場合は同形式でファイルを書き込めば良いです（Monitoring の KillSwitch は Settings.kill_flag_path を使います）。
  - stop flag:
    - run_monitoring/run_execution はそれぞれ `data/stop_requested.flag` を監視しています。ファイルを置くと安全に終了します。
  - clear:
    - KillSwitch.clear() で kill.flag を削除できます。起動時に自動でクリアする設定（KILL_FLAG_CLEAR_ON_START）があります。

---

## 設計上の注意・運用メモ

- 環境ごとの DB 分離
  - KABUSYS_ENV=`paper_trading` の場合、paper_trading 用の SQLite を使用して本番 DB と完全分離します。
- .env 読み込み
  - プロジェクトルートの `.env` と `.env.local` を自動ロードします（OS 環境変数が優先されます）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- プロセス優先度 / CPU affinity
  - 起動時に `set_process_priority("high")` を呼びます。権限不足や未サポート OS の場合は警告を出してスキップします。
- DuckDB / SQLite スキーマは実行時に自動で初期化・マイグレーションされます（init_monitoring_db）。
- OpenAI の呼び出しは冪等性 / フェイルセーフを考慮して実装されています（429/5xx のリトライや失敗時のフォールバック）。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要ファイルと役割の簡易ツリーです。

- src/
  - kabusys/
    - __init__.py              — パッケージ宣言
    - config.py                — 環境変数 / Settings 管理
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み付け
      - position_sizing.py     — 株数決定・投資上限・単元丸め
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py     — Momentum/Volatility/Value 等の計算
      - feature_exploration.py — 将来リターン・IC・統計
    - ai/
      - news_nlp.py            — ニュース→LLM→ai_scores 更新
      - regime_detector.py     — レジーム判定・market_regime 書き込み
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ
      - system_monitor.py      — CPU/Mem/Disk・データ鮮度・PID チェック
      - trade_monitor.py       — 注文滞留・約定異常チェック
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag 管理
      - alert_manager.py       — LINE 通知ラッパー
      - monitoring_engine.py   — 複数モニタの統括
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ... （ブローカーファクトリ・エンジン等）
    - utils/
      - process_priority.py    — psutil ベースの優先度/affinity ユーティリティ
    - data/                     — 実行時に使用するファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag など）

---

## トラブルシューティング

- psutil AccessDenied / affinity 設定が失敗する場合:
  - root 権限または適切な権限が必要です。許可がない場合は警告が出てスキップします。
- OpenAI API 呼び出しでエラーが出る場合:
  - OPENAI_API_KEY の確認、レート制限、ネットワーク状態を確認してください。ai モジュールは一部エラーを許容してフォールバックする実装です。
- monitoring.db が見つからない場合:
  - MonitoringEngine を起動していないと Streamlit が読み込めません。run_monitoring を先に起動してください。

---

## ライセンス / 貢献

この README はコードベースから生成された説明です。実運用・配布の際はライセンス表記やセキュリティポリシーを別途整備してください。バグ報告や機能提案は Issue / PR をお願いします。

---

必要であれば、README にサンプル .env.example や requirements.txt の雛形、簡単なコマンド一覧（systemd ユニット例等）を追記します。どの追加情報がほしいか教えてください。