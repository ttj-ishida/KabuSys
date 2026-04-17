KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 監視 / 研究用ライブラリ群です。  
主要機能は以下のとおりです。

- 実行エンジン（ExecutionEngine）による発注・リスク管理・リコンシリエーション
- 監視エンジン（MonitoringEngine）によるプロセス・リスク・注文監視、LINE 通知、kill-switch
- Paper Trading 用の分離された DB と Mock ブローカー
- ファクター計算・リサーチユーティリティ（DuckDB 経由でのファクター計算）
- ニュース NLP（OpenAI を利用した銘柄別センチメントスコア付与）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ算出・セクター制約）
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

主な設計方針
- 本番 DB と paper_trading DB を分離（実行時の KABUSYS_ENV による）
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない等）
- 外部 API 呼び出しは明示的に渡す（OpenAI の API キーは引数か環境変数で指定）
- フェイルセーフ（API 失敗時はフォールバック動作、監視は継続）

機能一覧
---------
- Execution
  - ブローカー抽象（BrokerClientFactory）
  - OrderManager / OrderRepository（注文生成・状態管理・DB 永続化）
  - Reconciler（再起動時リコンシリエーション）
  - RiskManager（ポジション・利用率・ドローダウン等のリスク制御）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（停止フラグ書き込みによる ExecutionEngine 停止）
  - AlertManager（LINE への通知）
  - Streamlit ダッシュボード（監視データの可視化）
- Research / Data
  - DuckDB を用いたファクター計算（momentum / volatility / value 等）
  - 将来リターン・IC 計算、特徴量サマリー
- AI
  - news_nlp: ニュースを集約して OpenAI による銘柄別センチメント算出 → ai_scores へ保存
  - regime_detector: ma200 とマクロニュースを合成して市場レジームを判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、成功率、レイテンシ等）

セットアップ
-------------
1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（プロジェクトに requirements.txt が無い場合の参考）
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて）numpy 等を追加
4. プロジェクトルートに .env を作成（自動で読み込まれます。読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

推奨の主要環境変数（.env 例）
- KABUSYS_ENV=development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- PAPER_FILL_MODE=instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

重要な動作上の注意
- 監視（monitoring）は KABUSYS_ENV に関係なく本番の sqlite_path（SQLITE_PATH）を使用します（監視ログを本番 DB に記録する設計）。
- 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading のとき専用の PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と完全に分離します。
- 自動で .env/.env.local を読み込みます（OS 環境変数が優先）。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

使い方
-------

1) 監視ループを起動（プロセス優先度を高に設定）
- 起動:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
- 停止:
  - プロジェクトルート/data/stop_requested.flag を作成するとループは安全終了します（または Ctrl+C）。

2) 実行エンジンを起動（ExecutionEngine）
- 起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録
  - 実行中は data/execution.pid を書き、stop は stop_requested.flag ファイルで受け付ける
- 停止:
  - stop_requested.flag を作成するとエンジンを停止します

3) Paper Trading 検証レポートを生成
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 指定期間: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/data/paper_trading.db
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

4) Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System のタブで表示

5) AI / レジーム判定
- news_nlp.score_news(conn, target_date, api_key=None)
  - duckdb 接続を渡して呼び出す。api_key を省略すると環境変数 OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None)

運用フローと kill-switch
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を使って定期チェックを行います。
- KillSwitch は RiskMonitor の検出結果（ドローダウン超過やポジション上限超過）により data/kill.flag を作成し ExecutionEngine に停止シグナルを送ります。
- AlertManager は LINE Messaging API への一方向通知を行います（チャンネルが設定されていない場合はログのみ）。

主要ファイルとディレクトリ構成
--------------------------------
（プロジェクトルート: src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py                — パッケージ定義、__version__
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト

- src/kabusys/execution/
  - execution_engine.py        — 実行エンジン本体（起動・セッション管理）
  - broker_factory.py          — ブローカークライアントファクトリ（Mock/実ブローカー切替）
  - broker_api.py              — ブローカー API インターフェース定義
  - order_repository.py        — SQLite ベースの注文永続化
  - order_manager.py           — OrderManager（注文生成・同期・キャンセル等）
  - reconciler.py              — 再起動時のリコンシリエーション
  - risk_manager.py            — リスク管理ロジック
  - order_record.py            — OrderRecord / OrderState 定義

- src/kabusys/monitoring/
  - monitoring_db.py           — 監視用 SQLite スキーマと永続化 API（MonitoringDB）
  - system_monitor.py          — システム監視（CPU/メモリ/プロセス/データ鮮度）
  - trade_monitor.py           — 注文滞留・約定異常監視
  - risk_monitor.py            — ドローダウン / ポジション上限監視
  - kill_switch.py             — kill.flag 管理
  - alert_manager.py           — LINE 通知クライアント
  - monitoring_engine.py       — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py     — Streamlit ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py       — 候補選定・重み計算（等重/スコア重み）
  - position_sizing.py         — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py         — セクター制限・レジーム乗数

- src/kabusys/research/
  - factor_research.py         — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py     — 将来リターン・IC・統計サマリ

- src/kabusys/ai/
  - news_nlp.py                — ニュース集約 → OpenAI で銘柄別スコア算出
  - regime_detector.py         — ma200 とマクロニュースを合成してレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- src/kabusys/utils/
  - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ

データ / デフォルトパス
- data/monitoring.db          — 監視ログ（デフォルト: SQLITE_PATH）
- data/paper_trading.db      — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb        — DuckDB ファイル（DUCKDB_PATH）
- data/execution.pid         — 実行エンジン PID（pid ファイル、Settings.pid_file_path）
- data/kill.flag             — KillSwitch が書き込む停止フラグ
- data/stop_requested.flag   — run_* スクリプトが監視する手動停止フラグ（例: CI / 管理者が作成）

開発・テストのヒント
- .env.local は .env より優先して上書き（ただし OS 環境変数は保護される）
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 関連機能は API キーが無い場合、呼び出し時に ValueError を送出するためテスト時はモック化推奨
- MonitoringDB.init_monitoring_db は冪等（既存スキーマに対する最小限のマイグレーション対応あり）
- DuckDB 接続をテストで利用する場合はメモリや一時ファイルを利用して isolation を保つ

ライセンス・注意事項
- このリポジトリは自動売買のためのサンプル実装です。実取引での利用は各自の責任で行ってください。API キー・パスワード等の機密情報は必ず環境変数で管理してください。

質問・導入サポート
------------------
導入時の環境変数のサンプルや実行トラブルの情報（エラーログ、使用 OS、Python バージョン等）を教えていただければ、より具体的なサポートを提供します。