# KabuSys

日本株向けの自動売買システム（ライブラリ＋稼働用スクリプト群）

このリポジトリは、シグナル処理・ポートフォリオ構築・発注管理・監視・研究用ファクター計算・AI を用いたニューススコアリングなどを含むモジュール群です。実行環境の分離（本番 / paper_trading）や監視・アラート機能も備えています。

---

## 主要な特徴（抜粋）

- Execution 部分
  - 発注状態遷移管理（OrderManager, Reconciler）
  - ブローカークライアントを抽象化する Factory（BrokerClientFactory）
  - Paper Trading モードで本番 DB と分離（data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - MonitoringDB（SQLite）へログ永続化
  - KillSwitch による停止フラグ書き込み
  - AlertManager による LINE プッシュ通知（オプション）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定 / 等分配・スコア加重配分 / リスク調整 / ポジションサイズ計算
- リサーチ（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリ
- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai.news_nlp）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（ai.regime_detector）
  - OpenAI API 呼び出しは堅牢にリトライ・検証を行う
- ツール
  - Paper Trading 検証レポート出力スクリプト（kabusys.tools.paper_verification_report）

---

## 前提 / 必要な依存パッケージ（例）

- Python 3.9+（コードは型注釈や pathlib 等を利用）
- duckdb
- psutil
- requests
- openai（AI 機能を利用する場合）
- streamlit（ダッシュボードを使う場合）

pip でインストールする例:
```
pip install duckdb psutil requests openai streamlit
```

（実際の requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数（主なもの）

Settings クラスで利用される主要な環境変数とデフォルト:

- KABUSYS_ENV: 起動環境（"development" / "paper_trading" / "live"）。デフォルト: development
- SQLITE_PATH: 監視用 SQLite（monitoring）パス。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading）パス。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")。デフォルト: "instant"
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス。デフォルト: data/execution.pid
- KILL_FLAG_PATH: KillSwitch のフラグパス。デフォルト: data/kill.flag
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視の閾値
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）デフォルト: INFO
- OPENAI_API_KEY: OpenAI を使う機能で必要（ai.score_news / score_regime）

自動 .env ロード:
- プロジェクトルートにある `.env` / `.env.local` を自動読み込みします（OS 環境変数優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

監視ポーリング間隔:
- MONITOR_POLL_INTERVAL: run_monitoring 実行時のポーリング間隔（秒）。デフォルト 60 秒。
  - 1 未満の値は無効と見なされデフォルトにフォールバックします。

---

## セットアップ手順（ローカルでの簡易手順）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存をインストール
   ```
   pip install -r requirements.txt  # あれば
   # または最低限:
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数を用意（.env を作るか OS 環境変数で設定）
   - OpenAI を使う場合:
     ```
     export OPENAI_API_KEY="sk-..."
     ```
   - Paper Trading を使う場合:
     ```
     export KABUSYS_ENV=paper_trading
     # 必要に応じて PAPER_TRADING_SQLITE_PATH や PAPER_FILL_MODE を設定
     ```

4. DB ファイル群はデフォルトで `data/` 配下に作成されます。監視 DB は起動スクリプトが初回で初期化します。

---

## 使い方（代表的なコマンド）

- 監視ループを起動（monitoring 用）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（例: 30 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを残します。

- ExecutionEngine を起動（発注エンジン）:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全に分離）。
  - Execution 起動時に PID ファイルを書きます（Settings.pid_file_path）。

- Streamlit ダッシュボード（監視 UI）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - `--db` オプションで読み込み対象の monitoring DB を指定できます（既定: data/monitoring.db）。read-only URI 経由で開くため MonitoringEngine が動いている必要があります。

- Paper Trading 検証レポート出力:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パス指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` より優先されます。

- AI モジュール（プログラム的に利用）:
  - ニュース NLP（ai.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と API キーを受け取る関数として提供されています。例:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - OpenAI API を使うため `OPENAI_API_KEY` を用意してください。

---

## 注意点 / 実装上のメモ

- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基に .env を自動読み込みします。テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- MonitoringDB の初期化処理（init_monitoring_db）は冪等で、既存スキーマに対する簡単なマイグレーション（カラム追加）も行います。
- Paper Trading モードは本番 DB と完全分離されるように設計されています（`settings.is_paper` を利用して接続先を切り替え）。
- AI 系の呼び出しではレスポンス検証・クリップ・リトライ等の堅牢化が入っていますが、API キー不足や外部サービス障害時はフェイルセーフで処理を続行する設計です（必要に応じてログで確認してください）。
- プロセス優先度設定：起動スクリプトは最初に set_process_priority("high") を試みます。権限がない場合は警告が出るだけで続行します。
- KillSwitch は監視結果から停止要因を判定し、`KILL_FLAG_PATH` に理由を書き込むことで ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側でフラグを監視する実装を想定）。

---

## ディレクトリ構成（概要）

（src/kabusys 以下の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py            # ニュース NLP スコアリング
      - regime_detector.py     # 市場レジーム判定
    - monitoring/
      - __init__.py
      - monitoring_db.py      # SQLite 永続化層（監視ログ）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (broker関連・order_repository等のファイル)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - data/
      - (データパイプライン／DuckDB 関連モジュールが入る想定)
    - utils/
      - process_priority.py
      - __init__.py

上記は主要モジュールの抜粋です。細かな実装ファイルは該当ディレクトリを参照してください。

---

## よくある操作例（まとめ）

- 監視開始:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- Execution 起動（Paper Trading）:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

README に書かれている以外の詳細（内部 API の仕様や追加の実行オプション等）は、各モジュールの docstring を参照してください。必要であれば、各コンポーネントの使い方（ExecutionEngine の設定例、BrokerClient 実装例、DuckDB テーブルスキーマ等）を別途まとめます。