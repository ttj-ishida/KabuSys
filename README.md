# KabuSys

日本株向け自動売買システムのコアライブラリ群（ポートフォリオ構築、発注管理、監視、リサーチ、AI ニュースセンチメント等）。この README はソースツリー（src/kabusys 以下）に含まれる主要モジュールの使い方・セットアップ・構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群です。

- 株価データに基づくファクター計算 / リサーチ（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み計算、リスク調整、株数計算）
- 注文管理 / 発注エンジン（ブローカー抽象化、リコンシリエーション）
- 監視（プロセス・資源・注文滞留・リスク）とアラート送信（LINE）
- Paper Trading 用の分離 DB と検証レポート生成ツール
- LLM を用いたニュースセンチメント（OpenAI）および市場レジーム判定

設計方針は「テスト容易性」「ルックアヘッドバイアス回避」「クラッシュ耐性（冪等・二相永続化など）」を重視しています。

---

## 主な機能一覧

- portfolio
  - 銘柄候補選定（score / rank）
  - 等金額・スコア加重の重み計算
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（ロット丸め・aggregate cap）
- execution
  - OrderManager、OrderRepository、ExecutionEngine（起動スクリプトあり）
  - Reconciler（起動時の自動復旧）
  - ブローカー抽象化（本番／モックの切替）
- monitoring
  - SystemMonitor（CPU/MEM/DISK、プロセス・データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルで実行エンジン停止指示）
  - AlertManager（LINE へのプッシュ通知・クールダウン管理）
  - Streamlit ダッシュボード（監視 UI）
- research
  - ファクター計算（Momentum, Volatility, Value）
  - 特徴量探索（将来リターン計算、IC、統計サマリ）
- ai
  - ニュース NLP スコアリング（OpenAI）
  - レジーム検出（ETF MA + マクロニュースの LLM 合成）
- tools
  - Paper Trading 検証レポート生成スクリプト

---

## 動作要件（推奨）

- Python 3.10+
- ライブラリ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は組み込みのため追加不要

（プロジェクトの requirements.txt があればそちらを利用してください）

例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存をインストール
3. 環境変数を設定（.env / .env.local を使用可能）
   - 自動ロードは Settings モジュールがプロジェクトルート（.git または pyproject.toml）を検出した場合に行われます
   - 自動ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. 必要な外部 API キーを設定（OpenAI 等）
5. データフォルダを作成（デフォルトの DB パスは data/ 以下）

例（簡易）:
```bash
export KABUSYS_ENV=development
export OPENAI_API_KEY="sk-..."
export KABU_API_PASSWORD="..."
# あるいは .env/.env.local に記述
```

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用） — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: paper_trading の MockBroker fill モード — instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番ブローカー利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス — デフォルト: data/execution.pid
- KILL_FLAG_PATH: KillSwitch が作るフラグ — デフォルト: data/kill.flag
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

Settings モジュールは .env/.env.local を自動ロードし、OS 環境変数より優先度の低い値を補完します（.env.local は .env を上書き）。

---

## 使い方

以下はよく使う実行例です。各コマンドはプロジェクトルートから実行します。

- ExecutionEngine を起動（本番／paper_trading 切替）
  - 本番（live）
    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - Paper Trading（モックブローカー／DB 分離）
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 注意: paper_trading の場合、MockBrokerClient が使われ `PAPER_TRADING_SQLITE_PATH` にデータを記録します（本番 DB と完全に分離）。

- Monitoring（SystemMonitor 単体起動）
  - 監視プロセスの起動（デフォルトで sqlite_path を使用、MONITOR_POLL_INTERVAL で間隔変更可）
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 補足: run_monitoring は Monitoring 用に常に本番の sqlite_path（Settings.sqlite_path）を使います。環境に関わらず同一監視 DB を参照する設計です。

- Streamlit ダッシュボード（監視 UI）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を read-only で開きます。MonitoringEngine を先に起動してデータを生成してください。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI（ニューススコアリング / レジーム判定）
  - プログラム内から呼び出す:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を設定）

- テスト用に MonitoringEngine を単発実行（プログラムで）
  - MonitoringEngine.run_once() を呼んで単一サイクルだけ実行可能（ユニットテスト向け）

---

## 重要な挙動・注意点

- プロセス優先度
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足などで失敗する場合は警告を出してスキップします。
- Kill Switch
  - RiskMonitor が閾値（ドローダウン等）を超えると KillSwitch が `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側はこのフラグを検出して安全に停止する想定です。
- DB の分離
  - Paper Trading（KABUSYS_ENV=paper_trading）時は発注系データを `PAPER_TRADING_SQLITE_PATH` に記録して本番 DB から完全に分離します。
  - MonitoringDB は init_monitoring_db により必要テーブルを冪等に作成します。スキーママイグレーション（列追加など）もコード内で扱っています。
- LLM 呼び出しのロバストネス
  - ai モジュール（news_nlp / regime_detector）は API エラーや JSON 解析エラーに対してフェイルセーフ（フォールバック値、リトライ、部分失敗保護）を実装しています。
- Settings の .env 自動ロード
  - 優先順位: OS 環境変数 > .env.local > .env
  - プロジェクトルートが判定できない場合は自動ロードをスキップします
  - 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュール（本 README の対象になっているソース）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
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
      - （ブローカー・エンジン・リポジトリ等は別ファイル群）
    - utils/
      - __init__.py
      - process_priority.py
    - research、data、execution などの他モジュールが存在します（ここに示した以外にも機能が含まれます）

（上記はソースコードの主要なファイルを抜粋したものです。実際のリポジトリ構成はさらに細分化されています）

---

## 開発上のヒント

- ユニットテストを行う際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境依存読み込みを制御すると便利です。
- DuckDB/SQLite に対する読み取り専用アクセスを行う場合、streamlit 等は URI に `?mode=ro` を付与して開く実装例があります。
- OpenAI を使う機能はネットワークに依存するため、ユニットテストでは API 呼び出しをモックしてください（コード内にモック差替えを想定した関数分離があります）。

---

この README は現在のソース（src/kabusys 以下）に基づく概要です。運用や拡張の際は各モジュールの docstring / ソースコメントを参照してください。追加で README に含めたい情報（例: 詳細な .env.example、デプロイ手順、systemd ユニット例、テスト手順など）があれば指定してください。