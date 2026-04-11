# KabuSys

KabuSys は日本株向けの自動売買基盤（研究 -> シグナル -> 発注 -> 監視）を想定した軽量なモジュール群です。本リポジトリは以下の主要機能を備え、実運用／ペーパートレーディング／研究用途を分離して扱える設計になっています。

- シグナル処理と Order State Machine（ExecutionEngine / OrderManager）
- ブローカー抽象化（実ブローカー／モックの切替）
- 再起動時のリコンシリエーション（Reconciler）
- リスク管理（RiskManager, RiskMonitor）
- 監視基盤（SystemMonitor / TradeMonitor / MonitoringEngine / AlertManager）
- ニュース NLP（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（ETF MA + マクロ NLP を合成）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、株数算出）
- 研究用ファクター計算（DuckDB ベースのファクター群）
- Streamlit ベースの簡易ダッシュボード

以下では導入・実行方法、主な設定、およびディレクトリ構成をまとめます。

---

## 機能一覧（概観）

- Execution
  - ExecutionEngine: シグナル読み取り・発注ループ、WebSocket などからの push ドレイン処理想定
  - OrderManager: 注文作成・送信・同期・キャンセル（2 相永続化等のクラッシュ耐性考慮）
  - Reconciler: 起動時の未確定注文・ポジション差分の突合
  - RiskManager: 発注ゲート（Gate1/2/3）、レート制限、サーキットブレーカー等（設定で制御）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス存在確認
  - TradeMonitor: 注文滞留・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill flag 発動）
  - MonitoringDB: SQLite を用いた監視ログの永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（監視 DB を read-only で参照）
- AI / Research
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に格納
  - regime_detector: ETF（1321）MA200 とマクロ NLP を合成して market_regime を判定・保存
  - research: momentum / volatility / value 等のファクター計算、forward returns、IC 計算等（DuckDB を利用）
- Portfolio
  - 候補選定（select_candidates）
  - 重み付け（等金額・スコア重み）
  - ポジションサイジング（リスクベース / 重みベース、単元丸め・aggregate cap）
- Utils
  - process_priority: Windows / POSIX を吸収してプロセス優先度／CPU affinity を設定

---

## 必要要件

- Python 3.10 以上（typing に match する環境を想定）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで同梱）
- ネットワークアクセス（OpenAI / LINE API / ブローカー API を利用する場合）

package 管理ファイルは本サンプルに含まれていません。プロジェクト固有の requirements.txt がある場合はそちらを優先してください。

---

## 環境変数（主なもの）

Settings クラスは .env（プロジェクトルート）および .env.local を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数／意味（不足は Settings._require により起動時に例外となるものがあります）:

- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")、デフォルト "development"
  - paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を使用する AI モジュールで必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager が LINE Push を行うために使用
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag ファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring でのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading における Mock の約定挙動 ("instant" | "partial" | "never" | "reject")
- LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

簡易 .env 例:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-xxxx
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、ルートに移動
2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実際はプロジェクトの requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポート
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データディレクトリの準備
   - data/ ディレクトリを作成
   - DuckDB のスキーマ・テーブル（prices_daily / raw_financials / raw_news 等）は研究・実行に必要
   - 監視 DB は実行時に自動でテーブル作成（init_monitoring_db）されます

注意: DuckDB に必要なテーブル（prices_daily, raw_financials, raw_news など）はプロジェクト外で準備する必要があります（データの投入方法は本 README には含みません）。

---

## 使い方（実行例）

プロジェクトルートから `src` を Python パスに含めてモジュールとして実行することを推奨します。

- ExecutionEngine を起動（通常運用）
  - PYTHONPATH=src python -m kabusys.run_execution
  - Paper trading モードで起動:
    - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
    - paper_trading の場合は data/paper_trading.db（デフォルト）を使用し、本番 DB と分離されます。
  - 起動時にプロセス優先度を "high" に設定し、Monitoring テーブルを初期化します。
  - ExecutionEngine は pid ファイル（Settings.pid_file_path）を監視に使用します。

- Monitoring を起動（監視ループ）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring

- Streamlit ダッシュボード（監視 DB を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite を開き、監視状況やポジション、直近の発注ログ等を確認します。

- AI / Regime / News スコアリング（研究用関数）
  - ai.score_news / ai.regime_detector.score_regime 等の関数は DuckDB 接続と target_date を渡して呼び出します。
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または引数で渡す）。

- kill.flag
  - KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 起動中・ループ中は kill.flag の存在を検知して安全停止処理を行います。
  - 必要に応じて設定ファイル／起動スクリプトで kill.flag をクリアしてください。

---

## 注意事項・挙動メモ

- DB
  - 監視用 SQLite（SQLITE_PATH）は Monitoring 用にのみ使用。paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
  - init_monitoring_db(conn) は冪等でテーブルを作成し、古いスキーマからのマイグレーション（dashboard.peak_value の追加）を行います。
- 再起動耐性
  - OrderManager は send の前後で複数回コミットする設計（OrderSent の永続化 → ブローカー呼び出し → broker_order_id 永続化 → OrderAccepted 更新等）によりクラッシュ時の復旧を容易にしています。
  - Reconciler は起動時に残った OrderSent を突合して回復を試みます。
- AI 呼び出し
  - OpenAI 呼び出しはリトライ（429 / 接続エラー / 5xx）を行い、最終的に失敗した場合はフェイルセーフ（0.0 等）で処理継続します。API キー未設定時は例外を送出する関数もあります。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びます（プラットフォーム依存：Windows / POSIX を吸収）。アクセス権がない場合は警告を出して継続します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数/.env 読み込みと Settings
    - utils/
      - process_priority.py         — プロセス優先度／CPU affinity ユーティリティ
    - execution/
      - execution_engine.py         — ExecutionEngine（メイン発注ロジック）
      - order_manager.py            — OrderManager（注文ワークフロー）
      - order_repository.py         — SQLite ベースの注文永続化（not shown）
      - order_record.py             — 注文状態モデル（not shown）
      - reconciler.py               — 再起動時リコンシリエーション
      - risk_manager.py             — 発注リスク管理（not shown）
      - broker_factory.py           — Broker クライアント生成（not shown）
      - broker_api.py               — ブローカー API 抽象（not shown）
    - monitoring/
      - run_monitoring.py           — 監視ループ起動スクリプト
      - monitoring_db.py            — MonitoringDB クラス（SQLite）＋ init
      - system_monitor.py           — システム／データ鮮度監視
      - trade_monitor.py            — 注文滞留／約定異常監視
      - risk_monitor.py             — ドローダウン・ポジション監視
      - monitoring_engine.py        — 各モニタ束ねるエンジン
      - kill_switch.py              — kill.flag 書き込みユーティリティ
      - alert_manager.py            — LINE 通知管理
      - streamlit_dashboard.py      — Streamlit ダッシュボード
    - portfolio/
      - portfolio_builder.py        — 候補選定・重み計算
      - position_sizing.py          — 株数算出・制約適用
      - risk_adjustment.py          — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py          — momentum/volatility/value 等
      - feature_exploration.py      — forward returns / IC / summary
    - ai/
      - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py          — 市場レジーム判定（MA200 + マクロ NLP）
    - monitoring (root exports)     — __init__.py で主要クラスを再エクスポート
    - run_execution.py              — ExecutionEngine 起動スクリプト（トップレベル実行）
- data/                            — デフォルト DB ファイル格納場所（monitoring.db, kabusys.duckdb, paper_trading.db 等）

---

## 開発・拡張のヒント

- DuckDB を用いたファクター計算は SQL と Python を混在させた設計になっています。大規模データや別スキーマを追加する場合は DuckDB のテーブル設計を最初に固めてください。
- Broker 抽象は BrokerAPIProtocol に基づいているため、実ブローカー実装（kabuステーション等）や Mock を容易に差し替え可能です。paper_trading モード用に MockBrokerClient を用意してください。
- アラートは AlertManager 経由で LINE に送信されます。運用時は channel token と user id を .env で設定してください。クールダウンがあるため同一アラートの多発を抑制できます。
- ローカルでの研究実行は DuckDB のデータ準備と OPENAI_API_KEY の管理が重要です。AI 呼び出しはコストがかかるためバッチサイズや記事トリミング（MAX_CHARS_PER_STOCK）などの設定に注意してください。

---

必要に応じて README を拡張して、インストール手順（pip packaging）、CI/CD、データ投入スクリプトやサンプル .duckdb ファイル、テストケースの実行方法などを追加できます。ほしい追加情報（例: 依存関係の exact list、データスキーマ定義、運用 runbook など）があれば教えてください。