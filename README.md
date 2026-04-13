# KabuSys — 日本株自動売買システム（README）

本リポジトリは日本株向けの自動売買システム KabuSys のコードベースです。戦略・銘柄選定・ポジションサイジング、Execution（発注）周り、監視（Monitoring）、研究／ファクター計算、ニュースNLP による AI スコアリングなどを含みます。

以下、概観・機能一覧・セットアップ手順・基本的な使い方・ディレクトリ構成を日本語でまとめます。

注意: 実運用（live）で使用する場合は十分なテスト・安全対策（API 鍵管理、アクセス権、ペイロード検証、サンドボックス等）を行ってください。

---

## プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群。
- 主な機能:
  - シグナルからの銘柄選定、重み付け、ポジションサイジング
  - 発注管理（OrderManager / ExecutionEngine / BrokerClientFactory 経由）
  - 起動時のリコンシリエーション（Reconciler）による自動復旧
  - 監視（System / Trade / Risk）と Kill Switch、LINE 通知
  - Paper Trading 用の分離データベース、検証用レポート生成ツール
  - DuckDB を用いたファクター計算・研究用ユーティリティ
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価とレジーム判定

---

## 主な機能一覧
- 設定管理
  - .env/.env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）
  - Settings クラス経由で各種環境変数を取得・バリデーション
- Execution（発注）
  - OrderManager: 注文ライフサイクル管理（作成・送信・同期）
  - Reconciler: 起動時の OrderSent 照合・ポジション差分チェック
  - Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- Monitoring（監視）
  - SystemMonitor: CPU/Memory/Disk、Execution プロセス存在、データ鮮度監視
  - TradeMonitor: 注文滞留（stale order）、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション数上限チェック、dashboard 更新
  - KillSwitch: 条件を満たしたら data/kill.flag を書き込んで Execution 停止指示
  - AlertManager: LINE Push によるアラート通知（クールダウン付き）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio（銘柄選定 / ウェイト / サイジング）
  - 候補選定、等配分 / スコア加重、リスクベースの株数計算、セクターキャップ、レジーム乗数
- Research（研究）
  - DuckDB を利用したファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（ニュース）
  - news_nlp: raw_news を集約して OpenAI へ投げ、銘柄ごとの ai_score を ai_scores テーブルに書込
  - regime_detector: 1321（ETF）MA200 乖離 + マクロニュースセンチメントで日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## セットアップ手順（開発環境向け）
以下は最小限の手順例です。実際はプロジェクトの requirements.txt を用意して pip install を行ってください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

   補足: このコードは Python 3.10+ の構文（| 型注釈など）を使用しています。3.10 以上を推奨します。

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   実運用では:
   - pip install -r requirements.txt を提供している場合はそれを使用してください。

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主な環境変数（Settings で要求される・利用されるもの）
   - JQUANTS_REFRESH_TOKEN         （必須）
   - KABU_API_PASSWORD             （必須）
   - OPENAI_API_KEY                （AI 機能利用時に必須）
   - KABUSYS_ENV                   （development / paper_trading / live、デフォルト: development）
   - PAPER_FILL_MODE               （paper_trading の注文成行処理モード: instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH     （paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
   - SQLITE_PATH                   （monitoring 用 SQLite、デフォルト: data/monitoring.db）
   - DUCKDB_PATH                   （DuckDB ファイル、デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH                 （Execution 用 PID ファイルパス、デフォルト: data/execution.pid）
   - KILL_FLAG_PATH                （kill flag ファイルパス、デフォルト: data/kill.flag）
   - LOG_LEVEL                     （DEBUG/INFO/...）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （LINE 通知）

   例 (.env)
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   ```

---

## 使い方（主要スクリプト）
- ExecutionEngine を起動（通常は systemd 等でデーモン化）
  - python -m kabusys.run_execution
  - Paper Trading で実行する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading 時は settings.paper_sqlite_path（data/paper_trading.db 等）を利用し、本番 DB と分離されます。

  起動時にプロセス優先度を high に設定し、各種コンポーネントを組み立てて ExecutionEngine.run_session() を起動します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番 monitoring.db）を使用します（KABUSYS_ENV に依らず本番パスを使う点に注意）。

- Streamlit ダッシュボード（監視表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで可視化（読み取り専用モードで DB を開きます）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db オプションで変更可能）

- AI / 研究用ユーティリティ
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime 等のテーブルに書き込みを行います。OPENAI_API_KEY が未設定の場合は例外になります。

---

## 動作上の注意・トラブルシュート
- 自動 .env ロード:
  - プロジェクトルートが .git または pyproject.toml を基に判定されます。ルート検出に失敗すると自動ロードはスキップされます。
  - テスト時などで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- Process priority / CPU affinity:
  - set_process_priority() は psutil を使います。権限不足で設定できない場合は警告になります（処理は継続）。
- OpenAI API:
  - OPENAI_API_KEY 未設定だと news_nlp.score_news / regime_detector.score_regime は ValueError を投げます。テストやオフライン実行時はキーを渡さないで呼ばないかモックしてください。
  - API 呼び出しはリトライ・バックオフを実装していますが、コストとレート制限に注意。
- DB マイグレーション:
  - init_monitoring_db() は起動時にテーブルの存在を保証し、必要に応じてカラム追加（簡易マイグレーション）を行います。
- Paper Trading と本番 DB の分離:
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を用いるため本番監視 DB とデータが混ざりません。
  - ただし monitoring は本番 sqlite_path を使用するため、監視と実行が混同しないよう環境変数を適切に設定してください。
- レポートツールが DB を開けない場合:
  - "Database not found" 等のエラーが出たらパスを確認してください（--db オプション、環境変数 PAPER_TRADING_SQLITE_PATH）。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル／パッケージと簡単な説明です。

- kabusys/
  - __init__.py
    - パッケージメタ情報（__version__ 等）
  - config.py
    - Settings クラス：環境変数の読み込み・バリデーション、.env 自動ロード
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/
    - run_execution.py: ExecutionEngine 起動スクリプト
    - order_manager.py: Order 管理（作成 / 送信 / 同期）
    - reconciler.py: 起動時リコンシリエーション（注文・ポジション同期）
    - order_repository.py, order_record.py, broker_api.py, broker_factory.py …（発注に関する実装）
  - monitoring/
    - run_monitoring.py: SystemMonitor ポーリングループ起動
    - monitoring_db.py: SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py: 注文滞留・約定異常検出
    - risk_monitor.py: DD / ポジション上限監視
    - kill_switch.py: kill.flag 書込み（Execution 停止シグナル）
    - alert_manager.py: LINE Push 通知
    - monitoring_engine.py: 各 Monitor を束ねてポーリングするエンジン
    - streamlit_dashboard.py: Streamlit による可視化
  - portfolio/
    - portfolio_builder.py: 候補選定 / スコアソート
    - position_sizing.py: 株数計算（risk_based, equal, score）
    - risk_adjustment.py: セクターキャップ / レジーム乗数
  - research/
    - factor_research.py: momentum / value / volatility ファクター計算（DuckDB）
    - feature_exploration.py: forward returns / IC / factor summary
  - ai/
    - news_nlp.py: raw_news を OpenAI で評価して ai_scores へ書き込み
    - regime_detector.py: ETF MA200 とマクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成 CLI

（省略されているファイルもありますが、上記が主要な機能境界です）

---

## よくあるコマンドまとめ
- 実行（開発）
  - python -m kabusys.run_execution
- 監視
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 貢献・拡張案（参考）
- stocks マスタに単元（lot_size）や銘柄メタデータを追加して position_sizing を拡張
- FX / 海外銘柄対応（時差・営業時間差・通貨換算）
- リアルタイム監視の強化（Prometheus / Grafana 連携）
- テストカバレッジの拡充（unit / integration、OpenAI 呼び出しはモック化）

---

README の内容は現状のコードベース（src/kabusys 配下）に基づいてまとめています。追加の要望（環境変数一覧のテンプレート、運用手順書、systemd ユニット例、CI 設定など）があれば追記します。