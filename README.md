# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視コンポーネント群をまとめた小規模フレームワークです。本リポジトリには、発注エンジン・注文管理・リコンシリエーション、ポートフォリオ構築ユーティリティ、ファクター計算、ニュース NLP（OpenAI 経由のセンチメント評価）、監視（モニタリング）などのモジュールが含まれます。

以下はこのコードベースの概要、機能、セットアップ・起動方法、主要コンポーネントの説明およびディレクトリ構成です。

## プロジェクト概要
- 自動売買エンジン（ExecutionEngine）を起動してブローカーへ発注を行う実行部分。
- 発注・注文リポジトリ、OrderManager による状態管理とリコンシリエーション機能。
- ポートフォリオ構築（候補選定、重み付け、リスク調整、ポジションサイズ計算）。
- 研究用モジュール（ファクター計算、将来リターン、IC 計算など） — DuckDB を用いたオフライン解析向け。
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定。
- 監視（MonitoringEngine）: システム状態、注文の滞留・異常、ドローダウン監視、LINE 通知、kill flag による ExecutionEngine 停止シグナル。
- Streamlit による監視ダッシュボード（read-only で monitoring DB を表示）。

## 主な機能一覧
- 実行系
  - run_execution: ExecutionEngine を起動（本番 / paper_trading 切替）  
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離
- 監視系
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ね、kill switch / alert 通知を行う
  - streamlit_dashboard: Streamlit で監視ダッシュボードを表示
- ツール
  - paper_verification_report: Paper Trading 用の検証レポート生成（期間指定可）
- 研究 / データ処理
  - research パッケージ: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
  - data 側（DuckDB）を用いた高速なバッチ集計
- AI
  - news_nlp: raw_news を OpenAI で評価し ai_scores へ保存
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を出力
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジション量算出（lot 単位丸め、aggregate cap）

## セットアップ手順（開発環境向け）
1. Python を準備（3.9+ を想定）。
2. 依存パッケージをインストール（requirements.txt がない場合は主な依存を個別インストール）:
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - 実行環境では sqlite3 は標準ライブラリで利用可能。
3. プロジェクトルートに .env を作成（.env.example を参考に）。自動読み込み:
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を検出して `.env` / `.env.local` を自動ロードします。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
4. 必須環境変数（少なくとも以下を設定）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - 必須でないが利用可能: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（監視通知）
5. デフォルト DB パス（変更可能）
   - DuckDB: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - Monitoring SQLite: SQLITE_PATH（デフォルト: data/monitoring.db）
   - Paper Trading SQLite: PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
6. データディレクトリを作成:
   - mkdir -p data

注意:
- Paper trading（シミュレーション）では本番 DB と切り離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- Settings で各種閾値やパス、env 判定（development / paper_trading / live）を管理します。

## 使い方（実行例）
- 監視ループを起動:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
- 実行エンジンを起動（発注処理）:
  - KABUSYS_ENV を指定して本番 / paper_trading を切り替え:
    - 本番: export KABUSYS_ENV=live
    - ペーパー: export KABUSYS_ENV=paper_trading
  - 実行:
    - python -m kabusys.run_execution
  - 実行時の挙動:
    - プロセス優先度を high に設定（psutil を使用、権限不足時は警告でスキップ）
    - paper_trading では専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と完全分離
- Streamlit 監視ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring.db を読み取り専用で開いてダッシュボード表示します
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- AI（ニュース NLP / レジーム判定）:
  - 各関数は OpenAI API キー（OPENAI_API_KEY）を必要とします。モジュール API を利用して programmatic に呼び出すことができます。
  - 例: kabusys.ai.score_news(conn, target_date, api_key=None) — api_key が None の場合は環境変数を参照。

## 主要環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID を書くファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill flag（実行停止シグナル）ファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading における Mock ブローカーの fill モード（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API の認証情報（必須）

## 監視・アラートの仕組み（概要）
- SystemMonitor: CPU / メモリ / ディスク / ExecutionEngine の PID 存在確認 / 株価データ鮮度チェック
- TradeMonitor: 注文滞留（stale）チェック、約定価格の異常検出
- RiskMonitor: ドローダウン監視（ハイウォーターマーク）、ポジション数上限監視
- KillSwitch: ドローダウンやポジション上限がトリガーする場合、KILL_FLAG_PATH に reason を書き込んで ExecutionEngine に停止指示
- AlertManager: LINE Messaging API への一方向プッシュ。トークン未設定時は送信せずログのみ。一定時間のクールダウンあり。

## ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite テーブル初期化・アクセスラッパー（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知用クライアント（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動方法は上記参照）
  - execution/
    - order_manager.py — 注文管理、発注ワークフロー、同期 API
    - reconciler.py — 起動時のリコンシリエーション（Order / Positions）
    - （その他 execution 関連ファイルは本ツリーにあり用途別に実装）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け（等重 / スコア）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - position_sizing.py — 発注株数計算・aggregate cap
    - __init__.py — API エクスポート
  - research/
    - factor_research.py — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
    - __init__.py — API エクスポート
  - ai/
    - news_nlp.py — raw_news をまとめて OpenAI に送信し ai_scores に書き込む
    - regime_detector.py — ma200 とマクロニュースで市場レジーム判定
    - __init__.py
  - data/ (想定：データ格納用)
    - data/kabusys.duckdb（デフォルト）
    - data/monitoring.db（監視ログ）
    - data/paper_trading.db（paper_trading 用）
  - utils/
    - process_priority.py — psutil を使った優先度 / CPU affinity 設定ユーティリティ

（注）上記はコード内のモジュール実装を基にした抜粋説明です。細かいファイルは他にも存在します。

## 開発メモ / 注意事項
- Settings はプロジェクトルートを .git / pyproject.toml から自動検出して .env/.env.local を読み込みます。CI やテストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring/run_execution は起動時にプロセス優先度を "high" にしようとします（権限がない場合は警告を出して続行します）。
- MonitoringDB.init_monitoring_db は冪等であり、既存 DB に対する軽微なマイグレーション（カラム追加）も含みます。
- OpenAI への呼び出しは失敗時にリトライとフェイルセーフ（スコア 0.0 へのフォールバック）を備えていますが、API キーは必須です。
- paper_verification_report は paper_trading の検証を目的とした CLI です。DB の存在チェックを行います。

---

以上がこのリポジトリの主要な概要と使い方です。具体的な実装や拡張、運用ルールについては各モジュール内の docstring / コメントを参照してください。必要であれば README に追記する内容（例: 詳しい環境変数一覧、推奨パッケージバージョン、起動用 systemd ユニットの例など）を教えてください。