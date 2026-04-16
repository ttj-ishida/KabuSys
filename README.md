# KabuSys

日本株自動売買システムのモジュール群。戦略・ポートフォリオ構築、発注エンジン、監視、リサーチ、AI（ニュースセンチメント／レジーム判定）などを含むモノレポ風のコードベースです。

以下はこのリポジトリの概要、主要機能、セットアップ方法、実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムを目指したライブラリ群です。設計上のポイント：

- 戦略算出（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、ウェイト計算、ポジションサイズ）
- 発注実行基盤（ExecutionEngine、OrderManager、Reconciler 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、LINE通知、ストリームリット ダッシュボード）
- Paper Trading サポート（本番 DB と分離された専用 SQLite）
- AI モジュール（OpenAI を利用したニュースセンチメント / レジーム判定）
- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等）

設計方針として「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的」「フェイルセーフ（API失敗時は安全にフォールバック）」等を重視しています。

---

## 機能一覧

- execution
  - 発注の作成・管理（OrderManager）
  - ブローカー同期・リコンシリエーション（Reconciler）
  - Risk / Circuit breaker 設定（RiskManager 等 — 実装の一部が存在）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留（stale orders）、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み & LINE 通知
  - MonitoringEngine: 各モニタをまとめてポーリング
  - Streamlit ダッシュボード（監視データ可視化）
- portfolio
  - 銘柄候補選定、等金額/スコア加重ウェイト、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン・IC・統計サマリ
- ai
  - ニュース NLP（OpenAI を用いた銘柄毎センチメント -> ai_scores へ書き込み）
  - レジーム判定（MA200 乖離 + マクロセンチメントの合成）
- tools
  - Paper Trading 検証レポート生成スクリプト（performance /稼働率・成功率等の集計）
- utils
  - プロセス優先度 / CPU affinity 設定ユーティリティ 等

---

## セットアップ手順

前提: Python 3.9+（型アノテーションに Union | などを使用しているため 3.9+ を推奨）  

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成と有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows (PowerShell では別コマンド)
   ```

3. 必要パッケージをインストール
   - 主要な依存例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - インストール例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. データディレクトリを作成
   ```
   mkdir -p data
   ```
   デフォルトでは以下のファイルパスを使用します（Settings 参照）:
   - SQLite (monitoring): data/monitoring.db
   - DuckDB: data/kabusys.duckdb
   - Paper Trading SQLite: data/paper_trading.db

5. 環境変数の設定
   - 必須（本番的な機能を使う場合）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）
   - .env / .env.local をプロジェクトルートに置くと自動読み込みされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例 .env（プロジェクトルート）:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=secret
   JQUANTS_REFRESH_TOKEN=...
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

---

## 使い方（代表コマンド）

注意: 開発時にパッケージを編集して実行するには PYTHONPATH を指定するか pip install -e . を行ってください。ソース直下から実行する例を示します。

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading の場合 KABUSYS_ENV=paper_trading にして起動すると MockBrokerClient を使用し、data/paper_trading.db に記録します。
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  または（環境変数を先にエクスポート）
  ```
  export KABUSYS_ENV=paper_trading
  PYTHONPATH=src python -m kabusys.run_execution
  ```

  実行中は data/stop_requested.flag を作成すると安全に停止します（スレッド内で監視して停止処理を行います）。ExecutionEngine の PID は data/execution.pid に書き込まれます。

- 監視ループ（MonitoringEngine / SystemMonitor）を起動
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: 30 秒）
    ```
    MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
    ```
  - 監視プロセスは常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依らず本番 DB を使う仕様に注意）。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に動かしてデータを蓄積してください。

- Paper Trading 検証レポート生成
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB 指定:
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュールの使用（例）
  - ニューススコアリング:
    ```
    # 実行例: Python スクリプト等から呼ぶ
    from kabusys.ai.news_nlp import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 主要設定（Settings の要点）

クラス: kabusys.config.Settings — 環境変数を参照して設定を取得します。主なキーとデフォルト:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - is_paper フラグにより run_execution は専用 paper DB を使用
- SQLITE_PATH: data/monitoring.db（monitoring 用）
- DUCKDB_PATH: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PID_FILE_PATH / KILL_FLAG_PATH：監視・停止フラグのパス
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL: INFO 等
- OPENAI_API_KEY: AI 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用

注意点:
- .env / .env.local がプロジェクトルートにある場合自動で読み込まれます（OS 環境変数を保護）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを停止できます（テスト等で便利）。

---

## 停止・フラグ操作

- run_monitoring.py / run_execution.py はそれぞれ data/stop_requested.flag の存在を監視しています。停止したい場合はそのファイルを作成してください。
- KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START 設定でクリーンアップを行うオプションがあります）。

---

## ディレクトリ構成

以下は src ディレクトリ配下の主要な構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - execution/
      - order_manager.py
      - order_repository.py
      - execution_engine.py
      - reconciler.py
      - broker_factory.py
      - ... (発注関連)
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - utils/
      - process_priority.py
    - data/                    — 実行時に使用する DB / PID / flag など（リポジトリには通常空ディレクトリ）
- data/
  - monitoring.db (default)
  - kabusys.duckdb (default)
  - paper_trading.db (paper trading 用)
  - execution.pid
  - stop_requested.flag
  - kill.flag

---

## 注意事項 / 運用上のメモ

- Monitoring は Settings にかかわらず監視用 sqlite_path を使用する設計です（監視 DB は環境に関係なく本番 DB を参照するため、実行時は配置先に注意してください）。
- Paper Trading モードでは実取引 API を叩かない想定ですが、環境設定を誤ると本番 API を叩く可能性があるため、KABUSYS_ENV の設定には細心の注意を払い、本番環境では十分な監査を行ってください。
- OpenAI の呼び出しは外部 API 呼び出しで課金対象です。API キーの管理・レートコントロール・エラー対処（retry 実装）はコード内で実装済みですが、運用時はコスト管理を行ってください。
- process priority / CPU affinity の設定はプラットフォーム依存です。psutil の権限によっては設定に失敗する場合があります（警告ログが出ますが処理は続行されます）。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等です。既存カラムの判定と追加処理が実装されています。

---

README は以上です。具体的な機能追加や実運用のための runbook（デプロイ、監視アラートの内容、バックアップ手順、DB スキーマバージョニング等）が必要であれば、用途に合わせて追記します。