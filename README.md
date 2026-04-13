# KabuSys

KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ（ファクター計算）、AI ベースのニュースセンチメント評価等のコンポーネントを含みます。

主な設計方針
- 本番環境とテスト（Paper Trading）を分離する仕組みを提供
- DuckDB を用いたファクター計算・リサーチ、SQLite を用いた監視ログ保存
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価とレジーム判定
- LINE Messaging API を用いたアラート通知
- psutil によるプロセス優先度設定・監視

---

## 機能一覧
- ExecutionEngine（発注・オーダー状態管理、リスク管理、リコンシリエーション）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor、kill-switch、AlertManager、Streamlit ダッシュボード）
- Portfolio construction（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- Research（ファクター計算: Momentum / Volatility / Value、将来リターン・IC 計算、統計サマリー）
- AI モジュール
  - news_nlp: raw_news を LLM で評価して ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して日次で市場レジームを判定
- Tools
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等の検証レポートを生成
- ユーティリティ
  - 環境変数読み込み（.env / .env.local の自動ロード）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発 / 実行）
以下は基本的なセットアップ例です。環境に応じて適宜調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell など)
   ```

3. 依存パッケージをインストール
   必要な代表パッケージ（pip）:
   ```
   pip install duckdb openai psutil requests streamlit
   ```
   ※実環境ではバージョン固定や requirements.txt を用意して管理してください。

4. データディレクトリを準備
   ```
   mkdir -p data
   ```
   SQLite / DuckDB のデフォルトパスは `data/monitoring.db` および `data/kabusys.duckdb` です。必要に応じて環境変数で上書きできます（後述）。

5. 環境変数を設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS の環境変数が優先され、`.env.local` は上書きされます）。必須のものは Settings._require に従います。

   主要な環境変数（例）
   ```
   KABUSYS_ENV=development            # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...                 # AI 機能を使う場合に必要
   LINE_CHANNEL_ACCESS_TOKEN=...      # アラート送信用（任意）
   LINE_USER_ID=...                   # アラート送信用（任意）

   # DB パス（省略時は data/... が使われる）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

   # Paper Trading の注文約定モード（instant|partial|never|reject）
   PAPER_FILL_MODE=instant

   # 監視関連
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   MONITOR_POLL_INTERVAL=60           # run_monitoring のポーリング間隔（秒）
   ```

   注意:
   - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等は必須の設定があるため、実行時に不足すると例外が発生します（Settings がチェックします）。
   - Paper Trading（KABUSYS_ENV=paper_trading）は実取引 API を使わず MockBrokerClient を使い、書き込み先 SQLite は `PAPER_TRADING_SQLITE_PATH` を参照して「本番 DB と完全分離」されます。

---

## 実行方法（代表的なコマンド）

- 監視ループ（SystemMonitor を単独で動かす）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）。
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使って監視ログを保存します。

- Execution Engine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と分離）。
  - 起動時にプロセス優先度を "high" に設定し、DB 初期化 / reconciler 等を実行します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 出力は標準出力。稼働率、注文成功率、送信率、レイテンシ（P95）等を表示し PASS/FAIL を判定します。

- Streamlit ダッシュボード（監視用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - Read-only 接続で監視 DB を表示します。MonitoringEngine を動かした後で参照してください。

- AI モジュールの呼び出し（コード内 API）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（環境変数 OPENAI_API_KEY または引数）を必要とします。

---

## 設定項目の要点（Settings）
Settings クラスで参照される主な環境変数一覧（抜粋）:

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能で必要)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信で任意)

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用; デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (Paper Trading 用; デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject

- 監視閾値（デフォルト値は Settings プロパティを参照）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

- 実行環境フラグ
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

---

## 使い方のヒント / 運用メモ
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定すると実取引 API を呼ばず専用の SQLite に記録されます。
- run_monitoring は監視用 DB を初期化するため、初回は自動でテーブルが作成されます（init_monitoring_db）。
- Kill Switch:
  - RiskMonitor が閾値を超えると KillSwitch が `data/kill.flag` を書き込み、ExecutionEngine 停止のシグナルとなります。
  - 起動時にこのフラグをクリアする挙動は `KILL_FLAG_CLEAR_ON_START` によって制御できます。
- LINE アラート:
  - token と user_id が設定されていない場合は送信をスキップしますが、ログには記録されます。
  - 同一カテゴリ/レベルの通知にはクールダウン（デフォルト 30 分）が適用されます。
- OpenAI 呼び出し:
  - news_nlp と regime_detector はリトライ（指数バックオフ）やレスポンスバリデーションを組み込んでいますが、API キーやレート制限に注意してください。
  - API の失敗はフェイルセーフで無害な既定値（例: macro_sentiment=0.0）にフォールバックする設計です。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py

- src/kabusys/monitoring/
  - monitoring_db.py        — SQLite テーブル定義 / 永続化層
  - system_monitor.py       — CPU / メモリ / データ鮮度監視
  - trade_monitor.py        — 注文滞留 / 約定異常監視
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みロジック
  - alert_manager.py        — LINE 通知送信
  - monitoring_engine.py    — 各モニタを束ねるポーリングエンジン
  - streamlit_dashboard.py  — 監視用 UI（Streamlit）

- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py
  - broker_factory.py
  - broker_api.py
  - (その他、OrderRecord 等)

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - process_priority.py

---

## 開発上の注意点 / 補足
- DB マイグレーションは簡易的に init_monitoring_db の中で実施しています（カラム追加チェック等）。複雑なスキーマ変更が必要な場合は別途マイグレーションツールを導入してください。
- DuckDB 接続はリサーチ・AI モジュールで大量の SQL を投げます。データ準備（prices_daily / raw_financials / raw_news 等）の整備が前提です。
- 実運用ではログレベル・プロセス優先度・PID 管理・監視間隔などを慎重に設定してください。
- セキュリティ: API キーやパスワードは .env に平文で置く場合の保護に注意（アクセス権やシークレット管理ツールの利用を推奨）。

---

README は以上です。実行時や開発で不明点があれば、特定のモジュール（例: news_nlp の使い方、ExecutionEngine の起動フロー、DB スキーマ）についてさらに詳しいドキュメントを作成します。必要であればどの部分を拡張するか教えてください。