# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）。  
ポートフォリオ構築・ポジションサイジング・発注管理・監視・研究・AI（ニュースセンチメント／レジーム判定）等のコンポーネントを含むモジュール群です。

---

## 概要

KabuSys は以下の主要機能を組み合わせて、日本株の自動売買ワークフローを実現するためのライブラリ／実行スクリプト群です。

- 戦略側：ファクター計算（モメンタム／ボラティリティ／バリュー等）、特徴量探索、ファクター評価（IC）  
- ポートフォリオ構築：候補選定、等重・スコア重み付け、セクター制限、レジーム乗数  
- ポジション管理：リスクベース/等配分等の株数計算、単元株丸め、キャッシュ制約対応  
- 発注実行：OrderManager／ExecutionEngine（ブローカークライアント抽象化、Paper Trading モードあり）  
- リコンシリエーション：再起動後の注文・ポジション同期処理（Reconciler）  
- 監視：プロセス・リソース・データ鮮度・滞留注文・約定異常・ドローダウン等の監視とログ永続化（SQLite）  
- アラート：LINE Push を使った通知（AlertManager）  
- AI：OpenAI を用いたニュースのセンチメントスコアリング（news_nlp）と市場レジーム判定（regime_detector）  
- UI/ツール：Streamlit ベースの監視ダッシュボード、Paper Trading の検証レポート生成ツール

プロジェクトはモジュール単位で設計され、テストや研究用途で DuckDB / SQLite を用いてローカルに完結するようになっています。

---

## 機能一覧（抜粋）

- kabusys.config: .env 自動読み込み / 環境設定取得（KABUSYS_ENV により動作モード切替）
- kabusys.portfolio: 候補選定・重み算出・リスク調整・ポジションサイズ算出
- kabusys.research: ファクター計算（momentum/volatility/value）、将来リターン・IC・統計サマリ
- kabusys.execution: OrderManager、Reconciler、ExecutionEngine（ブローカー抽象化）
- kabusys.monitoring: MonitoringDB（SQLite）、System/Trade/Risk モニタ、KillSwitch、AlertManager、MonitoringEngine、Streamlit ダッシュボード
- kabusys.ai: news_nlp（ニュース→センチメント）、regime_detector（MA + マクロセンチメント合成）
- ツール: paper_verification_report（Paper Trading の検証レポート生成）

主な実行エントリ:
- run_execution.py — ExecutionEngine 起動（本番/紙/検証モード対応）
- run_monitoring.py — SystemMonitor（単体）を起動する簡易ポーリングスクリプト
- streamlit_dashboard.py — Streamlit による監視ダッシュボード
- tools.paper_verification_report — Paper Trading の検証レポート出力ツール

---

## セットアップ

前提
- Python 3.8+（プロジェクトで厳密な要求は明記されていませんが、型注釈等から少なくとも 3.8 以上を想定）
- SQLite（標準ライブラリ）
- DuckDB
- psutil, requests, openai, streamlit など

例: 仮想環境での手順（一般例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（requirements.txt がある場合はそれを利用）
   - pip install duckdb psutil requests openai streamlit

   ※プロジェクトに requirements.txt がなければ上記主要依存をインストールしてください。

環境変数 / .env
- プロジェクトはルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 主要な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
  - KABUSYS_ENV — 実行モード（development / paper_trading / live）。paper_trading は broker をモック化し DB を分離します。
  - PAPER_FILL_MODE — paper_trading 時の約定挙動（instant / partial / never / reject）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — Execution 起動・停止制御関連
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

簡単な .env の例 (.env.example を参考に作成してください):
    JQUANTS_REFRESH_TOKEN=xxxx
    KABU_API_PASSWORD=yyyy
    OPENAI_API_KEY=sk-...
    KABUSYS_ENV=development
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

データディレクトリ
- デフォルトで使用する DB やファイルは `data/` に配置されます。必要に応じて環境変数で上書きしてください。

---

## 使い方（実行例）

1. ExecutionEngine を起動する（本番/紙取引は KABUSYS_ENV で切替）
   - python -m kabusys.run_execution
   - 実行時は Settings が .env 等を参照し、paper_trading なら `data/paper_trading.db` を使用します。

2. SystemMonitor（単体の監視プロセス）をポーリング起動
   - MONITOR_POLL_INTERVAL 環境変数で間隔指定（秒）
   - python -m kabusys.run_monitoring

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4. Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5. AI スコアリング / レジーム判定（ライブラリ API として）
   - ニューススコア付与（例、Python スクリプト内で呼び出し）:
     from kabusys.ai import score_news
     score_news(conn=duckdb_conn, target_date=date(2026,4,10), api_key="sk-...")
   - レジーム判定（regime_detector.score_regime を直接呼ぶ）:
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn=duckdb_conn, target_date=date(2026,4,10), api_key="sk-...")

注意事項
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離した専用 SQLite を用います。
- run_monitoring/run_execution は起動時にプロセス優先度を high に設定しようとします（psutil で失敗時は警告を出します）。
- monitroing の DB テーブルは起動時に自動作成・マイグレーションされます（init_monitoring_db を参照）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化（__version__）
  - config.py — .env 自動読み込み、Settings クラス（環境変数アクセス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数決定・キャップ・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）スコアリング
    - regime_detector.py — マクロ + MA によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・MonitoringDB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
    - trade_monitor.py — 滞留注文・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション数チェック
    - kill_switch.py — kill.flag 書き込みによる停止トリガ
    - alert_manager.py — LINE プッシュ通知管理
    - monitoring_engine.py — Monitor をまとめて実行するエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — OrderState 管理・発注フロー
    - reconciler.py — 再起動時の同期処理
    - （その他：broker_factory, order_repository, execution_engine など 想定）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （実行時に使用する DB 等。ソース管理では通常除外）

---

## 運用上のメモ（重要ポイント）

- KABUSYS_ENV
  - development / paper_trading / live のいずれか。paper_trading は MockBroker を使い、記録 DB を分離します。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。0 以下や不正値は 60 秒にフォールバックします。
- PID / kill.flag
  - ExecutionEngine は PID ファイルを書き、監視プロセスは PID ファイルの存在や死活を確認して stale PID を検出します。
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に安全停止を促します。
- OpenAI
  - news_nlp / regime_detector は OpenAI API を利用します。API キー未設定時は例外またはフォールバック（regime は macro_sentiment=0）となる挙動があります。API 呼び出しはリトライとフェイルセーフ実装あり。
- 監視ログ
  - MonitoringDB（SQLite）は system_status, trade_logs, positions, risk_logs, dashboard を持ち、マイグレーション（カラム追加）処理も起動時に走ります。

---

## 開発・拡張ポイント（参考）

- position_sizing: lot_size の銘柄別対応や価格フォールバックの改善余地あり
- AI モジュール: JSON 出力検証やチャンク処理の堅牢化済みだが、プロンプトやモデル選択は今後調整可能
- monitoring: Alert の送信先追加（Slack 等）や永続化拡張が可能
- DuckDB を用いることでローカルで高速に時系列クエリ・ファクター計算を行える設計

---

この README はコードベースを元に概要と使い方を整理したものです。詳細な設計仕様やドキュメント（StrategyModel.md, PortfolioConstruction.md 等）が別途ある想定です。必要であれば各モジュールの API 仕様や使用例（コードスニペット）を追加できます。