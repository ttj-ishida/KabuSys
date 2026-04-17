# KabuSys

KabuSys は日本株の自動売買（エクゼキューション）と運用監視を目的とした軽量な Python コードベースです。本リポジトリには、発注エンジンの起動スクリプト、監視システム、ポートフォリオ構築ロジック、リサーチ / ファクター計算、AI を使ったニュースセンチメント評価などの主要コンポーネントが含まれています。

---  

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数 / 設定
- 使い方（起動コマンド例）
- 重要なファイル・挙動メモ
- ディレクトリ構成

---

## プロジェクト概要

- 日本株自動売買システムのコアライブラリ群（Execution, Monitoring, Portfolio, Research, AI など）。
- DuckDB / SQLite を用いた市場データ・監視ログ保存。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / 市場レジーム判定の実装（API キー必須）。
- Paper Trading モードを持ち、本番 DB と分離された状態での検証が可能。

設計方針の一部：
- DuckDB を用いたローカル分析（prices_daily / raw_financials 等）を想定。
- 監視（Monitoring）は環境に依らず本番用の sqlite_path を参照する設計の箇所あり（run_monitoring の注記参照）。
- 起動時にプロセス優先度を高く設定するユーティリティを備える（psutil を使用）。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerFactory による実装切替（paper_trading では MockBroker）
  - OrderManager / OrderRepository / Reconciler による注文管理と再同期処理

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス確認 / データ鮮度チェック
  - TradeMonitor: 滞留注文チェック、約定異常チェック
  - RiskMonitor: ドローダウン／ポジション上限監視・アラート記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine 停止を通知
  - AlertManager: LINE Push による通知（トークン未設定時はログのみ）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
  - 監視ログ永続化（SQLite）を管理する MonitoringDB（テーブル初期化・マイグレーション含む）

- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - 株数決定（position sizing）、単元株丸め、投下資金のスケーリング

- Research（リサーチ）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（ニュースNLP / レジーム検知）
  - news_nlp.score_news: raw_news から銘柄ごとに記事を集約し OpenAI でスコア化 → ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) MA200 とマクロニュースセンチメントを合成して market_regime を算出・永続化
  - 再試行・バックオフ、レスポンス検証などフェイルセーフ実装あり

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカルでの実行想定）

前提：
- Python 3.10 以上（PEP 604 の | 型や match を用いていないが、Union 型の省略表記を使用しているため）
- SQLite（組み込み）、DuckDB、psutil、requests、openai、streamlit 等の Python パッケージ

推奨手順（一例）：

1. リポジトリをクローン / 取得
   - 例: git clone <this-repo>

2. 仮想環境の作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - インストールするパッケージ例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt がある場合はそれを利用してください（本コードベースには未提示）。

4. PYTHONPATH を通す（開発時）
   - export PYTHONPATH=src
   - Windows (PowerShell): $env:PYTHONPATH = "src"

   あるいはパッケージを編集可能インストール:
   - pip install -e .

5. .env ファイルの準備（任意だが推奨）
   - プロジェクトルートに .env / .env.local を置くことで Settings が自動で読み込みます（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数や主要なものは次節参照。

---

## 環境変数 / 設定（主要なもの）

Settings クラスで扱う主要変数（抜粋）:

- 必須（Settings._require を通るもの）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（使用箇所による）
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- OpenAI / LINE
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで必須）
  - LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（AlertManager）
  - LINE_USER_ID — LINE ユーザー ID（AlertManager）

- 実行環境切替
  - KABUSYS_ENV — 開発/ペーパー/本番を指定
    - 有効値: development, paper_trading, live
    - デフォルト: development

- DB / パス系
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill フラグファイル（デフォルト: data/kill.flag）

- Paper Trading 動作
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

- 監視しきい値
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（デフォルト値は Settings に設定）

- ログ
  - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）

自動ロード:
- プロジェクトルート（.git または pyproject.toml を検出）から .env を自動で読み込みます（ただし OS 環境変数は上書きされません）。.env.local は上書きされます。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（よく使う起動コマンド例）

開発時は PYTHONPATH=src を設定して モジュールとして実行します。あるいは pip install -e . して -m で実行できます。

1. 監視ループを起動（Monitoring）
   - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可（正の整数のみ、有効でない場合は 60 秒にフォールバック）。
   - 実行例:
     - PYTHONPATH=src python -m kabusys.run_monitoring
     - または: python -m kabusys.run_monitoring

   - 動作ノート:
     - 監視は常に Settings.sqlite_path（本番 DB）を使います（run_monitoring の実装上の挙動）。
     - 停止はプロジェクトルート/data/stop_requested.flag の作成で検出します。

2. 発注エンジンを起動（Execution）
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
   - 実行例:
     - PYTHONPATH=src python -m kabusys.run_execution
   - 動作ノート:
     - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
     - 実行中に stop flag が作られると安全に停止処理を行います。
     - エンジンは data/execution.pid に PID を書きます。

3. Streamlit 監視ダッシュボード
   - 実行例（ファイル内コメントの通り）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで別 DB を指定できます。デフォルトは data/paper_trading.db。

5. AI モジュールを直接呼び出す例（プログラム内から）
   - news スコア取得:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="sk-...")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="sk-...")

   いずれも duckdb 接続（duckdb.connect(...)）を渡して使用します。API キーは引数または環境変数 OPENAI_API_KEY から解決されます。

---

## 停止・フラグ関連

- 停止フラグ（run_monitoring / run_execution が参照）
  - data/stop_requested.flag — 両スクリプトで監視・起動制御に利用
- Kill Switch（自動停止判定）
  - KillSwitch はリスク条件を満たすと data/kill.flag（デフォルトパスは Settings.kill_flag_path）を書き込むことで ExecutionEngine 停止を誘導します。
  - KillSwitch はすでにファイルが存在する場合は上書きしない（冪等）。

---

## 重要な実装メモ（運用上の注意）

- Settings はプロジェクトルートの .env / .env.local を自動読み込みします。テストや CI で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- run_monitoring は「監視」用であり、実装上 monitoring が本番 sqlite_path を参照するので environment に依らず本番 DB を使う点に注意してください（意図的な設計）。
- process priority の設定は psutil によるもので、権限不足時は警告が出てスキップされます。
- OpenAI 呼び出し部分はリトライやレスポンス検証が組み込まれていますが、API キーや料金・レートに注意してください。

---

## ディレクトリ構成（抜粋）

以下は本コードベースに含まれる主なファイルと説明です（src/kabusys 以下）:

- __init__.py
  - パッケージ定義（__version__ 等）

- run_monitoring.py
  - SystemMonitor を用いたポーリングループ起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60 秒）

- run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading モードで MockBroker を使用

- config.py
  - Settings クラス（環境変数読み込み、.env の自動ローディング、各種パス・設定）

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン / IC / 統計

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）ロジック
  - regime_detector.py — 市場レジーム判定（MA + macro sentiment）

- monitoring/
  - monitoring_db.py — SQLite テーブル作成・CRUD ユーティリティ（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション数監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE Push 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード

- execution/
  - order_manager.py, reconciler.py, order_repository.py, ...（発注ロジック）

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上の一覧は提供ファイルに基づく抜粋です。実際のリポジトリにはさらに細かなファイル／モジュールが存在する可能性があります）

---

## よくある操作例 / トラブルシューティング

- 「モジュールが見つからない」エラー
  - 開発時は `PYTHONPATH=src` を設定するか、`pip install -e .` で編集可能インストールしてください。

- OpenAI 関連でのエラー
  - OPENAI_API_KEY を環境変数または関数引数で供給してください。ネットワークやレート制限はリトライ実装がありますが、回数超過で失敗すると該当銘柄はスキップされます。

- データベースファイルがない / 開けない
  - duckdb / sqlite のファイルパスは Settings で指定できます（デフォルトは data/ 以下）。必要なら data ディレクトリを作成してください（自動で作成される箇所もありますが、権限等により失敗することがあります）。

---

この README はコードベースの主要部分に基づく概要ドキュメントです。実際の運用やデプロイにあたっては、環境に合わせた .env の整備、API キー管理（安全なシークレット管理）、監視の運用フロー設計（ログの永続化・バックアップ、アラート受信者設定）を行ってください。必要であれば、起動フローやデプロイ手順をより詳細にまとめた運用ドキュメント作成も支援します。