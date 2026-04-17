# KabuSys

日本株向けの自動売買・研究・監視フレームワーク（軽量プロトタイプ）

この README はリポジトリ内のコードを基に作成した利用ガイドです。主要な機能、セットアップ、起動方法、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジン、監視基盤、ポートフォリオ構築・リスク計算、リサーチ（ファクター計算）や AI（ニュースセンチメント / レジーム判定）などを含むモジュール群から成るシステムです。  
設計上のポイント：

- 実運用と Paper Trading を環境で切り替え可能（DBも分離）。
- DuckDB を使った時系列ファクター計算／データ分析。
- SQLite を使った軽量な監視ログ・トレードログの永続化。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定（任意）。
- Streamlit ベースの監視ダッシュボードを備える。

README は開発者や運用者向けに起動／監視／簡易操作方法を示します。

---

## 主な機能一覧

- Execution（発注）サブシステム
  - Broker クライアント抽象化 / Mock ブローカーによる Paper Trading
  - OrderManager / ExecutionEngine / Reconciler（再起動時のリコンシリエーション）
  - リスク管理（Rate limit・ポジション上限・ドローダウン等）
- Monitoring（監視）
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・保有数上限監視）
  - KillSwitch（条件に応じて ExecutionEngine を停止するための flag ファイル生成）
  - AlertManager（LINE Push API による通知）
  - Streamlit ダッシュボード（read-only で監視情報表示）
- Portfolio（銘柄選定・重み付け・ポジションサイジング）
  - 候補選定、等金額/スコア重み、リスクベースの株数計算、セクター制限、レジーム乗数
- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（ニュースNLP / レジーム判定）
  - OpenAI を利用したニュースのセンチメント集約と ai_scores への書き込み
  - マクロニュース + ETF MA を合成した市場レジーム判定（market_regime テーブルへの書き込み）
- tools
  - Paper Trading 検証レポート生成スクリプト（過去データから各種指標を集計）

---

## 要求環境 / 事前準備

必須（概略）：

- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
  - その他（SQLite は標準組込）

インストールの例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil requests openai streamlit
```

備考:
- psutil はプロセス優先度や CPU affinity の制御に使用します。権限不足で設定できない場合は警告を出してスキップします。
- OpenAI を利用する機能を使う場合は API キーが必要です（環境変数 / 引数で指定）。

---

## 設定（環境変数）

KabuSys は .env / .env.local / OS 環境変数から設定を自動ロードします（プロジェクトルートが .git または pyproject.toml によって自動検出される場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（代表）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai/news/regime 用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

注意:
- Settings クラスは未設定の必須項目に対して ValueError を投げます。`.env.example` を参考に .env を準備してください（リポジトリに例ファイルがある前提）。

---

## セットアップ手順（要点）

1. リポジトリをクローンし、仮想環境を作成して依存をインストール
2. プロジェクトルートに `.env`（と必要なら `.env.local`）を作成し、必要な環境変数を設定
3. データディレクトリを作成（例: data/）
4. DuckDB / SQLite はデフォルトパス（data/ 以下）を使用するのでパーミッションを確認

例:

```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
mkdir -p data
# .env を作成（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY などを設定）
```

---

## 使い方（主要コマンド）

基本はモジュールを直接実行するか、Streamlit を利用します。

- Monitoring（監視ループ）起動

  MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）。

  ```bash
  python -m kabusys.run_monitoring
  # 例: 30秒間隔
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  停止方法:
  - プロセスに SIGINT（Ctrl+C）
  - またはプロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して終了します。

- ExecutionEngine（発注エンジン）起動

  KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使い、Paper 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。本番環境では通常 `KABUSYS_ENV=live`。

  ```bash
  # Paper trading
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # Live（注意: 実ブローカー接続になる）
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

  停止方法:
  - プロセスに SIGINT（Ctrl+C）
  - data/stop_requested.flag を作成すると起動済みのループが検知して安全に停止します。
  - KillSwitch（監視側）が `data/kill.flag` を書き込むと ExecutionEngine 側で起動時に検知し終了させる仕組みもあります。

- Streamlit ダッシュボード起動（監視 DB を read-only で開く）

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート（tools）

  data/paper_trading.db または別パスの DB を指定して検証レポートを生成します。

  ```bash
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report

  # 期間を指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / News scoring, Regime scoring（プログラム的呼び出し）
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)

  これらは OpenAI API キー（OPENAI_API_KEY）を設定して呼び出してください。エラー時はフェイルセーフ（スコア 0 等）で継続する実装です。

---

## 実運用上の注意点

- Paper Trading は本番 DB と物理的に分離（PAPER_TRADING_SQLITE_PATH）されています。Paper 実行時に本番 DB を誤って上書かないよう注意してください。
- Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使います（コメントにある通り KABUSYS_ENV に依存せず本番 path を見る実装）。
- KillSwitch は条件に応じて `data/kill.flag` に理由を書き込みます。ExecutionEngine 起動時にこのファイルがあると起動しないため、起動前にクリアする必要があります。KillSwitch.clear() が提供されています（通常は手動で削除）。
- OpenAI を使う機能は API キーが無いとエラーになります。API 呼び出しは 429 / 一時エラー / 5xx に対して指数バックオフでリトライする設計になっていますが、料金とレート制限に注意してください。

---

## 主要ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイル・ディレクトリの概観です。

```
src/kabusys/
├─ __init__.py
├─ config.py                     # 環境変数・設定管理
├─ run_monitoring.py             # SystemMonitor ポーリングループ起動
├─ run_execution.py              # ExecutionEngine 起動スクリプト
├─ tools/
│  ├─ __init__.py
│  └─ paper_verification_report.py
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ monitoring/
│  ├─ __init__.py
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  ├─ alert_manager.py
│  ├─ monitoring_engine.py
│  └─ streamlit_dashboard.py
├─ execution/
│  ├─ order_manager.py
│  ├─ reconciler.py
│  └─ (その他: broker_factory, execution_engine, order_repository 等)
├─ utils/
│  ├─ __init__.py
│  └─ process_priority.py
└─ data/                          # 実行時に利用されるデフォルトの DB / flag ファイル
   ├─ monitoring.db               # monitoring 用 SQLite（デフォルト）
   ├─ paper_trading.db            # paper trading 用 SQLite（デフォルト）
   ├─ kabusys.duckdb              # DuckDB（デフォルト: data/kabusys.duckdb）
   ├─ execution.pid               # PID ファイル（ExecutionEngine）
   ├─ kill.flag                   # KillSwitch が書き込むファイル
   └─ stop_requested.flag         # 起動スクリプトが監視する停止フラグ
```

---

## 開発者向け補足

- Settings は .env（と .env.local）をプロジェクトルートから自動読み込みします。自動ロードを一時的に無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で便利です）。
- モジュールはできるだけ純粋関数／副作用最小に設計されています（portfolio / research 等は DB を参照しない純粋関数群が多い）。
- DuckDB 接続を受け取り SQL を直接実行する実装方針が採られているため、テーブルスキーマ（prices_daily / raw_financials 等）に注意してください。
- 監視用 DB 初期化は init_monitoring_db() で行います（冪等）。

---

## トラブルシューティング（よくある項目）

- 認証 / 環境変数エラー
  - Settings の必須項目が空だと起動時に ValueError を投げます。.env を再確認してください。
- OpenAI が使えない
  - OPENAI_API_KEY を設定し、ネットワーク接続・レート制限・課金状況を確認してください。API 呼び出し失敗時は一部機能がデグレードしますがシステム全体は継続する設計です。
- psutil による優先度設定で権限エラー
  - 権限が低い環境だとプロセス優先度設定が失敗します（警告が出ます）。この場合はスキップされますが動作自体には影響しません。
- DB ファイルのロック/排他
  - Streamlit から SQLite に読み取り専用で接続する際は URI モード（?mode=ro）で開く例を streamlit_dashboard.py が示しています。書き込み中のアクセスは注意してください。

---

以上がコードベースに基づく README.md です。必要であれば、.env.example の具体例、requirements.txt、起動スクリプトの systemd サービス定義例、または主要 API（関数）一覧を追加できます。どの情報がさらに欲しいか教えてください。