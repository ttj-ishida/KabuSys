README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python コードベースです。本リポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン（ExecutionEngine）: シグナルに基づく発注ループ、リスクゲート、ブローカーとの同期・再同期機能
- 監視（Monitoring）: システム状態・注文滞留・リスク監視、LINE へのアラート送信、kill flag による安全停止
- ポートフォリオ構築: 候補選定、重み算出、ポジションサイズ計算、セクター制約・レジーム補正
- 研究（Research）: DuckDB 上でのファクター計算、将来リターン・IC 計算、特徴量サマリ
- AI モジュール: ニュースの NLP によるセンチメントスコアリング（OpenAI）、市場レジーム判定
- ユーティリティ: 設定管理（.env ロード）、プロセス優先度設定、Streamlit ダッシュボードなど

主な設計方針は「本番 DB と paper_trading の分離」「ルックアヘッドバイアスを防ぐ」「API エラーはフェイルセーフにフォールバックする」など安全性と再現性重視です。

機能一覧
--------
- Execution
  - Signal を読み取り Order を作成 → ブローカーへ送信（強固な永続化手順）
  - 再起動後のリコンシリエーション（Reconciler）
  - Gate 系リスクチェック（signal レベル・実行レベル・ドローダウン等）
  - paper_trading モード（MockBroker）で本番 DB と完全分離
- Monitoring
  - CPU / メモリ / ディスク / プロセス状態の定期ログ（SQLite）
  - 注文の滞留検出・約定価格異常検出
  - ドローダウン・ポジション上限監視と kill.flag 書き込み
  - LINE によるアラート送信（クールダウン管理）
  - Streamlit による監視ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定（スコア降順）、等金額/スコア加重/リスクベース配分
  - セクターキャップ制御、レジームに応じた投下資金乗数
  - 単元株 (lot) に応じた株数丸め・アグリゲート制約対応
- Research / AI
  - DuckDB を用いたモメンタム・ボラティリティ・バリュー等ファクター計算
  - 将来リターン、IC、ファクター統計サマリ
  - raw_news を OpenAI (gpt-4o-mini) に投げるニューススコアリング（ai_scores へ保存）
  - マクロニュース + ETF ma200 乖離から市場レジーム判定（market_regime テーブルへ保存）

セットアップ手順
----------------

前提
- Python 3.10+（typing | の union 表記が使われています）
- システムに sqlite3, duckdb を操作できる環境（duckdb は Python パッケージ）
- 適切な API キー（OpenAI 等）、およびブローカーの設定

1. リポジトリをクローンし、ソースパスを有効にする
   - 開発環境ではプロジェクトルートに requirements をインストールし、editable インストールを推奨します:
     - python -m venv .venv
     - source .venv/bin/activate (Windows は .venv\Scripts\activate)
     - pip install -U pip
     - pip install -e .   （pyproject.toml/setup.cfg がある場合）

   もしパッケージ化せず直接実行する場合は PYTHONPATH=src を設定:
     - export PYTHONPATH=src

2. 必要なパッケージ（代表例）
   - duckdb
   - psutil
   - requests
   - streamlit
   - openai
   - これらは pyproject / requirements にまとめてある想定ですが、個別にインストールする場合:
     - pip install duckdb psutil requests streamlit openai

3. 環境変数（.env）を用意
   - プロジェクトルートの .env/.env.local を自動読み込みします（OS 環境変数が優先）。
   - 主要な環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60 (秒、run_monitoring のポーリング間隔を上書き)
     - LOG_LEVEL=INFO

   - テストや CI で自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化
   - monitoring 用 SQLite はスクリプト実行時に init_monitoring_db() が呼ばれて作成されます。
   - DuckDB（data/kabusys.duckdb）はファクター計算や raw_financials/prices_daily テーブルが必要です。データ投入は別途パイプライン（kabusys.data.pipeline）等で準備してください。

使い方
------

1. 実行エンジン（本番 / paper_trading）
   - KABUSYS_ENV に応じて paper_trading と本番 DB が切り替わります。paper_trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
   - 起動:
     - python -m kabusys.run_execution
     - （もしくは）python src/kabusys/run_execution.py
   - ログレベルは環境変数 LOG_LEVEL で調整可能。
   - 起動時に PID ファイル（Settings.pid_file_path）を書き込み、kill.flag を検知すると安全停止します。
   - kill.flag を手動でクリアしたい場合は（ファイルを削除）、または KillSwitch.clear() を利用します。

2. 監視プロセス
   - System / Trade / Risk をポーリングして monitoring DB にログを残し、必要時に kill.flag を書きます。
   - 起動:
     - python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
   - 監視は常に本番用の sqlite_path を参照します（KABUSYS_ENV に関係なく本番 monitoring DB を使用）。

3. Streamlit ダッシュボード（読み取り専用）
   - 監視 DB（読み取り専用 URI）を参照して簡易ダッシュボードを提供します。
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. AI / レジーム判定・ニューススコアリング
   - ニューススコアリング（OpenAI を利用）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")  # api_key を None にすると OPENAI_API_KEY を参照
   - 市場レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")
   - 呼び出しはスクリプトからスケジュールで実行することを想定。API キー未設定時は例外になるため注意。

5. Research / Factor 計算
   - DuckDB コネクションを渡して関数を呼ぶだけです（prices_daily / raw_financials テーブルを参照）。
     - from kabusys.research import calc_momentum, calc_volatility, calc_value
     - calc_momentum(duckdb_conn, date(2026, 3, 20))

設定と挙動のポイント
--------------------
- Settings クラス（kabusys.config.Settings）は .env 自動ロード機構を持ち、プロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- paper_trading モードでは broker は MockBroker を使い、発注ログは PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と完全分離）。
- run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使います。
- ExecutionEngine 起動時に PID ファイルを書き込み、Process 存在確認や stale PID の除去を行います。
- kill.flag が書かれると ExecutionEngine は安全に停止する設計です（KillSwitch により reason を書き込む）。

ディレクトリ構成
----------------

（src 配下がパッケージルート）主なファイル/ディレクトリ:

- src/kabusys/
  - __init__.py                     -- パッケージ定義（__version__ 等）
  - config.py                        -- 環境変数・.env 読み込み設定（Settings）
  - run_execution.py                 -- ExecutionEngine 起動スクリプト
  - run_monitoring.py                -- SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py            -- プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - execution_engine.py            -- ExecutionEngine 本体
    - order_manager.py               -- Order state machine の外向き API
    - order_repository.py            -- （DB 周りの実装は別ファイルに存在する想定）
    - reconciler.py                  -- 再起動時の照合処理
    - risk_manager.py                -- リスクゲート（Engine 依存）
    - broker_factory.py              -- Broker クライアント生成
    - broker_api.py                  -- Broker API プロトコル定義
    - order_record.py                -- OrderRecord / 状態遷移用ロジック
  - monitoring/
    - monitoring_db.py               -- SQLite テーブル初期化 + MonitoringDB ラッパ
    - system_monitor.py              -- CPU/メモリ/データ鮮度・PID チェック
    - trade_monitor.py               -- 注文滞留・約定異常チェック
    - risk_monitor.py                -- ドローダウン・ポジション数監視
    - kill_switch.py                 -- kill.flag の書き込み・管理
    - alert_manager.py               -- LINE Push 通知ラッパ
    - monitoring_engine.py           -- 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py         -- Streamlit ダッシュボード（読み取り専用）
  - portfolio/
    - portfolio_builder.py           -- 候補選定・重み計算
    - position_sizing.py             -- 株数決定 / アグリゲート制御
    - risk_adjustment.py             -- セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py             -- momentum/volatility/value 等の計算
    - feature_exploration.py         -- forward returns / IC / summary
    - __init__.py
  - ai/
    - news_nlp.py                    -- raw_news を LLM でセンチメント化して ai_scores に書込
    - regime_detector.py             -- マクロ + ETF MA200 でレジーム判定
    - __init__.py
  - data/ (想定: 外部パイプラインで投入される DuckDB / CSV 等)
    - （data/kabusys.duckdb 等）

補足・運用上の注意
------------------
- DuckDB のデータ（prices_daily, raw_financials, raw_news など）が揃っていないと研究・AI 関数は期待どおり動作しません。データ投入は別途パイプラインを用意してください。
- OpenAI など外部 API 呼び出しはネットワーク・レート制限の影響を受けます。スクリプト側はリトライやフォールバック（macro_sentiment=0.0 など）を実装していますが、API キー管理には注意してください。
- production では KABUSYS_ENV=live、適切なログ/監視設定、バックアップ戦略を整備してください。
- 本リポジトリは設計文書（コメント）を多く含み、各関数に挙動説明が書かれているため、実装の拡張やテスト作成の際に参照してください。

ライセンスや貢献
----------------
- 本 README にはライセンス情報を含めていません。実プロジェクトでは LICENSE ファイルを追加し、貢献ガイドライン（CONTRIBUTING.md）を用意してください。

以上。必要であれば「環境変数の例となる .env.example」や「よくある運用コマンド集（systemd ユニット例・Docker Compose 例）」のテンプレートも作成します。どちらを優先しますか？