KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株の自動売買・検証・監視に関する主要コンポーネント群（ExecutionEngine / Monitoring / Research / Portfolio / AI 補助等）を含む軽量フレームワークです。  
README はコードベース（src/kabusys 配下）から主要仕様・使い方を抽出して日本語でまとめたものです。

要点
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）はプロセス分離され、それぞれ起動スクリプトを持ちます。
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB と分離して data/paper_trading.db に書き込みます。
- 監視は SQLite（monitoring.db）へ永続化し、Streamlit ベースのダッシュボードを提供します。
- ニュースの NLP（OpenAI）やレジーム判定は ai モジュールで実装されています（OpenAI API キーが必要）。

主な機能
- Execution
  - ブローカー抽象化（BrokerClientFactory）を用いた発注管理
  - リコンシリエーション（再起動後の注文同期）
  - OrderManager / RiskManager / Reconciler 等の実装（注文ライフサイクル管理）
- Monitoring
  - システム状態（CPU/メモリ/ディスク/プロセス）監視と永続化
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視と Kill Switch（停止フラグ file）発動
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（data/monitoring.db を読み取り専用で表示）
- Research / Portfolio
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン・IC 計算、特徴量サマリ
  - 銘柄選定・等重/スコア重み・リスクベースのポジションサイズ計算
  - セクター集中制限・レジーム乗数
- AI
  - ニュースを OpenAI（gpt-4o-mini 等）で評価して銘柄別 ai_score を生成（ai.score_news）
  - マクロ記事 + ETF MA を組み合わせて日次レジーム判定（score_regime）
- ツール
  - paper_verification_report：Paper Trading の検証レポート出力（成功率・稼働率・レイテンシ等）

必要な依存（主なもの）
- Python 3.9+
- duckdb
- psutil
- requests
- openai（OpenAI Python SDK）
- streamlit（ダッシュボードを使う場合）
- sqlite3（標準ライブラリ）
- （必要に応じて）その他パッケージ

セットアップ手順（開発/簡易ローカル実行）
1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
2. 必要パッケージをインストール（requirements.txt があればそれを使うのが簡単）
   - pip install duckdb psutil requests openai streamlit
   - （開発用に追加パッケージがあれば適宜インストール）
3. データディレクトリ作成
   - mkdir -p data
4. 環境変数設定（.env をプロジェクトルートに置くことが想定）
   - 自動で .env / .env.local が読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...            （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60      （監視ループの秒間隔、デフォルト60）
   - .env のパースはシェル風の export / 引用 / コメントをある程度サポートします（Config モジュール参照）。
5. 初期 DB（必要に応じて）
   - monitoring は起動時にスキーマを自動で初期化します（init_monitoring_db）。

基本的な使い方（起動コマンド例）
- 監視プロセス起動（MonitoringEngine のポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例：MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視用 DB は本番環境に関係なく本番 sqlite_path を参照する実装）。
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag（プロジェクトルートの data/stop_requested.flag）が存在するとエンジンは起動せず終了します。停止は data/stop_requested.flag / data/kill.flag により通知されます。
- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview・Positions・Orders・System タブを提供します。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  （開始日）
    - --to YYYY-MM-DD    （終了日）
    - --db PATH          （SQLite DB パス、環境変数 PAPER_TRADING_SQLITE_PATH と併用可能）
  - 指標: 稼働率・注文成功率・送信率・P95 レイテンシ等を表示し PASS/FAIL を判定します。

重要ファイル / フラグ
- data/monitoring.db （デフォルトの監視 SQLite）
- data/kabusys.duckdb （DuckDB データ格納：prices_daily 等）
- data/paper_trading.db （Paper Trading 用 SQLite）
- data/execution.pid （ExecutionEngine の PID ファイル）
- data/kill.flag （KillSwitch が書き込む停止フラグ）
- data/stop_requested.flag （run_* スクリプトが監視する停止フラグ）

Monitoring DB スキーマ（自動初期化）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の単一行で集計情報を保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

設計上の注意事項 / 運用メモ
- Settings（kabusys.config）モジュールは .env を自動ロードします（プロジェクトルートの探索は .git または pyproject.toml を基準）。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。
- KABUSYS_ENV の有効値は development, paper_trading, live。paper_trading は DB を分離して安全に検証できます。
- Process priority の設定: run_monitoring / run_execution 起動時にプロセス優先度を "high" に設定しようとします。失敗してもログに警告を出して継続します。
- OpenAI を用いる機能（ai.score_news, ai.regime_detector）は API キーが必要です。API 呼び出しの失敗はフェイルセーフ（スコアを 0 またはスキップ）で処理を継続します。
- KillSwitch（監視 → 実行 engine 停止）は data/kill.flag の書き込みで発動します。ExecutionEngine は起動中にこのフラグを検知すると安全に停止します。
- Paper Trading の検証レポートや AI 処理は外部 API（OpenAI）に依存する箇所があるため、ローカル検証時は API キーの準備またはモックが必要です。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / .env 読み込みと Settings クラス
    - run_monitoring.py                 — Monitoring ポーリングループ起動スクリプト
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py    — Paper Trading 検証レポート CLI
    - ai/
      - news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py              — マクロ + MA によるレジーム判定（OpenAI）
      - __init__.py
    - monitoring/
      - monitoring_db.py                — monitoring DB 初期化 / 永続化クラス
      - monitoring_engine.py            — 各 Monitor を束ねるエンジン
      - system_monitor.py               — CPU/mem/disk/process/data freshness チェック
      - trade_monitor.py                — 注文滞留 / 約定異常チェック
      - risk_monitor.py                 — ドローダウン/ポジション上限監視
      - kill_switch.py                  — kill.flag の読み書き
      - alert_manager.py                — LINE push 通知
      - streamlit_dashboard.py          — Streamlit ダッシュボード
      - __init__.py
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - execution_engine.py
      - broker_factory.py
      - broker_api.py
      - ...（実行関連コンポーネント）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/ (実行時生成を想定、Git 管理外)
      - monitoring.db
      - kabusys.duckdb
      - paper_trading.db
      - execution.pid
      - kill.flag
      - stop_requested.flag

よくある運用コマンド（例）
- 監視開始:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン開始（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

追加の参考
- 設定・環境変数の読み込みルールは kabusys.config を参照してください（.env/.env.local の優先度、保護キー、値のバリデーション等）。
- MonitoringDB のスキーマ変更は init_monitoring_db に記載のマイグレーションロジックを確認してください（既存 DB にカラムがない場合の ALTER 等）。
- OpenAI 呼び出しや外部 API のエラー処理はフェイルセーフを重視していますが、本番運用時は API レート制限やコストに注意してください。

この README はコード内の docstring / コメントを元に要約しています。より詳細な設計・アルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）は別ドキュメントを参照してください（リポジトリに含まれている場合）。質問や追記したい点があれば教えてください。