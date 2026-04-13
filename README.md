# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ツール群です。  
本リポジトリは取引実行ロジック、ポートフォリオ構築、リスク管理、監視・アラート、リサーチ用ファクター計算、そして一部AI支援（ニュースセンチメント／レジーム判定）を含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群で構成されています。

- 取引実行（ExecutionEngine / OrderManager / BrokerClient）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- リスク制御（ドローダウン監視・ポジション上限など）
- 監視（システム状態、注文滞留、約定異常の検出）とアラート（LINE通知）
- リサーチ（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメントスコアリング、マーケットレジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

設計方針の一部：
- データアクセスは sqlite（監視ログ等）/ DuckDB（時系列・ファクターデータ）を使用
- 環境による挙動切替（development / paper_trading / live）
- Paper Trading は本番DBと完全分離（`data/paper_trading.db`）
- 外部 API 呼び出し（OpenAI 等）は失敗に対してフォールバックするフェイルセーフ設計

---

## 主な機能一覧

- Execution
  - 注文作成・送信・状態同期（OrderManager / Reconciler）
  - 起動時の自動リコンシリエーション（再起動後の整合性回復）
  - Paper Trading モード（MockBrokerClient）対応
- Portfolio
  - シグナルから候補選定（スコア順）
  - 等分配・スコア加重配分
  - ポジションサイズ計算（risk-based / equal / score）
  - セクター上限適用、レジーム乗数
- Monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン／ポジション数監視、kill flag 出力
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores テーブル
  - regime_detector: ma200 とマクロセンチメントの合成によるレジーム判定
- Tools
  - paper_verification_report: Paper Trading データから検証レポート生成

---

## セットアップ手順（ローカル実行向け）

前提
- Python 3.10 以上を推奨（typing の | 演算子を使用）
- SQLite は標準ライブラリ、DuckDB と外部モジュールは pip でインストール

1. リポジトリをクローン、Python 仮想環境を作成・有効化
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストール
   （requirements.txt があればそれを使うか、下記例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   ※ 開発・CI用に pytest などを追加する場合があります。

3. データディレクトリ作成（例）
   ```
   mkdir -p data
   ```

4. 環境変数の設定
   - ルートの `.env` / `.env.local` を用意すると自動ロードされます（既存 OS 環境変数を保護）。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必要なら）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI を使う場合必須
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（paper_trading モード）
     - LOG_LEVEL: DEBUG/INFO/...
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の約定挙動）
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に監視テーブルを冪等で初期化します。特別な初期化コマンドは不要です。

---

## 使い方（起動コマンド・ツール）

- 監視ループ起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で変更できます（デフォルト 60 秒）。
  - 監視は常に本番 SQLite パス（Settings.sqlite_path）を参照します（KABUSYS_ENV に依らず）。

- 実行エンジン起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）へ記録します。
  - 起動時に pid ファイル（Settings.pid_file_path, デフォルト data/execution.pid）を書き、プロセス優先度を高く設定します。
  - `Settings.kill_flag_clear_on_start` が true の場合、起動時に kill flag をクリアします。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を読み取り専用で開きます。MonitoringEngine が先に起動している必要がある点に注意。

- AI / リサーチ機能（プログラム的呼び出し）
  - 例: ファクター計算
    ```python
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect('data/kabusys.duckdb')
    res = calc_momentum(conn, date(2026, 4, 1))
    ```
  - AI モジュール（news_nlp.score_news / regime_detector.score_regime）は OpenAI API キーが必要です。失敗時はフォールバック動作で例外を上位に伝播または 0 値を使って継続します（関数ドキュメント参照）。

---

## 主要設定（主な環境変数）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト development）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: 実行エンジンの pid ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（デフォルト data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, default 60）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: "instant"|"partial"|"never"|"reject"（paper_trading の約定モデル）

設定は `.env` / `.env.local` をプロジェクトルートに置くことで自動読み込みされます（既存 OS 環境を保護）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイルと役割の概要です。

- src/kabusys/
  - __init__.py           — パッケージ宣言（バージョン等）
  - config.py             — 環境変数/設定管理（.env 自動読み込み）
  - run_monitoring.py     — SystemMonitor のポーリングループ実行スクリプト
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - execution/
    - order_manager.py    — 注文ライフサイクル管理
    - reconciler.py       — 起動時の注文・ポジション整合性チェック
    - (その他 broker / engine 関連)
  - monitoring/
    - monitoring_db.py    — SQLite テーブル定義・CRUD（冪等初期化）
    - system_monitor.py    — システム／データ鮮度監視
    - trade_monitor.py     — 注文滞留・約定異常監視
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag ファイル生成ユーティリティ
    - alert_manager.py     — LINE PUSH 通知ラッパ
    - monitoring_engine.py — 複数 Monitor を束ねる実行ループ
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定・投下資金スケールロジック
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py   — Momentum, Volatility, Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py          — ニュースを OpenAI で評価して ai_scores を更新
    - regime_detector.py   — ma200 + マクロセンチメントで market_regime を算出
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。実装ファイルはさらに細分化されています）

---

## 運用上の注意

- Paper Trading は本番DBと分離されます。paper_trading モードの DB はデフォルト `data/paper_trading.db` です。設定を確認してください。
- run_execution/run_monitoring は起動時にプロセス優先度（High）を設定しますが、環境により権限が必要で失敗する場合があります。失敗時は警告が出て処理を継続します。
- 強制停止シグナルはファイルベース（kill.flag）です。KillSwitch によって書き込まれると ExecutionEngine 側で検知して停止する仕組みです。
- OpenAI の利用は API キーが必要です。API 利用に伴うコスト・レート制限に注意してください。API の一時エラーには指数バックオフでリトライする実装がありますが、最終的にフォールバックする場合があります。
- DuckDB / SQLite のファイルロックや同時アクセスに注意してください（特にローカル環境で複数プロセスからアクセスする場合）。

---

## よく使うコマンドまとめ

- 仮想環境作成・有効化
  - Unix/macOS:
    ```
    python -m venv .venv
    source .venv/bin/activate
    ```
- パッケージインストール
  ```
  pip install duckdb psutil requests openai streamlit
  ```
- 監視起動
  ```
  python -m kabusys.run_monitoring
  ```
- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
- Streamlit ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に記載のない詳細な関数仕様や内部実装の説明は、各モジュールの docstring を参照してください。必要であれば、特定モジュールの使い方サンプルや環境変数サンプル（.env.example 相当）を追記します。どの部分を優先してドキュメント化したいか教えてください。