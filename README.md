# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋実行スクリプト群）。

このリポジトリはトレーディングの実行エンジン、監視・アラート基盤、ポートフォリオ構築、リサーチ（ファクター計算）や AI ベースのニュースセンチメント評価などを含むモジュール群で構成されています。設計上、DB（SQLite / DuckDB）や外部 API（kabuステーション / OpenAI / J-Quants / LINE）との疎結合を保ち、テストしやすく、Paper Trading（完全分離）での検証も容易に行えるようになっています。

## 主な特徴
- ExecutionEngine（注文作成・送信、リスク管理、Reconciliation）
- Monitoring（システム状態、注文滞留、約定異常、ドローダウン監視）
- Kill Switch（閾値到達時にフラグファイルを書き停止シグナル）
- AlertManager（LINE Push による通知、クールダウン制御）
- Portfolio construction（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- Research（DuckDB を用いたファクター計算、将来リターン、IC 計算）
- AI モジュール（ニュース NLP による銘柄別スコアリング、レジーム判定）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 用の検証レポート生成スクリプト

---

## 必要条件（例）
- Python 3.9+
- pip
- OS: Linux / macOS / Windows（大部分はクロスプラットフォーム）

主な Python ライブラリ（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

必要に応じてプロジェクト独自の requirements.txt を作成して管理してください。

---

## 環境変数（主要）
アプリは .env / .env.local / OS 環境変数から設定を読み込みます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主要な環境変数:

- KABUSYS_ENV: 起動環境（development | paper_trading | live）  
  - paper_trading の場合、Execution は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を有効にする場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定だと送信はスキップ）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス（デフォルト data 以下）

簡単な .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（クイック）
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存関係インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install duckdb psutil requests openai streamlit
   ```

3. data ディレクトリを作成
   ```bash
   mkdir -p data
   ```

4. 環境変数を .env に設定（上の例を参照）

注: monitoring 用 DB / テーブルはスクリプト起動時に自動で初期化されます（init_monitoring_db が冪等で実行されます）。

---

## 使い方（主要スクリプト）

- 監視プロセスを起動（Monitoring）
  - デフォルトでは本番用 sqlite_path（KABUSYS_ENV にかかわらず Settings.sqlite_path）を使用して監視ログを記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、1以上）。
  ```bash
  # パッケージモードで起動
  python -m kabusys.run_monitoring
  ```
  - 停止: プロセスを停止するか、プロジェクトルート下の data/stop_requested.flag を作成するとループが終了します。

- 実行エンジンを起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading 用 DB（data/paper_trading.db）に完全分離して記録します。
  - stop フラグ（data/stop_requested.flag）を検知すると安全停止します。
  ```bash
  # 通常起動
  python -m kabusys.run_execution

  # Paper Trading モード例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Streamlit 監視ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - DB を読み取り専用で開く（存在しない場合はエラー表示）

- Paper Trading 検証レポート
  - Paper Trading DB（data/paper_trading.db）から各種指標を集計して標準出力にレポートを出します。
  ```bash
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（env: OPENAI_API_KEY または引数で渡す）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news を呼び出します（DuckDB 接続 + target_date を渡す）
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼び出します

---

## 停止 / 強制停止フロー（フラグファイル）
- data/stop_requested.flag: run_monitoring / run_execution が監視する停止フラグ（存在すると速やかに終了）
- data/kill.flag: KillSwitch によって書き込まれる停止シグナル（ExecutionEngine 停止要求）。KillSwitch はドローダウンやポジション上限を検出したときに書き込みます。
- data/execution.pid: ExecutionEngine の PID。SystemMonitor はこの PID の存在とプロセス生存確認でプロセス状態を判定します。

---

## 設計上の注意点 / 実装上の振る舞い
- .env の自動ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します（CWD に依存しない）。
  - 自動ロードは OS 環境変数を保護しつつ .env/.env.local を読み込みます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Monitoring（監視）は常に Settings.sqlite_path（本番監視 DB）を使用します。Execution は KABUSYS_ENV に応じて paper / live を切り替えます。
- Paper Trading:
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant / partial / never / reject）。
  - PAPER_TRADING_SQLITE_PATH で paper_trading DB を指定可能。
- Process priority / CPU affinity:
  - run_monitoring / run_execution 起動時にプロセス優先度を "high" に設定しようとします（psutil を使用、権限や OS により失敗することがありますが無害にスキップされます）。
- DB 初期化 / マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と簡単なマイグレーション（カラム追加）を行います（冪等）。
- AI 呼び出し時の堅牢性:
  - OpenAI 呼び出しはレート制限 / 5xx / ネットワーク切断に対して指数バックオフでリトライします。API 失敗時には安全にフォールバック（スコア=0 など）して継続する設計です。

---

## ディレクトリ構成（抜粋）
（src/kabusys 以下が主要なパッケージ。実ファイル名はリポジトリ内のファイルに対応）

- src/kabusys/
  - __init__.py                    — パッケージ定義（バージョン等）
  - config.py                      — 環境変数 / Settings 管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                  — ニュース NLG スコアリング / OpenAI 呼び出し
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py             — SQLite 永続化レイヤ（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py            — システム状態・データ鮮度チェック
    - trade_monitor.py             — 注文滞留 / 約定異常チェック
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — フラグ書き込みによる停止（Kill Switch）
    - alert_manager.py             — LINE Push 通知
    - monitoring_engine.py         — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py             — 注文作成・状態管理
    - reconciler.py                — 起動時のリコンシリエーション
    - (その他 broker_factory, order_repository 等)
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 発注株数算出（ロット丸め、リスク制限）
    - risk_adjustment.py           — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py           — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
  - data/                           — 実行時に使うファイルを置く想定（自動作成）
    - monitoring.db (default)      — SQLite（監視）
    - paper_trading.db (default)   — Paper Trading の SQLite（paper_trading 環境）
    - kabusys.duckdb (default)     — DuckDB ファイル
    - execution.pid / stop_requested.flag / kill.flag — 制御フラグ / PID ファイル

---

## よくある運用フロー（例）
- 開発環境立ち上げ
  1. .env を作成して最低限のキー（KABU_API_PASSWORD / JQUANTS_REFRESH_TOKEN）を設定
  2. DuckDB / SQLite（data 以下）を用意（初回は空ファイルで OK）
  3. 実行:
     - 監視: python -m kabusys.run_monitoring
     - 実行エンジン（Paper）: export KABUSYS_ENV=paper_trading; python -m kabusys.run_execution
     - ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading の検証
  1. KABUSYS_ENV=paper_trading で実行エンジンを走らせ、シミュレーションを行う
  2. 実行後、paper_verification_report を用いて期間指定でレポート生成

---

## 補足 / 開発メモ
- 各モジュールは外部依存（API クライアント等）をインタフェース化しており、ユニットテストではモック差替えがしやすく作られています。
- DuckDB を利用したリサーチコードは、prices_daily / raw_financials / raw_news 等のテーブル構造に依存しています。実データをロードしてから利用してください。
- セキュリティ: 実稼働時は API トークン等を安全に管理してください（.env は git 管理しない等）。

---

README に書かれていない内部実装や追加の運用手順が必要であれば、使いたい機能（例: ExecutionEngine の設定項目、Broker の切り替え方法、DB スキーマ詳細など）を教えてください。必要に応じて追記・テンプレートや運用チェックリストを作成します。