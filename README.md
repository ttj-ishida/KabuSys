# KabuSys

日本株自動売買システムのコードベース（抜粋）用 README。

以下はこのリポジトリに含まれる主要機能、起動方法、環境変数、およびディレクトリ構成の概要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を含むライブラリ／アプリケーションです。主な目的は次のとおりです。

- 発注（ExecutionEngine / OrderManager / BrokerClient）による自動取引
- 取引監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP（OpenAI）を用いた銘柄センチメント評価および市場レジーム判定
- Paper trading 検証レポート生成、Streamlit ダッシュボード等の運用ツール

設計方針として、DuckDB / SQLite をローカルデータ層に用い、外部 API 呼び出しはブローカークライアントや OpenAI クライアントなどで明確に扱われています。

---

## 機能一覧

- Execution
  - ExecutionEngine を起動してブローカーへ発注・状態同期・リスク制御を実施
  - paper_trading モードで MockBrokerClient を使用し、本番 DB と分離して検証可能
  - Reconciler による再起動時の自動リコンシリエーション（注文・ポジションの突合）
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス PID、データ鮮度を監視
  - TradeMonitor: 滞留注文（stale orders）や約定価格異常を検出
  - RiskMonitor: ドローダウン／ポジション上限を監視、必要時 kill.flag を書き込み停止指示
  - AlertManager: LINE Push による通知（クールダウン管理付き）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア降順）、等重・スコア加重配分
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（ロット丸め、利用可能現金でスケーリング）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリー
- AI
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA200 とマクロニュースの LLM 評価を合成）
- Tools
  - paper_trading の検証レポート生成スクリプト（期間指定可）
  - その他ユーティリティ（プロセス優先度設定など）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上を推奨（typing | を使用しているため）
- Git, インターネット環境（依存パッケージ取得）

1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone ...  
   - cd <repo_root>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb psutil openai requests streamlit
   - 追加で開発用・テスト用パッケージがあれば適宜インストールしてください。
   - SQLite は標準ライブラリに含まれます。

   （もし requirements.txt がある場合は `pip install -r requirements.txt` を利用）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルトで自動ロードされます）。
   - テストや CI などで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他の設定は後述の「環境変数一覧」を参照してください。

5. データディレクトリの準備
   - デフォルトの DB は `data/monitoring.db`（SQLite）および `data/kabusys.duckdb`（DuckDB）
   - 起動時に監視用テーブルは自動作成・マイグレーションされます（init_monitoring_db）。

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数とデフォルト値（存在するもの）／説明です。

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
  - paper_trading の場合は MockBrokerClient を使い、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の模擬約定モード（instant / partial / never / reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に既存 kill.flag をクリアするか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: しきい値（Monitoring 用）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

.env に設定する例（最小）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
```

---

## 使い方（起動例・コマンド）

※ パッケージルート（src が import path に入るよう）で実行してください。単純に開発中はリポジトリルートで `python -m` を使うケースが多いです。

- ExecutionEngine 起動（本番または paper_trading）
  - 本番（デフォルト KABUSYS_ENV が `development` の場合は実装上 development。ライブは `KABUSYS_ENV=live`）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（MockBroker を使用し、paper DB に記録）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  起動時にプロセス優先度を "high" に設定し、必要な DB 接続や監視テーブルを初期化します。paper_trading では本番 SQLite を上書きせず、`PAPER_TRADING_SQLITE_PATH` を用いた専用 DB を使用します。

- Monitoring 起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視は Settings からの sqlite_path（監視 DB）を使います。ドキュメントにある通り monitoring は環境にかかわらず「本番 sqlite_path」を使用します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ポートフォリオ集計・ポジション・注文・最新のシステム状態を表示します。

- AI 機能（Python API 呼び出し）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # conn は DuckDB connection
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- 補助ユーティリティ
  - process priority / CPU affinity:
    - from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity

---

## 重要な挙動・設計上の注意点

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml がある場所）で `.env` と `.env.local` が自動的に読み込まれます。OS 環境変数が優先されます。自動ロード無効化用に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定できます。

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading のとき、Execution は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH` に記録します（本番 SQLite と完全に分離）。

- Monitoring と DB
  - run_monitoring のドキュメントにある通り、Monitoring は環境に関係なく「本番の sqlite_path」を使う設計になっているため、運用時は監視用 DB のパス取り扱いに注意してください。

- Kill Switch
  - RiskMonitor がしきい値を超えると `data/kill.flag` を書き込み、ExecutionEngine 側がこれを検出して安全停止します（KillSwitch により冪等的に書き込み）。起動時に既存フラグをクリアしたい場合は `KILL_FLAG_CLEAR_ON_START=1` を設定する等の運用ルールを検討してください。

- OpenAI 呼び出し
  - OpenAI API 呼び出しはリトライや JSON バリデーション、スコアクリップ等の処理を行っていますが、API キーが未設定の場合は例外が発生します（呼び出し前に `OPENAI_API_KEY` を設定してください）。

- プロセス優先度
  - run_* スクリプトは起動直後に set_process_priority("high") を呼びます。環境によっては権限不足で設定できない場合があり、その場合は警告ログを出してスキップします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- monitoring/
  - monitoring_db.py — SQLite 監視ログ永続化層（テーブル作成・CRUD）
  - system_monitor.py — システム／データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込みロジック
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — LINE Push 通知
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ...（Execution 関連の実装群）
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数算出、資金配分
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py — ニュースセンチメント生成（OpenAI 呼び出し、バッチ処理、検証）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロ記事 LLM）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- その他: data 関連、execution の broker/adapter 実装など（この抜粋には含まれていない部分があります）

---

## よくある運用コマンドまとめ（例）

- Execution (paper):
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 参考・補足

- DB スキーマ初期化は `kabusys.monitoring.monitoring_db.init_monitoring_db` で行われ、起動時に自動で呼ばれます。既存 DB に対する簡易マイグレーション（カラム追加）も含まれています。
- DuckDB 接続は research / ai モジュールで大きく使われます。prices_daily / raw_financials / raw_news 等のテーブルを前提とした処理が多数あります。
- 本 README はコードの抜粋に基づくまとめです。運用前は `.env.example`（存在する場合）や該当ブローカー実装のドキュメントを参照してください。

---

必要であれば、この README を README.md 形式で出力したり、環境変数の完全な一覧や systemd / supervisor 用のサービス定義サンプル、docker-compose 例などの追加ドキュメントも作成します。どの情報を補足しますか？