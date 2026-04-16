# KabuSys

日本株向けの自動売買システム（モジュール群）。注文実行・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリングなど、実運用を想定したコンポーネント群を含みます。

---

概要
- ExecutionEngine: ブローカーとの発注・注文状態管理・リコンシリエーション
- Monitoring: システム状態 / 注文異常 / リスク監視、LINE 通知、監視ダッシュボード
- Portfolio: 銘柄選定・重み計算・ポジションサイズ決定・セクター制約
- Research: DuckDB を用いたファクター計算・特徴量解析
- AI: ニュース NLP（OpenAI）による銘柄別センチメント、レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボード起動スクリプト等

本リポジトリの設計方針（抜粋）
- DuckDB / SQLite をデータ層に採用（分析は DuckDB、監視ログは SQLite）
- 実運用を想定しフェイルセーフを多用（API 失敗時はフォールバック、部分書き込み保護など）
- ルックアヘッドバイアス防止（date.today()/datetime.today() に依存しない実装）
- テスト容易性の確保（外部 API 呼び出し部分は差し替え可能）

---

主な機能一覧
- Execution
  - ExecutionEngine（起動/停止、セッション実行）
  - OrderManager / OrderRepository（発注フロー、DB 永続化）
  - Reconciler（再起動時の注文・ポジション突合）
  - RiskManager（注文件数/ポジション利用率等の制約）
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス監視、データ鮮度判定）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（しきい値超過で停止フラグ書き込み）
  - AlertManager（LINE へのプッシュ通知）
  - Streamlit ダッシュボード（監視 UI）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - news_nlp：OpenAI を使ったニュースセンチメント集計 → ai_scores 書き込み
  - regime_detector：ETF（1321）MA200 とマクロニュースを合成した市場レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB を集計して検証レポートを生成

---

動作要件（目安）
- Python 3.10+
- 主な Python ライブラリ
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite（Python 標準ライブラリで利用）
- ネットワークアクセス（LINE API / OpenAI / ブローカー API）

（requirements.txt は本コード断片に含まれていません。導入環境では上記パッケージを pip でインストールしてください。）

例:
pip install duckdb psutil requests openai streamlit

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. data ディレクトリを作成（DB / PID / フラグ用）
   - mkdir -p data
5. 環境変数を設定
   - .env や .env.local をプロジェクトルートに置くか、OS 環境変数で設定します。
   - 自動で .env/.env.local が読み込まれます（無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）
6. データベース初期化
   - Monitoring 系はスクリプト起動時にテーブル作成（init_monitoring_db）を行います。
   - DuckDB / Paper Trading DB 等は別途データ投入が必要（分析用テーブル: prices_daily, raw_financials 等）。

---

環境変数（主なもの・デフォルト値）
- KABUSYS_ENV
  - 値: development, paper_trading, live
  - default: development
  - paper_trading の場合、MockBrokerClient と data/paper_trading.db を使用
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合、必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（監視アラート送信に使用）
- PAPER_FILL_MODE (paper_trading 用)
  - instant | partial | never | reject（default: instant）
- PATHs / DB
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — 監視ログ用
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID / フラグ
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- モニタリング閾値
  - CPU_THRESHOLD_PCT (default: 90.0)
  - MEMORY_THRESHOLD_PCT (default: 85.0)
  - DISK_THRESHOLD_PCT (default: 90.0)
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60 秒。0 以下の値は無効扱いでデフォルトにフォールバック。
- LOG_LEVEL（DEBUG/INFO/...、default: INFO）

---

使い方（主なコマンド例）

1) 実行エンジン（ExecutionEngine）起動
- Production / Live:
  KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  （paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込まれます）

run_execution の挙動:
- 起動時に高優先度にプロセス優先度を設定（set_process_priority("high")）
- stop フラグ（data/stop_requested.flag）があれば起動しない
- エンジンは別スレッドで run_session を走らせ、フラグ検知で停止

2) 監視ループ起動（SystemMonitor 単体の簡易起動）
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可（デフォルト 60）
- 監視は常に production の sqlite_path（Settings.sqlite_path）を参照する設計になっています

3) Streamlit ダッシュボード起動（監視 UI）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視用 SQLite DB を read-only で開いて表示します

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db（--db で上書き可）
- 出力は標準出力にテキストレポートを生成

5) AI 関連（ライブラリ呼び出しとして）
- kabusys.ai.score_news(conn, target_date, api_key=...)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
- OpenAI API キーが必要。API 呼び出し部分はテストで差し替え可能。

停止・緊急停止
- 実行中の ExecutionEngine を停止させるには kill.flag を生成する（KillSwitch の設計により、KillSwitch が書き込む場合もあり）。KillSwitch は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）を書きます。
- run_execution/run_monitoring は data/stop_requested.flag の存在を監視してループを抜けます（手動で作成することで停止信号を送れます）。

ロギング
- 各スクリプトは logging.basicConfig(level=logging.INFO) で起動します。
- Settings.log_level による制御が随所で利用可能です（必要に応じてコード内で取得してセットしてください）。

---

ディレクトリ構成（主要ファイル抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定読み込みロジック
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py
    - execution/                 — 発注関連（OrderManager, Repository, Reconciler, Engine, BrokerFactory 等）
      - order_manager.py
      - reconciler.py
      - ...
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - utils/
      - process_priority.py
    - data/                      — 実行時に利用する DB / PID / フラグを置くことを想定（git 管理除外推奨）

---

補足／注意事項
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離して data/paper_trading.db に書きます。実機テスト時は安全に挙動確認ができます。
- OpenAI / ブローカー API 呼び出し部分はリトライやバックオフ処理、フェイルセーフを備えていますが、API 利用にはキーやネットワーク等の準備が必要です。
- streamlit を使うダッシュボードは SQLite を read-only モードで開きます。監視 DB が存在しない場合はエラー表示されます。
- 実運用では PID・フラグファイル（data/execution.pid, data/kill.flag, data/stop_requested.flag）の管理に注意してください。

---

開発／貢献
- ユニットテストやモック化がしやすい構造を意識しているため、外部 API 呼び出し部分（OpenAI クライアントなど）は差し替えてテスト可能です。
- 新しい機能を追加する場合は、まずローカル環境で DuckDB / SQLite に必要なスキーマを用意してから実装・検証してください。

---

問い合わせ・参考
- README に書かれている環境変数・挙動を参照し、環境を整えた上で各モジュールを起動してください。
- 追加の運用手順やデプロイ手順（systemd ユニットやコンテナ化）はこの README に含めていません。運用環境に応じてプロセス管理/ログ集約等を行ってください。

以上。必要に応じて README に追記（例: requirements.txt、.env.example の内容、systemd 例など）しますので、希望があれば教えてください。