# KabuSys

日本株向け自動売買プラットフォームのサンプル実装 (KabuSys)。  
このリポジトリには発注実行エンジン、監視モジュール、ファクター/リサーチ機能、AI を使ったニュース評価などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買基盤のコンポーネント群です。

- 発注（ExecutionEngine）: シグナル取り込み→Gate チェック→発注→Push ドレイン／同期
- リコンシリエーション（Reconciler）: 再起動時の注文・ポジション整合
- リスク管理（RiskManager / RiskMonitor）: ドローダウン・ポジション上限・レート制御
- 監視（MonitoringEngine）: システム状態 / 注文滞留 / リスクイベントの常時監視
- 通知（AlertManager）: LINE への一方向プッシュ通知
- AI モジュール: ニュースを LLM（OpenAI）でスコアリング、マクロセンチメントと MA を合成したレジーム判定
- ポートフォリオ構築ロジック: 候補選定・重み計算・ポジションサイジング・セクター制約
- 研究用ユーティリティ: ファクター計算・将来リターン / IC 計算
- ストリームリット監視ダッシュボード

設計方針として、DB（DuckDB / SQLite）を用いたローカル解析・永続化を行い、発注ロジックはブローカー API 抽象を通じて実装されます。

---

## 主な機能一覧

- Execution
  - Signal ベースの発注ループ（シグナル期間とドレイン期間に分割）
  - Gate チェック (シグナルレベル / 実行レベル / ドローダウンチェック)
  - 発注の2相永続化設計（OrderSent の扱い・Reconciliation による回復）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（価格データの最終日）
  - 注文滞留・約定異常価格の検出
  - ダッシュボード（streamlit）
  - kill.flag による外部停止シグナル
- AI
  - ニュース記事の LLM センチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定
- Portfolio
  - 候補選定、等金額／スコア重み、リスクベースの株数決定
  - セクター集中制限、レジーム乗数
- Utilities
  - プロセス優先度 / CPU affinity 設定（Windows / POSIX を吸収）
- DB 層
  - monitoring 用 SQLite（system_status / trade_logs / positions / risk_logs / dashboard）の初期化・永続化ユーティリティ

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を準備します。

2. 必要パッケージをインストールします（例）:

   ```bash
   pip install duckdb psutil requests streamlit openai
   ```

   実際の要件は使う機能により異なります（streamlit や openai はそれぞれの機能を使う場合のみ必要）。

3. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動読み込みは既定で有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   代表的な環境変数（例）:

   ```
   KABUSYS_ENV=development           # development | paper_trading | live
   LOG_LEVEL=INFO
   SQLITE_PATH=data/monitoring.db    # monitoring 用（Monitoring は環境にかかわらず本番 sqlite_path を使用）
   DUCKDB_PATH=data/kabusys.duckdb
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=1        # 起動時に kill.flag をクリアする（paper_trading 等のテスト時に便利）
   OPENAI_API_KEY=sk-xxxx...         # AI 機能を使う場合
   JQUANTS_REFRESH_TOKEN=...         # 必要に応じて
   KABU_API_PASSWORD=...             # ブローカー連携用
   PAPER_FILL_MODE=instant           # paper_trading 用: instant|partial|never|reject
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

   .env の詳細なパースルールは `kabusys.config` に準拠します（export プレフィックスやクォート、インラインコメント対応あり）。

4. DB 初期化は各起動処理内で自動的に行われます（monitoring 用テーブルは `init_monitoring_db()` で冪等に作成）。

---

## 実行方法（使い方）

各スクリプトはパッケージモジュールとして実行できます（推奨）:

- 監視ループを起動（MonitoringEngine の簡易起動スクリプト）:

  ```bash
  # 環境変数でポーリング間隔を上書き（秒）
  export MONITOR_POLL_INTERVAL=30

  # モジュールとして起動
  python -m kabusys.run_monitoring

  # あるいは直接スクリプトを実行
  python src/kabusys/run_monitoring.py
  ```

  注意:
  - MONITOR_POLL_INTERVAL の無効値（0 や負値）は無視され、デフォルト 60 秒が使用されます。
  - run_monitoring は Settings に依らず「本番」sqlite_path を監視 DB として使用します（コード上の仕様）。

- 発注エンジンを起動（ExecutionEngine）:

  ```bash
  # 本番/開発/ペーパートレーディングは KABUSYS_ENV で切替
  export KABUSYS_ENV=paper_trading

  python -m kabusys.run_execution
  ```

  挙動:
  - KABUSYS_ENV=paper_trading の場合、Mock ブローカークライアントが用いられ、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
  - 起動時に PID ファイル (Settings.pid_file_path) に PID を書き込みます。kill.flag による停止制御をサポートします。

- Streamlit ダッシュボード:

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  データベースを読み取り専用で開くので、MonitoringEngine が稼働していることを確認してください。

- AI 関連（ニューススコア/レジーム判定）:

  - ニューススコアリング関数:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY 環境変数または api_key 引数が必要

  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同じく OpenAI API キーが必要

---

## 主要な設定項目（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- SQLITE_PATH: monitoring 用の SQLite パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: AI モジュール用 API キー
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール（抜粋）:

```
src/
└─ kabusys/
   ├─ __init__.py                 # パッケージ定義
   ├─ config.py                   # 環境変数・設定管理
   ├─ run_monitoring.py           # 監視ポーリング起動スクリプト
   ├─ run_execution.py            # 発注エンジン起動スクリプト
   ├─ utils/
   │   └─ process_priority.py     # プロセス優先度 / CPU affinity
   ├─ monitoring/
   │   ├─ monitoring_db.py        # monitoring 用 SQLite 抽象層
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py
   │   ├─ risk_monitor.py
   │   ├─ kill_switch.py
   │   ├─ alert_manager.py
   │   ├─ monitoring_engine.py
   │   └─ streamlit_dashboard.py
   ├─ execution/
   │   ├─ execution_engine.py
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   ├─ order_record.py
   │   ├─ reconciler.py
   │   ├─ risk_manager.py
   │   └─ broker_factory.py
   ├─ portfolio/
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ news_nlp.py              # ニュース→LLM スコアリング
   │   └─ regime_detector.py      # MA200 + マクロセンチメントでレジーム判定
   └─ data/                        # 実行時に生成される DB 等（data/kabusys.duckdb, data/monitoring.db ...）
```

（上は抜粋です。各サブモジュールにさらに細かい実装があります。）

---

## 運用上の注意 / 実装上のポイント

- Monitoring は run_monitoring 内で Settings.env に関わらず「本番」sqlite_path を参照する設計になっています（監視は常に本番 DB を見る想定）。
- ExecutionEngine は紙トレードモード（KABUSYS_ENV=paper_trading）時に本番 DB と完全に分離された paper_trading DB を使います。
- kill.flag による停止は冪等で、既存の flag があっても二度書きません。起動時にクリアしたければ KILL_FLAG_CLEAR_ON_START=1 を設定してください。
- OpenAI（LLM）呼び出しは失敗耐性を持ち、API 失敗時はフェイルセーフ値（例: macro_sentiment=0.0）にフォールバックしますが、API キーは必須です。
- プロセス優先度や CPU affinity の設定はプラットフォーム差分を吸収しますが、権限不足などで設定できない場合は警告を出してスキップします。
- DB マイグレーションやスキーマ追加（例: dashboard.peak_value の追加）は起動時に自動で補完します（簡易マイグレーションロジック有り）。

---

## 参考コマンドまとめ

- 監視開始:

  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 発注エンジン開始（ペーパートレード）:

  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード:

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

README はここまでです。必要であれば以下の点も補足できます：

- より詳細な .env.example を作る（全キー列挙、説明付き）
- Docker 化 / systemd ユニット例
- 具体的な Broker 実装（Mock / 実ブローカー）インターフェースと実装例
- テスト実行方法（ユニットテスト / モックの利用方法）

どれを追加しますか？