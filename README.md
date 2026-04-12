# KabuSys

日本株自動売買システムのコアライブラリ群とユーティリティ。  
このリポジトリは戦略のポートフォリオ構築、発注実行、監視（監視DB / アラート / Kill Switch）、リサーチ／ファクター計算、AI を使ったニュースセンチメント評価などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な設計方針は以下の通りです。

- モジュール化：監視（monitoring）、発注（execution）、ポートフォリオ構築（portfolio）、リサーチ（research）、AI（ai）などを分離
- フェイルセーフ：API 失敗や部分失敗時は安全にフォールバック（例：AI API失敗 → スコア0で継続）
- テスト容易性：外部呼び出しを抽象化し、モック/テスト差し替えしやすい設計
- DB分離：`paper_trading` 環境は本番DBと分離された専用SQLiteを使用

---

## 機能一覧

- 環境変数ベースの設定読み込み（.env / .env.local 自動ロード）
- 実行プロセスの優先度設定ユーティリティ（Windows / POSIX 対応）
- 監視機能
  - SystemMonitor：CPU/メモリ/ディスク使用率、プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新・risk_logs 登録
  - KillSwitch：条件によりフラグファイルを書き ExecutionEngine を停止させる
  - AlertManager：LINE Push での通知（クールダウン付き）
  - MonitoringEngine：各モニタを束ねて定期ポーリング
  - Streamlit ダッシュボード（read-only 表示）
- 発注・Execution 周り（実行エンジン呼び出しスクリプト／各種コンポーネント）
  - OrderManager、Reconciler（起動時の同期処理）、RiskManager 等（実装参照）
  - Paper trading モードでは Mock ブローカーを使用し、専用 DB に記録
- ポートフォリオ構築
  - 候補選定、等配分／スコア加重配分、リスク調整（セクター上限、レジーム乗数）
  - 位置サイズ計算（単元株丸め、aggregate cap、コストバッファ等）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン ρ）、統計サマリ
- AI
  - news_nlp：OpenAI を使ったニュースセンチメント集計 → ai_scores テーブルへ保存
  - regime_detector：ETF MA とマクロニュースを合成して市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（過去期間の稼働率／成功率／レイテンシ評価）

---

## 動作要件（概略）

- Python 3.10+
- 主な依存パッケージ（詳細は requirements.txt を用意してください）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI / LINE API 利用時）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロダクション用に requirements.txt を用意している場合は `pip install -r requirements.txt`）

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN — （J-Quants 用）
     - KABU_API_PASSWORD    — kabuステーション API のパスワード
   - 任意（例・デフォルトあり）
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — default: instant
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等
   - サンプル: .env.example を参照（プロジェクトルートにある想定）

5. データディレクトリ準備
   - デフォルトの DB パス（data/）を作成:
     - mkdir -p data

6. 初期 DB テーブル生成
   - 監視用 SQLite は起動時に `init_monitoring_db()` が実行されて自動作成されます。特別な初期化は不要です。

---

## 使い方（代表コマンド／例）

- 監視ループの起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
    - または（パスから）python src/kabusys/run_monitoring.py
  - 補足:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意。

- 実行エンジン（ExecutionEngine）起動
  - 実行:
    - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録されます。
    - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from / --to 日付（YYYY-MM-DD）
    - --db DBファイルパス（省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を read-only で開いて表示します。DB が存在しない場合は MonitoringEngine を先に起動してください。

- ライブラリ関数の利用例（Python から直接呼ぶ）
  - 例: AI ニューススコアリング
    - from kabusys.ai import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - n = score_news(conn, target_date=datetime.date(2026,4,1), api_key="your_openai_key")
  - 例: ファクター計算
    - from kabusys.research import calc_momentum
    - result = calc_momentum(duckdb_conn, target_date)

---

## 主要な設定（環境変数）

（Settings クラスに基づく主な設定項目）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — AI 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE通知）利用時に必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の約定挙動）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG|INFO|...（default: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ宣言（__version__ 等）
- config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化と永続化 API（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みによる停止シグナル
  - alert_manager.py — LINE push 通知ラッパ
  - monitoring_engine.py — 各 Monitor を束ねてポーリング
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数決定・aggregate cap 処理
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- execution/
  - order_manager.py — OrderState 管理、発注ワークフロー
  - reconciler.py — 起動時の注文・ポジション照合・復旧
  - （その他: broker_factory, execution_engine, order_repository, risk_manager 等）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（実際のリポジトリには上記以外にも細かいモジュールが含まれます。各ファイルの docstring に詳細設計や挙動の注意点が書かれていますので参照してください。）

---

## 開発メモ / 注意点

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）検出に依存します。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper trading は本番 DB と排他に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- MonitoringDB のマイグレーション（カラム追加）は init_monitoring_db で冪等に行われます。
- OpenAI API 呼び出しはリトライ／バックオフ実装あり。API キー未設定時は明示的に例外を出す関数と、失敗時に安全側フォールバックする実装があります（関数ごとに挙動を確認してください）。
- `MONITOR_POLL_INTERVAL` の値が不正（負や 0）の場合はデフォルトにフォールバックします。

---

必要であれば、README に追加する内容（例: 詳細な起動フロー図、CI/CD 手順、テストの書き方、requirements.txt の具体的な内容、開発環境構築スクリプト例）を作成します。どの情報を優先して追加しますか？