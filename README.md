# KabuSys — 自動売買システム README

本リポジトリは日本株向けの自動売買システム「KabuSys」の一部実装です。ここではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

注意：この README はソースコード（src/kabusys 以下）を元に作成しています。実運用時は必ず十分なテストとレビューを行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステム群で、主に以下の機能ブロックを含みます。

- 注文発行・状態管理（ExecutionEngine、OrderManager、OrderRepository 等）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- リスク制御（ドローダウン監視、ポジション上限等）、Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定／重み付け／ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算等）
- AI 補助（ニュースの NLP による銘柄センチメントスコア、レジーム検出）
- 運用補助ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針の一部：
- 本番／Paper Trading を分離（DB も分離）
- ルックアヘッドバイアスを避ける（datetime.today() を直接参照しない等）
- 外部 API 呼び出しは単一箇所に集約・リトライ実装（OpenAI 呼び出しなど）
- SQLite / DuckDB をデータ層で利用

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象（BrokerClientFactory）
  - Order 管理（作成、同期、キャンセル等）
  - Reconciler による再起動後の自動復旧（注文状態・ポジションの突合）
  - Paper Trading モード（MockBrokerClient、専用 DB）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常検知
  - RiskMonitor：ドローダウン、ポジション数上限の監視とアラート記録
  - KillSwitch：条件により停止フラグ（data/kill.flag）を作成して Execution を停止
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringDB：監視ログを保存する SQLite 層（スキーマ作成/マイグレーション含む）
  - Streamlit ダッシュボード（data/monitoring.db を読み取り表示）

- Portfolio construction
  - 候補選定（select_candidates）
  - 重み算出（等配分 / スコア加重）
  - セクター集中制限の適用（apply_sector_cap）
  - ポジションサイズ計算（複数方式、lot 単位丸め、aggregate cap）

- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI
  - news_nlp.score_news：ニュース記事を OpenAI で解析し ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロニュース（LLM）で市場レジーム判定

- ツール
  - tools/paper_verification_report.py：Paper Trading DB を使った検証レポート生成

---

## セットアップ手順（開発環境向け）

1. システム要件（目安）
   - Python 3.9 以上推奨
   - SQLite（組み込み）
   - DuckDB Python パッケージ
   - ネットワークアクセス（ブローカー API / OpenAI / LINE を使う場合）

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（代表的な依存）
   （プロジェクトの requirements.txt がない場合、以下をインストールしてください）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - duckdb: 時系列データ計算 / research 用
   - psutil: プロセス・CPU/メモリ情報取得
   - requests: LINE API 呼び出し
   - openai: OpenAI API（news_nlp / regime_detector）
   - streamlit: 監視ダッシュボード

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（config.py により）。
   - 重要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (news_nlp / regime_detector を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (監視アラート用)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|...
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
     - PAPER_FILL_MODE: instant|partial|never|reject  (paper_trading の約定モード)

   例 `.env` の抜粋（.env.example を作る場合の例）
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

5. データディレクトリ
   - デフォルトで `data/` 配下に SQLite / DuckDB / PID / フラグファイルが保管されます。必要に応じて手動で作成してください。
   - 実行スクリプトは起動時にテーブル作成（init_monitoring_db）を行います。

---

## 使い方（主要スクリプト・モジュール）

以下は典型的な起動・利用方法です。実運用では監視・ログ・プロセスマネージャを組み合わせて運用してください。

### 1) 実行エンジン起動（Execution）
- 目的：発注エンジンを起動し、戦略からのシグナルで発注を行う（ブローカー接続が必要）。
- 起動（モジュール実行）：
  ```
  python -m kabusys.run_execution
  ```
- 注意点：
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient が使用され、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB と分離されます。
  - 起動前に `data/kill.flag` が存在すると起動を中止します（停止フラグ）。
  - プロセス PID は `data/execution.pid` に書き込まれます（実行ファイル内で設定）。

### 2) 監視ループ起動（Monitoring）
- 目的：定期的に System / Trade / Risk を監視し、ログ・アラート・KillSwitch を管理する。
- 起動：
  ```
  python -m kabusys.run_monitoring
  ```
- オプション（環境変数）
  - MONITOR_POLL_INTERVAL：ポーリング間隔（秒、デフォルト 60）。無効値はデフォルトにフォールバック。
- 停止：
  - プロジェクトルートの `data/stop_requested.flag` を作成すると監視ループは安全に終了します（run_monitoring/run_execution の両方でチェックされています）。
- 監視は MonitoringDB（SQLite）にログを残します。

### 3) Streamlit ダッシュボード（監視）
- 目的：監視 DB を可視化する（ローカルでの確認用）。
- 起動（例）：
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Dashboard は read-only URI で SQLite に接続します。MonitoringEngine が DB を作成していない場合はエラー表示します。

### 4) Paper Trading 検証レポート
- 目的：Paper Trading の実績を集計・評価して PASS/FAIL を出す。
- 実行例：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB 指定：
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
- 出力：稼働率、注文成功率、送信率、レイテンシ（P95）などを表示し、閾値に基づいて判定します。

### 5) AI 関連（ニューススコアリング / レジーム判定）
- news_nlp.score_news と regime_detector.score_regime は Python API として提供されます。DuckDB 接続（duckdb.connect）を渡して使用します。
- OpenAI API キーは `OPENAI_API_KEY` 環境変数、もしくは関数引数で渡します。
- 例（簡易）：
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date は date オブジェクト
  score_news(conn, target_date, api_key="sk-...")
  ```

---

## 運用上のファイル・フラグ（主要）

- data/monitoring.db（デフォルトの監視 SQLite DB、Settings.sqlite_path）
- data/paper_trading.db（Paper Trading 用 SQLite DB）
- data/kabusys.duckdb（DuckDB データ格納）
- data/execution.pid（ExecutionEngine の PID）
- data/kill.flag（KillSwitch が書き出す停止フラグ。ExecutionEngine は起動時に設定を参照）
- data/stop_requested.flag（手動停止用フラグ。run_monitoring / run_execution が監視して終了）

Kill Switch と Stop フラグの違い：
- Kill Switch（kill.flag）はシステム内部の条件（ドローダウン等）により作成され、Execution を停止するために用います。
- stop_requested.flag は外部からの「優雅な停止要求」に使われ、監視ループやエンジンはこれを検出して終了します。

---

## 設定について（Settings / .env の自動読み込み）

- `src/kabusys/config.py` により、プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします（OS 環境変数優先）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- Settings クラスでアクセス可能な主要プロパティ（抜粋）:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path, paper_sqlite_path
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - env (development | paper_trading | live), log_level

---

## ディレクトリ構成（主要ファイルの一覧）

以下はソースツリー（src/kabusys）のおおまかな構成です。実際のリポジトリには追加ファイルがある場合があります。

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py (参照ファイル群がある前提)
    - reconciler.py
    - execution_engine.py (参照)
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_repository.py
    - order_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/  (アプリ実行時に使用するファイル群：DB / pid / flags)

---

## 注意点・運用上のヒント

- Paper Trading モードでは本番 DB を汚染しないよう、`KABUSYS_ENV=paper_trading` を利用してください。Settings では paper_sqlite_path が使われます。
- モニタリングは常に本番の sqlite_path を参照する設計になっている箇所があるため（run_monitoring.py コメント参照）、運用時の DB 設定に注意してください。
- OpenAI を利用する機能は API キーとコストが必要です。API 呼び出しはリトライ等の堅牢化がされていますが、失敗時はフェイルセーフ（多くはスコア 0 またはスキップ）となるよう実装されています。
- process priority や CPU affinity は `psutil` 経由で変更します。権限がないと警告ログを出しスキップします。
- monitoring_db.init_monitoring_db は冪等にテーブルを作り、必要に応じて簡易マイグレーション（カラム追加）も行います。
- デバッグ（ローカル開発）では `KABUSYS_ENV=development` を使い、ログレベルや DB パスを .env で調整してください。

---

## さらに参考になる箇所（ソース内コメント）

- 各モジュール（news_nlp.py / regime_detector.py / factor_research.py / position_sizing.py など）は詳細な設計方針やアルゴリズムのコメントが付与されています。実装や挙動を理解する際は各ファイル上部の docstring を参照してください。

---

この README はソースコードのスナップショットに基づく概要です。環境や要件に合わせて設定や運用手順を調整してください。追加で必要な項目（例：詳細な環境変数一覧のテンプレート、CI / systemd ユニット例、requirements.txt 生成など）があれば教えてください。必要に応じて追記します。