# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
このリポジトリは、注文実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含みます。

主な設計方針：
- 本番用の DB（DuckDB / SQLite）を用いたデータ処理と永続化
- モジュール分離（execution / monitoring / portfolio / research / ai）
- テストしやすい純粋関数群（ポートフォリオ計算など）
- OpenAI を利用した自然言語処理機能はフェイルセーフ実装（API失敗時は許容）

---

## 概要（Project overview）

主要な実行スクリプト：
- 実行エンジン起動: `src/kabusys/run_execution.py`
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper 専用 SQLite（既定: `data/paper_trading.db`）に記録して本番と分離します。
- 監視ループ起動: `src/kabusys/run_monitoring.py`
  - システム状態・注文状況・リスク監視を定期実行して SQLite にログ保存します。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。

ユーティリティ & ツール：
- Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
  - Paper DB を集計して uptime、注文成功率、レイテンシ等の検証レポートを標準出力に出します。
- Streamlit ダッシュボード: `src/kabusys/monitoring/streamlit_dashboard.py`
  - 監視用の簡易 UI を提供（読み取り専用で SQLite を開く）。

設定管理：
- `src/kabusys/config.py` — 環境変数の読み込み・検証。`.env`/.env.local の自動読み込み機能あり（無効化可）。

AI 機能：
- `kabusys.ai.news_nlp` — ニュース記事から銘柄別センチメントを OpenAI (gpt-4o-mini) で算出して `ai_scores` に書き込む。
- `kabusys.ai.regime_detector` — ETF の MA / マクロニュースを組み合わせて市場レジームを判定・永続化。

ポートフォリオ & リスク：
- `kabusys.portfolio` — 候補選定、重み計算、ポジションサイズ決定、セクターキャップ・レジーム乗数などを純粋関数で実装。
- `kabusys.monitoring` — system / trade / risk の各種モニター、アラート、kill switch、監視 DB 操作など。

---

## 機能一覧

- Execution
  - 注文作成 → 送信 → 同期（Reconciler による再起動後の復旧）
  - リスク管理（RiskManager）
- Monitoring
  - サーバリソース（CPU/Mem/Disk）監視
  - データ鮮度（DuckDB 上の最終価格日）
  - 注文滞留（stale orders）・約定異常価格検出
  - ドローダウン・ポジション上限監視と kill flag 発行
  - LINE によるアラート送信（任意設定）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio construction
  - 候補選定（score / rank）
  - 等重／スコア重み／リスクベース割当
  - セクターキャップ適用、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）・統計サマリ
- AI（OpenAI）
  - ニュース NLU による銘柄センチメント（バッチ、リトライ、検証）
  - マクロ記事を用いたレジーム判定（MA + LLM）  
  ※ OpenAI API の失敗はフォールバックや 0 値で安全に継続します。

---

## 必要条件（Dependencies）

最低限の主要依存ライブラリ：
- Python 3.9+
- duckdb
- psutil
- requests
- streamlit（ダッシュボードを使う場合）
- openai（AI機能を使う場合）

（実際のプロジェクトでは requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 依存パッケージのインストール
   - pip install duckdb psutil requests streamlit openai
   - （開発時は pip install -e . を推奨）

3. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動ロードされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 代表的な環境変数（デフォルトは括弧内）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API）
     - OPENAI_API_KEY — OpenAI を使う場合に必須
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定なら通知はスキップ）
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定モード（デフォルト: instant）
     - PID_FILE_PATH (data/execution.pid)
     - KILL_FLAG_PATH (data/kill.flag)
     - MONITOR_POLL_INTERVAL — 監視ループの間隔（秒、デフォルト 60）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - `.env.local` があれば `.env` の上から上書き読み込みされます。OS 環境変数は保護され上書きされません。

4. DB 初期化
   - `run_monitoring` や `run_execution` 起動時に `init_monitoring_db()` が呼ばれて監視用 SQLite テーブルは自動作成されます。
   - DuckDB や raw データの準備はプロジェクト固有（prices_daily / raw_financials / raw_news 等のテーブルが必要）。

---

## 使い方（起動方法・コマンド例）

基本的な起動例（仮想環境内から）：

- 監視ループを起動（デフォルトポーリング 60 秒）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書きする: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（実際のブローカーを叩かない検証モード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper 専用 DB に記録され、本番監視 DB とは分離されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 別 DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - Dashboard は読み取り専用で、DB が見つからない場合は起動に失敗します（MonitoringEngine を先に起動してください）。

開発用のユーティリティ：
- MonitoringEngine.run_once() を使えば単発実行のテストが可能（単体テストで利用）。

注意点：
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使います（監視ログは本番監視 DB を前提）。
- run_execution は KABUSYS_ENV が `paper_trading` の場合に paper_sqlite_path を使用し本番 DB と分離します。

---

## 主要な設定項目（Settings の要約）

（`src/kabusys/config.py` を参照）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが有効値制約あり）
- DUCKDB_PATH: DuckDB ファイルのパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（既定: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper ブローカーの約定振る舞い）
- PID_FILE_PATH / KILL_FLAG_PATH: ExecutionEngine の監視・停止に使うファイルパス
- CPU / MEMORY / DISK の閾値は環境変数で上書き可能

自動 .env 読み込み：
- プロジェクトルートは `.git` または `pyproject.toml` を親階層から検索して決定
- `.env` → `.env.local` の順で読み込み（OS 環境変数は保護）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

---

## アーキテクチャ & コンポーネント説明（簡易）

- execution/
  - ブローカークライアント生成（BrokerClientFactory）
  - OrderManager / OrderRepository / Reconciler — 注文の作成・送信・同期
  - RiskManager — 発注前リスクチェック
- monitoring/
  - SystemMonitor — システムリソース・データ鮮度・プロセス監視
  - TradeMonitor — 注文滞留や約定異常を検出
  - RiskMonitor — ドローダウン、ポジション上限監視
  - KillSwitch / AlertManager — 停止シグナル・通知
  - MonitoringDB — SQLite の CRUD をラップ（テーブル作成 / マイグレーション含む）
- portfolio/
  - 候補抽出・重み付け・ポジションサイズ計算・リスク調整（純粋関数群）
- research/
  - DuckDB 上でファクター計算・将来リターン・IC 計算等
- ai/
  - news_nlp / regime_detector — OpenAI を用いたテキスト解析と DB への格納
- utils/
  - process_priority — プラットフォーム依存を吸収してプロセス優先度 / CPU affinity を設定

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_execution.py
- run_monitoring.py
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
  - (その他 broker / engine / order_repository 等)
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
- data/ (想定されるデータアクセスモジュール)
- utils/
  - __init__.py
  - process_priority.py

（上記はリポジトリ内の主要ファイルの抜粋です。実際のファイル一覧はプロジェクトを参照してください）

---

## 運用・注意事項

- 監視プロセスは `set_process_priority("high")` を呼んでプロセス優先度を上げようとしますが、権限や OS により失敗する可能性があります（警告が出ます）。
- OpenAI 連携機能を使う場合は `OPENAI_API_KEY` を必ず設定してください。API 呼び出しはリトライ・バックオフが組み込まれていますが、コストとレート制限に注意してください。
- Paper Trading は本番 DB と分離されていますが、DuckDB（履歴データ等）は共通で使われる想定になることがあります。運用時は DB パスや権限に注意してください。
- kill.flag（既定: data/kill.flag）を監視して ExecutionEngine を停止させる仕組みがあります。起動時にフラグを自動でクリアする挙動は `KILL_FLAG_CLEAR_ON_START` で制御可能です。
- `monitoring_db.init_monitoring_db()` は冪等であり、既存 DB に対するカラム追加等の簡単なマイグレーションを含みます。

---

## 開発者向けメモ

- テストしやすさのため、AI呼び出し部分や time.sleep 等をモックできるように設計されています（例: news_nlp._call_openai_api を差し替え）。
- `MonitoringEngine.run_once()` や各 Monitor の `check_once()` は単体実行可能でユニットテストが書きやすいインターフェースです。
- DuckDB を使ったリサーチコードは SQL + Python の組み合わせで高速に計算する設計です。prices_daily / raw_financials / raw_news といったテーブルが前提になります。

---

必要であれば、README に付けるサンプル .env.template、起動シェルスクリプト、依存用 requirements.txt、及びデプロイ手順（systemd ユニット例）を作成できます。どれを追加しますか？