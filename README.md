# KabuSys

日本株自動売買システムのコンポーネント群。  
ポートフォリオ構築・ポジションサイジング、発注エンジン、監視・アラート、リサーチ（ファクター計算）、AI（ニュースNLP / レジーム判定）などをモジュール化して提供します。

※ 本リポジトリはライブラリ＋実行スクリプト群のコレクションです。用途に応じて ExecutionEngine / MonitoringEngine / ツール等を起動して利用します。

---

## 主な特徴（機能一覧）

- Execution（発注）
  - ExecutionEngine / OrderManager / Reconciler による注文発行・状態同期・起動時リコンシリエーション
  - Paper Trading（KABUSYS_ENV=paper_trading）用の MockBroker と専用 SQLite（data/paper_trading.db）による完全分離
  - リスクマネージャ（ポジション上限・利用率・ドローダウン等）
- Monitoring（監視）
  - SystemMonitor（プロセス生存 / CPU/メモリ/ディスク / データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格）
  - RiskMonitor（ドローダウン・ポジション上限監視）と KillSwitch（条件で停止フラグ生成）
  - MonitoringDB（SQLite）へ監視ログ/イベントを永続化
  - Streamlit ダッシュボード（read-only で監視状況表示）
- Portfolio（銘柄選定・配分・サイズ計算）
  - 候補選定、等重 / スコア重み、リスクベースサイズ計算、セクターキャップ、レジーム乗数
- Research（DuckDB を使ったファクター計算 / 特徴量解析）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- AI（OpenAI 連携）
  - ニュース NLP による銘柄別センチメントスコア生成（ai_scores への書き込み）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定（market_regime テーブルへ書込）
  - OpenAI 呼び出しはリトライ・フェイルセーフ等を備えた実装
- ツール
  - paper_verification_report: Paper Trading データから検証レポート生成
- ユーティリティ
  - 環境変数ローダー（.env/.env.local 自動読み込み）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - LINE Push によるアラート送信機能

---

## 必要条件（概略）

- Python 3.10+
- SQLite（組み込み）
- DuckDB（duckdb Python パッケージ）
- 外部ライブラリ（例）
  - duckdb, psutil, requests, streamlit, openai
- インターネット接続（OpenAI / LINE を利用する場合）
- 実行ユーザーによりプロセス優先度変更が失敗する場合あり（権限要件に注意）

（実際の依存関係はプロジェクトに requirements.txt 等を用意してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests streamlit openai

   実運用では pip の requirements.txt を用意し `pip install -r requirements.txt` を推奨します。

4. 環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` に設定できます（自動ロードされます）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必須/推奨）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY（AI 機能利用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE アラート利用時）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の振る舞い）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
   - LOG_LEVEL（INFO 等）
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）

5. data ディレクトリ等の作成（必要に応じて）
   - mkdir -p data

---

## 使い方（起動・コマンド例）

- ExecutionEngine を起動（本番・paper_trading は Settings に従う）
  - python -m kabusys.run_execution
  - 動作: PID ファイル (data/execution.pid)、停止フラグ (data/stop_requested.flag) を利用。KABUSYS_ENV=paper_trading の場合は paper_db に書き込み。

- Monitoring（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒、デフォルト 60）。
  - 監視は常に本番 sqlite_path を使用（Settings により決定）。

- Streamlit ダッシュボード（監視データ参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI 関連（ライブラリ的に使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key 引数が None の場合は環境変数 OPENAI_API_KEY を参照します。

- Kill / Stop
  - ExecutionEngine/Monitoring には以下のファイルを検査して停止や制御を行います:
    - data/stop_requested.flag: 実行スクリプトがループを終了するための外部停止フラグ
    - data/kill.flag: KillSwitch が書き込む（ExecutionEngine 停止指示用）
    - data/execution.pid: Execution プロセスの PID 管理
  - KillSwitch をクリアする（起動前クリーンアップ）は KillSwitch.clear() を呼ぶか、手動でファイル削除してください。

---

## 設計上の注意点 / 実用上のポイント

- Paper Trading と本番 DB は完全に分離されます（settings.is_paper により paper_sqlite_path が使用される）。
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします（CWD に依存しない）。
- OpenAI 呼び出しはレート制限 / ネットワーク障害 / 5xx に対してリトライとフェイルセーフ（0.0 にフォールバック等）を備えていますが、API キーの管理・コストに注意してください。
- process priority の設定は psutil を使って行います。権限不足で設定できない場合はログ警告でスキップされます。
- Monitoring のログ・テーブルは init_monitoring_db() で作成・マイグレーションが自動で行われます。
- DuckDB は研究用ファクタ処理・データ分析向けに使われ、prices_daily / raw_financials / raw_news 等のテーブルを参照します。DuckDB ファイルパスは Settings.duckdb_path で指定可能です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings 管理（.env ローダ含む）
  - run_execution.py                   — ExecutionEngine 起動スクリプト
  - run_monitoring.py                  — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py     — Paper Trading レポート生成ツール
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                      — ニュース NLP / OpenAI 連携
    - regime_detector.py               — レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py                 — SQLite 監視 DB 層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py                 — LINE push 通知
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker / order_repository 等の実装ファイル)
  - utils/
    - process_priority.py              — 優先度 / CPU affinity 設定ユーティリティ
  - research, data, portfolio, etc.

（上は主要モジュールの抜粋です。詳細はソースツリーを参照してください。）

---

## 簡単な起動例

1. 仮想環境 & 依存インストール（前述）
2. .env を用意（最低限必要なキーを設定）
3. 監視 DB の初期化（run_monitoring を起動すれば init_monitoring_db が実行されます）
4. Execution を起動
   - python -m kabusys.run_execution
5. 別ターミナルで Monitoring を起動
   - python -m kabusys.run_monitoring
6. ダッシュボード確認
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## トラブルシューティング / よくある質問

- 起動時に .env が読み込まれない:
  - Settings はプロジェクトルート（.git か pyproject.toml が存在するディレクトリ）を探索します。配布パッケージ後やテスト環境では自動ロードをスキップする場合があります。明示的に環境変数をエクスポートするか、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化できます。
- OpenAI 呼び出しで失敗してもシステムは継続:
  - AI モジュールはフェイルセーフ設計で、API 失敗時はスコアを 0 やスキップするなどの挙動になります。ログを確認してください。
- process priority の設定で PermissionError:
  - 権限の低いユーザーでは nice 値や Windows の優先度変更が拒否されます。ログに警告が出力されますが動作自体は継続します。
- kill.flag / stop_requested.flag の使い方:
  - 外部から ExecutionEngine を停止させたい場合は data/kill.flag を生成するか（KillSwitch が作成）、stop_requested.flag を置くことで run_* スクリプトを終了させることができます。起動時にクリーンにしたい場合はこれらを手動で削除してください。

---

この README はソースコードと同期していますが、実運用前に環境変数・依存ライブラリ・外部 API キーの管理方針を必ず確認してください。さらに詳しい仕様やアルゴリズムの詳細はソース内の docstring / コメントおよび関連ドキュメント（PortfolioConstruction.md 等）を参照してください。