# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視を行うためのモジュール群です。  
Execution（発注・リスク管理）・Monitoring（監視・アラート）・Research（ファクター計算）・AI（ニュースセンチメント／レジーム判定）などの機能を備え、paper trading と live（本番）を環境に応じて分離して運用できるよう設計されています。

主な設計方針：
- DB は SQLite（監視ログ等）と DuckDB（時系列・ファイナンスデータ）を併用
- paper_trading 実行時は本番 DB と完全分離（data/paper_trading.db を使用）
- 外部 API（kabu/station, J-Quants, OpenAI）や LINE 通知との連携を想定
- 自動化の安全性（リコンシリエーション、kill flag、リスク監視、アラート）を重視

---

## 主な機能一覧

- Execution（発注系）
  - ExecutionEngine（起動・セッション管理）
  - OrderManager（注文状態遷移・送信）
  - RiskManager（ポジション上限、利用率、ドローダウン等）
  - Reconciler（再起動後の自動復旧 / ブローカー突合）
  - BrokerClientFactory による本番 / モック（paper_trading）切替

- Monitoring（監視系）
  - SystemMonitor：プロセス状態 / CPU / メモリ / ディスク / データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウンやポジション上限の監視・ログ
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
  - AlertManager：LINE Push によるアラート送信
  - KillSwitch：flag ファイルで ExecutionEngine を停止させる仕組み
  - Streamlit ダッシュボード（監視結果可視化）

- Research（リサーチ）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分・スコア重み配分
  - セクター制約適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap）

- AI（LLM を用いた処理）
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）でセンチメント化して ai_scores に格納
  - regime_detector.score_regime：ETF MA とマクロニュースの LLM 評価を合成して市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件（開発環境例）

- Python 3.10+
- 外部ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード用)
- SQLite（Python 標準ライブラリで利用可）

インストール例（仮の requirements がない場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

必要な OS 権限：
- プロセス優先度設定や CPU affinity の操作は権限が必要な場合があります。失敗しても警告を出してスキップする実装です。

---

## 環境変数（主なもの）

Settings モジュールは .env / .env.local / OS 環境変数を読み込みます（自動ロードはデフォルト ON）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行する機能により変わります）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必要な機能で）
- KABU_API_PASSWORD — kabuステーション API 用パスワード

その他（代表例）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading のモック約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

.env のパースロジックはシェル風の export プレフィックス、クォート、コメント等に対応しています。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存パッケージをインストール
3. data ディレクトリを作成
   ```bash
   mkdir -p data
   ```
4. .env を作成（.env.example を参考に必要な値を設定）
5. （必要なら）DuckDB や初期データを準備（prices_daily / raw_financials 等は研究・AI 機能で使用）

注: run 系スクリプトは起動時に monitoring DB のテーブル作成（init_monitoring_db）を行います。監視 DB は環境により paper_trading 用と本番とを分離しています。

---

## 使い方（主要コマンド）

パッケージとして実行可能なエントリポイント（各モジュールには main() を持つものがあります）:

- ExecutionEngine（発注処理）
  - 本番 / 開発 / paper_trading の env を切り替え:
    ```bash
    # paper_trading（MockBroker を使用、DB は data/paper_trading.db）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

    # production（KABUSYS_ENV=live）
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 起動時にプロセス優先度を "high" に設定します（失敗しても継続）。

- Monitoring（監視ループ）
  - デフォルト 60 秒間隔でポーリング（環境変数で調整可）
    ```bash
    # 例: ポーリングを 30 秒に設定
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Streamlit ダッシュボード（監視可視化）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  引数 `--db` で監視 DB を指定できます（read-only URI を内部で作成）。

- Paper Trading 検証レポート
  ```bash
  # 全期間
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（プログラムからの利用例）
  - ニューススコアリング（programmatic）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    print(f"scored {n} stocks")
    ```
  - レジーム判定（programmatic）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

注意点：
- OpenAI API 呼び出しは API キー（OPENAI_API_KEY）必須です。未設定だと ValueError を投げます（関数内でチェック）。
- AI 周りはリトライやフェイルセーフ（失敗時 0.0 / スキップ）を実装していますが、API 料金や利用制限に注意してください。

---

## ディレクトリ構成（主要ファイル）

以下はこのリポジトリ内の主要なファイル・モジュール群です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み用 Settings
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング
    - regime_detector.py — 市場レジーム判定（ma200 + macro news）
  - monitoring/
    - monitoring_db.py — SQLite 監視テーブルの初期化 & MonitoringDB ラッパ
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — Monitor を束ねるエンジン
    - alert_manager.py — LINE 通知ラッパー
    - kill_switch.py — kill.flag の制御
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - （※ 他に BrokerFactory、OrderRepository などのモジュールが想定されます）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ （実行時に使用する DB ファイルや状態ファイルを置くディレクトリ）
    - kabusys.duckdb (デフォルト)
    - monitoring.db (監視用 SQLite)
    - paper_trading.db (paper trading 用 SQLite)

（実際のファイル一覧はリポジトリの内容に依存します。上は主要モジュールの要約です。）

---

## 運用上の注意 / FAQ

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
  - OS 環境変数は優先され、.env.local は .env の値を上書きできます。
  - テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading と本番 DB 分離:
  - KABUSYS_ENV=paper_trading の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB に書き込まれないよう分離して運用してください。

- kill.flag / PID:
  - ExecutionEngine の安全停止は kill.flag ファイル（Settings.kill_flag_path、デフォルト data/kill.flag）により行われます。
  - run_monitoring/run_execution は起動時に PID ファイルの管理や kill.flag のクリア（設定次第）を行います。手動で削除する場合は注意して操作してください。

- OpenAI / API 使用:
  - OpenAI に依存する機能は API 使用料・レート制限の影響を受けます。ローカルでのテストはモック化（テスト時に API 呼び出し関数をパッチ）することを推奨します。
  - news_nlp & regime_detector ではリトライ・バックオフ・フェイルセーフ処理を実装していますが、誤用により料金が発生する点に注意してください。

- ログ:
  - 各モジュールは logging を利用しています。LOG_LEVEL 環境変数で制御できます。

---

## 開発 / テストのヒント

- duckdb の接続はファイルパスを指定して行います。データがないと research / AI 機能は None や警告を返します。
- 多くの関数は純粋関数 / 副作用を限定した設計（DB を直接変更しない）になっており、ユニットテストしやすくなっています。API 呼び出し部分はモックしてテスト可能です（例: news_nlp._call_openai_api をパッチ）。
- MonitoringDB.init_monitoring_db は冪等（既存 DB があっても安全）です。マイグレーションも簡易に含まれています（カラム追加等）。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。より詳細な仕様（StrategyModel.md、PortfolioConstruction.md 等）や実運用ルールは別ドキュメントを参照してください。必要があれば、導入手順のスクリプト化や example .env の作成、requirements.txt の整備などもサポートします。