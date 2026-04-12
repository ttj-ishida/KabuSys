# KabuSys

日本株自動売買システムのサンプル実装リポジトリ（ライブラリ群 + 実行スクリプト）。  
この README ではプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

※ 本リポジトリは教育/研究目的のコードベースです。実運用では十分な安全対策・テスト・レビューが必要です。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のためのモジュール群を提供します。主な機能は以下の通りです。

- ポートフォリオ構成（候補選定・重み付け）
- ポジションサイジング（リスクベース、等配分、スコア配分）
- リスク調整（セクターキャップ、レジーム乗数）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等） — DuckDB での集計
- AI（LLM）を使ったニュースセンチメント（OpenAI）と市場レジーム判定
- 注文管理・送信のための Execution レイヤ（OrderManager 等）
- リコンシリエーション（再起動時の注文同期）
- 監視（System / Trade / Risk モニタ）、監視ログの永続化（SQLite）
- 監視ダッシュボード（Streamlit）と運用ツール（紙トレード検証レポート生成）

設計の特徴：
- DuckDB を用いたオンメモリ/高速集計（prices_daily / raw_financials 等を想定）
- 監視ログは SQLite（data/monitoring.db）。paper_trading は専用 SQLite に分離可能
- OpenAI API 呼び出しは明示的に API キーを渡すか環境変数を参照

---

## 主な機能一覧

- portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier
- research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary
- ai
  - news_nlp.score_news: ニュースを LLM でスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースでレジーム判定
- execution
  - OrderManager（注文状態遷移、送信/同期）
  - Reconciler（起動時の注文/ポジション照合）
  - run_execution.py: ExecutionEngine 起動スクリプト（paper_trading モードあり）
- monitoring
  - MonitoringDB（SQLite スキーマ初期化 / CRUD）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - MonitoringEngine: 複数モニタを束ねるポーリングループ
  - run_monitoring.py: SystemMonitor を単体でポーリングする起動スクリプト
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- tools
  - paper_verification_report.py: Paper Trading 用検証レポート生成

---

## セットアップ手順

前提
- Python 3.10 以上（モジュール内で型注釈に | が使われています）
- OS により一部機能（プロセス優先度設定、CPU affinity）が制限されます

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて他の依存を追加）

   ※ requirements.txt が無ければ上記の主要パッケージを個別にインストールしてください。

4. データディレクトリを作成（任意）
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（デフォルト含む）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（監視アラート送信に使用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading のモック成行応答: instant | partial | never | reject、デフォルト: instant）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒を上書き）
     - LOG_LEVEL（INFO 等）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視の閾値）
     - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリア

6. 初回 DB 初期化
   - run_monitoring.py / run_execution.py の起動時に init_monitoring_db() が呼ばれて監視用 SQLite テーブルを作成します。
   - 手動で初期化したい場合は Python REPL で MonitoringDB または init_monitoring_db を呼ぶことも可能。

---

## 使い方

ここでは代表的なコマンド例を示します。モジュールはパッケージとして実行できるように if __name__ == "__main__" を備えています。

1. 監視プロセス（SystemMonitor のポーリング）
   - 簡易起動:
     - MONITOR_POLL_INTERVAL 環境変数で秒数を上書きできます（デフォルト 60 秒）。
     - 実行:
       - python -m kabusys.run_monitoring
   - 役割:
     - プロセス優先度を "high" に設定（可能な場合）
     - 監視データを sqlite に保存（監視テーブルは init_monitoring_db による冪等作成）
     - DuckDB には本番 duckdb_path を使用

2. Execution エンジン（取引実行）
   - 本番／ペーパートレードの切替:
     - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
   - 実行:
     - python -m kabusys.run_execution
   - 役割:
     - プロセス優先度を "high" に設定
     - ブローカークライアント生成 → OrderRepository / OrderManager / RiskManager / Reconciler 組立て → ExecutionEngine.run_session()

3. 監視ダッシュボード（Streamlit）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 備考:
     - デフォルトで監視DBに read-only 接続（URI に ?mode=ro を付与）
     - MonitoringEngine を先に起動していないとデータがない旨が表示されます

4. Paper Trading 検証レポート
   - 使い方:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を指定する場合:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 出力:
     - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定を標準出力に表示

5. AI 系機能（プログラム的利用）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルに書き込みます
     - api_key が None の場合は OPENAI_API_KEY 環境変数を参照
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルへ日次レジーム判定を書き込みます
   - 注意:
     - OpenAI の呼び出しはネットワークエラー・レート制限等に対してリトライやフォールバックロジックを持ちますが、API キーの管理・コストに注意してください

6. プロセス停止制御（Kill Switch）
   - KillSwitch は監視で条件を満たした場合に flag ファイル（デフォルト data/kill.flag）を書き、ExecutionEngine に停止指示を出します。
   - ExecutionEngine は起動時に kill.flag のクリア設定（KILL_FLAG_CLEAR_ON_START）を参照できます。

---

## 環境変数（主要）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
- PID_FILE_PATH: ExecutionEngine PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- LOG_LEVEL: "DEBUG"/"INFO"/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

詳細は kabusys.config.Settings のプロパティ実装を参照してください。

---

## 主要なファイル / モジュール説明

- src/kabusys/config.py
  - 環境変数の自動読み込み (.env / .env.local)、Settings クラス（環境変数のラップ）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード考慮）
- src/kabusys/monitoring/
  - monitoring_db.py: SQLite スキーマ定義と MonitoringDB クラス
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 個別監視ロジック
  - monitoring_engine.py: 複数監視を束ねるエンジン
  - alert_manager.py: LINE による通知
  - kill_switch.py: 停止フラグ管理
  - streamlit_dashboard.py: Streamlit ダッシュボード
- src/kabusys/execution/
  - order_manager.py, reconciler.py, ...（注文管理・リコンシリエーション）
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
- src/kabusys/research/
  - factor_research.py, feature_exploration.py（ファクター計算・分析）
- src/kabusys/ai/
  - news_nlp.py（ニュースセンチメント）, regime_detector.py（市場レジーム判定）
- src/kabusys/tools/paper_verification_report.py
  - Paper Trading の検証レポート生成スクリプト
- src/kabusys/utils/process_priority.py
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## ディレクトリ構成（抜粋）

例:

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py
- utils/
  - __init__.py
  - process_priority.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（その他の execution モジュール）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- tools/
  - __init__.py
  - paper_verification_report.py

（上記はリポジトリの主要ファイルのみ抜粋しています）

---

## 運用上の注意 / 実装メモ

- DB マイグレーション:
  - init_monitoring_db は冪等でテーブルとインデックスを作成し、既存カラムの追加（ALTER TABLE）も行います。
- paper_trading:
  - 完全に本番 DB と分離します。PAPER_FILL_MODE に応じたモック挙動を実装しています。
- OpenAI 呼び出し:
  - レート制限・ネットワーク断・5xx に対するリトライ実装とフォールバック（ゼロやスキップ）を内包していますが、実際の運用ではコスト管理とエラーハンドリングの検討が必要です。
- プロセス優先度設定:
  - set_process_priority はプラットフォーム差を吸収しますが、権限不足等で設定されない場合があります（警告ログのみ）。
- kill.flag:
  - KillSwitch がフラグを書き込むと ExecutionEngine が停止する仕組み。既存フラグの再書き込みは行いません（冪等）。

---

## 開発・テスト

- 自動テストや CI の設定は含まれていません。モジュールはユニットテストを書きやすい純粋関数／副作用分離の設計を目指しています（例: portfolio 関数群は DB 参照なし）。
- AI 呼び出し部分は外部依存が強いため、テスト時に API 呼び出し関数をモック（unittest.mock.patch）してください。

---

必要であれば、README にセクションを追加します（例: API ドキュメント、設定ファイルのテンプレート .env.example、起動スクリプトの systemd サービス例など）。どの情報を追記したいか教えてください。