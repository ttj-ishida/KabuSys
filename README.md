# KabuSys

日本株向け自動売買システムの一部（ライブラリ／ランタイムスクリプト群）です。本リポジトリは以下の主要機能を含みます: モニタリング（監視）/ 実行エンジン起動・リコンシリエーション / ポートフォリオ構築ユーティリティ / ファクター計算・リサーチ / ニュースNLP・レジーム判定 / 各種ツール。

※ この README はソースツリー（src/kabusys 以下）に含まれるモジュールに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能を提供します。

- 実行系（ExecutionEngine）起動スクリプト（本番／Paper Trading 切替）
- システム監視（CPU/メモリ/ディスク/プロセス/データ鮮度）とリスク監視（ドローダウン・ポジション上限）
- 監視ログ永続化（SQLite）とダッシュボード（Streamlit）
- 注文滞留・約定異常の検出・アラート（LINE Push）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・位置サイズ計算・セクター制限）
- ファクター計算 / 特徴量探索（DuckDB を用いた prices_daily / raw_financials 参照）
- ニュースNLP による銘柄センチメント取得（OpenAI API 経由）および市場レジーム判定
- Paper Trading 検証レポート生成ツール

---

## 主な機能一覧

- run_monitoring.py
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定（デフォルト 60 秒）
- run_execution.py
  - ExecutionEngine を起動し発注処理を実行
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- monitoring
  - MonitoringDB: SQLite スキーマ初期化・読み書き
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine
  - Streamlit ダッシュボード（監視状況の可視化）
- portfolio
  - 候補選定、重み計算、位置サイズ計算、セクター上限・レジーム乗数などの純関数実装
- research
  - ファクター（momentum, volatility, value）計算、将来リターン・IC・統計サマリー
- ai
  - news_nlp: raw_news を集約して OpenAI に投げ、ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を作成
- tools
  - paper_verification_report: Paper Trading DB を対象に稼働率 / 注文成功率 / レイテンシ等を出力

---

## 依存パッケージ（例）

本コードで利用されている外部ライブラリ（最低限）：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. レポジトリをクローンしてプロジェクトルートへ移動  
   （ソースは src/ 配下にあります）

2. 仮想環境作成・有効化、依存ライブラリをインストール

3. 環境変数設定
   - 必須（実行時に ValueError を投げるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合
     - OPENAI_API_KEY
   - 任意/デフォルト値あり
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant|partial|never|reject) — デフォルト: instant
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - MONITOR_POLL_INTERVAL （監視ポーリング間隔秒数、デフォルト 60）

   環境変数はプロジェクトルートの .env / .env.local を自動ロードします（OS環境変数が優先）。
   自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. SQLite / DuckDB の初期化  
   - 監視用 DB スキーマはスクリプト内の init_monitoring_db() が実行時に自動で作成／マイグレーションを行います。通常は初回起動時に自動作成されます。

---

## 使い方（起動 / コマンド例）

注意: ソースツリーを直接実行する場合、PYTHONPATH に src を追加して実行してください（パッケージとしてインストールしている場合は不要）。

UNIX/macOS の例:

- Monitoring（監視ループ）を起動

  ```bash
  # プロジェクトルートから
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```

  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を秒で上書き可能（例: 30 秒）
    ```bash
    MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
    ```

- Execution（注文実行エンジン）を起動

  ```bash
  PYTHONPATH=src python -m kabusys.run_execution
  ```

  - Paper Trading（モックブローカー）で実行する場合
    ```bash
    KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
    ```
    この場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）が使用され、本番の monitoring DB と分離されます。

- Streamlit ダッシュボード（監視 UI）

  ```bash
  # 監視 DB を読み取り専用で開く
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成ツール

  ```bash
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report
  # 期間を指定
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DBパスを直接指定
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（スコア生成 / レジーム判定）はそれぞれ kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す形で利用できます（OPENAI_API_KEY 必須）。

---

## 重要な挙動・注意点

- .env の自動読み込み  
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から `.env` と `.env.local` を読み込みます。OS 環境変数が優先されます。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- Paper Trading の分離  
  - `KABUSYS_ENV=paper_trading` の場合、実行スクリプトは MockBrokerClient を用い、paper_trading 用の SQLite（デフォルト data/paper_trading.db）に発注記録を残します。実運用 DB と分離されるため安全に検証可能です。

- OpenAI API 利用時のリトライとフェイルセーフ  
  - news_nlp / regime_detector はリトライ・バックオフや不正レスポンス時のフォールバック（スコア 0.0 等）を実装しており、API エラーでもシステムが致命的に停止しないよう設計されています。とはいえ API キーは必須です（例外を投げる箇所あり）。

- モニタリング DB のマイグレーションは init_monitoring_db() により起動時に行われます（新しいカラム追加等の簡易移行対応あり）。

- プロセス優先度設定  
  - run_monitoring / run_execution は起動時に set_process_priority("high") を試みます。権限によっては警告が出ることがあります。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／ディレクトリ（本 README 作成時点の抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 execution 関連モジュール)
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
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - (その他、data/ や strategy/ 等の参照があり得ます)

---

## 設定項目（Settings クラスからの主な取得項目）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — AI 機能の利用に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）を有効にする場合に必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（本番）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant|partial|never|reject（デフォルト: instant）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）

---

## 開発・デバッグのヒント

- ローカルでモジュールを直接実行する場合、`PYTHONPATH=src` を付与してモジュールとして実行すると import パスが通ります。
- Streamlit はデバッグ時に便利な UI を提供します。監視 DB が存在しない場合には「Start MonitoringEngine first.」のようなエラー表示になります。
- news_nlp / regime_detector の OpenAI 呼び出しは _call_openai_api を内部で定義しており、ユニットテスト時はその関数を patch/mocking して外部 API を差し替えられます。
- DB スキーマやマイグレーションは monitoring_db.init_monitoring_db() によって保証されます。既存 DB に対するカラム追加の互換性処理も含まれています。

---

## ライセンス / 貢献

（ここにライセンスや貢献方法を記載してください。リポジトリ固有の情報があれば追記してください。）

---

README に記載したコマンドや設定はソースコードの挙動に基づいており、実行環境や追加パッケージにより微調整が必要です。必要であれば各モジュールの使い方（API）や実行時ログの読み方、よくあるトラブルシューティングを別途追記します。