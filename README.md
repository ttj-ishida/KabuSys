# KabuSys

日本株向け自動売買システム（実装スニペット）。ファクター計算・ポートフォリオ構築・発注（ExecutionEngine）・監視（MonitoringEngine）・AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含みます。

---

## 概要

KabuSys は次のような機能群を備えた自動売買基盤の実装です。

- 定量ファクターの計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- 発注基盤（OrderManager / ExecutionEngine、ブローカ抽象化）
- 起動時リコンシリエーション（Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager）
- AI モジュール（ニュースのセンチメント解析、マクロレジーム判定）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- 監視用 Streamlit ダッシュボード

設計方針として、DuckDB を用いた研究・ファクター計算、SQLite を用いた軽量の監視・注文ログ永続化、OpenAI API を用いた NLP スコアリングなどを組み合わせています。

---

## 主な機能一覧

- research:
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析・IC 計算
- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes（単元株丸め・aggregate cap 等）
- execution:
  - OrderManager, Reconciler（起動時自動復旧）
  - ExecutionEngine（外部ブローカーへの発注を統括）
  - BrokerFactory による運用 / Paper Trading 切替
- monitoring:
  - MonitoringDB（テーブル定義・マイグレーション）
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine
  - AlertManager（LINE push 通知）
  - KillSwitch（kill.flag による安全停止）
  - streamlit_dashboard（監視用ダッシュボード）
- ai:
  - news_nlp.score_news（ニュースを OpenAI でセンチメント化して ai_scores に書込）
  - regime_detector.score_regime（ETF MA とマクロセンチメントでレジーム判定）
- tools:
  - paper_verification_report（Paper Trading 検証レポート生成）

---

## 前提・依存

（プロジェクトに requirements.txt がある想定だが、無い場合は最低限以下をインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボードを使う場合)
- sqlite3（標準ライブラリ）

例（pip）:
```
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをチェックアウトし、ワークディレクトリをプロジェクトルートにする。

2. 必要な Python パッケージをインストールする（上記参照）。

3. 環境変数を設定する：
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必要なデータディレクトリを作成：
```
mkdir -p data
```

5. （任意）.env.example を元に .env を作成してください（.env.example が存在する想定）。

---

## 環境変数（主なもの）

- 決済・API 系
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用、本番デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 SQLite、デフォルト: data/paper_trading.db)
- Paper Trading 設定
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
- 監視・PID
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill.flag をクリア)
- 監視しきい値
  - CPU_THRESHOLD_PCT (デフォルト: 90.0)
  - MEMORY_THRESHOLD_PCT (デフォルト: 85.0)
  - DISK_THRESHOLD_PCT (デフォルト: 90.0)
- ログ / 振る舞い
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。1 未満や不正値はデフォルトにフォールバック。

重要な挙動：
- run_monitoring は KABUSYS_ENV に関係なく「本番の」sqlite_path（Settings.sqlite_path）を使います。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込み、本番データベースと完全に分離します。

---

## 使い方（実行コマンド）

※ パッケージルートを PYTHONPATH に含めている、またはプロジェクトルートから実行することを想定しています。

- 監視ループを起動（SystemMonitor のポーリング）:
```
python -m kabusys.run_monitoring
# または環境変数でポーリング間隔を変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
備考: run_monitoring はプロセス優先度を high に設定し、monitoring DB（sqlite）と DuckDB に接続します。

- ExecutionEngine（発注エンジン）を起動:
```
python -m kabusys.run_execution
```
KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB に記録されます：
```
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Paper Trading 検証レポート生成:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- 監視ダッシュボード（Streamlit）:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
（`--` 以降はダッシュボードスクリプトへ渡す引数）

- AI モジュールの呼び出し（プログラムから）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

これらは DuckDB 接続を渡して呼び出します。API キーが渡されない場合は環境変数 `OPENAI_API_KEY` を参照します。

---

## DB 初期化・マイグレーション

- run_monitoring / run_execution 起動時に `init_monitoring_db()` を呼び出して監視用テーブルを作成（冪等）。必要なカラムが無い既存 DB に対しては簡単なマイグレーション（column 追加など）を行います。

- DuckDB は prices_daily / raw_financials / raw_news 等のデータソースを持つ想定です（研究モジュールが参照）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - data/                  — （別途実装想定）データパイプライン / stats 等
  - research/
    - factor_research.py   — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （Broker API / OrderRepository 等が想定される他ファイル）
  - monitoring/
    - monitoring_db.py     — SQLite テーブル定義・MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - ai/
    - news_nlp.py          — OpenAI を使ったニュースセンチメント
    - regime_detector.py   — マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py   — OS 横断のプロセス優先度 / CPU affinity ユーティリティ

（上記は本リポジトリの主要実装ファイルのサマリです）

---

## 運用時の注意点 / トラブルシュート

- .env の自動読み込み:
  - デフォルトで .env（次に .env.local）をプロジェクトルートから読み込みます。OS 環境変数は上書きされません。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- モニタリング DB の選択:
  - run_monitoring は常に Settings.sqlite_path（監視用本番パス）を使用します。Paper Trading の分離を期待する場合は実行プロセスに注意してください。

- Paper Trading:
  - KABUSYS_ENV=paper_trading を使用すると、実際のブローカー API を呼ばず Mock を使う想定になっており、記録は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ行われます。

- OpenAI API:
  - API エラー（429、タイムアウト、5xx）はリトライ実装がありますが、API キーのレートやクォータに注意してください。
  - API キーは関数引数または環境変数 `OPENAI_API_KEY` で渡します。

- プロセス優先度 / CPU affinity:
  - set_process_priority はプラットフォーム依存の挙動を吸収します。権限不足等で失敗すると警告ログを出して続行します。

---

## 開発ヒント

- 研究用の DuckDB は readonly で参照して、結果をメモリ上の dict/list として処理する設計です。
- 各モジュールはルックアヘッドバイアス防止のため、date.today() 等を直接参照しない実装方針が取られています（テスト容易性の向上）。
- テスト時には外部 API 呼び出し関数（OpenAI など）をモックすることで安定して検証できます（実装内部でもコメントでその旨が記載されています）。

---

もし README に追加したい具体的な情報（依存バージョン、実行例のログ、.env.example の例、テストコマンド等）があれば教えてください。必要に応じて README を拡張します。