# KabuSys

日本株向けの自動売買・リサーチ・監視フレームワーク（リポジトリ内の主要モジュール群の README）。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な目的は次のとおりです。

- 注文発行・状態管理（ExecutionEngine / OrderManager / Broker 抽象化）
- リコンシリエーション（再起動時の同期）
- 監視（システム状態・注文滞留・リスク監視）と通知（LINE）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算・特徴量探索）
- AI を用いたニュースセンチメント評価・レジーム判定（OpenAI API）
- Paper Trading 用検証レポート生成、Streamlit ダッシュボード

設計方針として、DB（SQLite / DuckDB）により永続化・分析を分離し、外部 API 呼び出し（ブローカー・OpenAI）は抽象化/失敗耐性を持たせています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・停止、PID 管理）
  - OrderManager（発注・重複防止・同期）
  - Reconciler（OrderSent の突合、ポジション差分の検出）
  - ブローカーファクトリで本番と paper_trading を切り替え（paper_trading は専用 DB に記録）
- Monitoring
  - SystemMonitor（CPU/MEM/Disk、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて kill.flag を書き込み ExecutionEngine を停止）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定、等配分・スコア加重、リスク調整（セクター制限・レジーム乗数）、発注株数決定（単元丸め、集約上限）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア化（ai_scores テーブル書込）
  - 市場レジーム判定（ETF の MA200 とマクロニュースの LLM 結果の合成）
- ユーティリティ
  - 環境変数の .env 自動読み込み（.env, .env.local）、設定ラッパー（Settings）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（依存パッケージ）

主要な Python 外部依存（例）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit

SQLite は標準ライブラリで利用します。実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。

例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. data ディレクトリを作成（スクリプトが自動作成する場合もありますが手動で用意すること推奨）
```
mkdir -p data
```
5. 環境変数を設定
   - プロジェクトルートに `.env`（必要なら `.env.local`）を置くと自動的にロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須や推奨の環境変数は次節を参照してください。
6. （Paper Trading を使う場合）`KABUSYS_ENV=paper_trading` を設定して起動すると、本番 DB と分離された `data/paper_trading.db` を使います。

---

## 主要な環境変数（代表）

Settings クラスで参照される主なキーとデフォルト：

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（設定しない場合は通知を送信しません）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: Execution PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

注意:
- .env/.env.local の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。
- 必須の値が未設定だと Settings 取得時に ValueError が発生します。

---

## 使い方（実行方法）

### 監視ループ（Monitoring）
監視ループをデーモン的に動かすスクリプト:
```
python -m kabusys.run_monitoring
```
- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 監視は本番用の sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照する旨の設計）。
- 停止にはプロジェクトルートの `data/stop_requested.flag` を作るとループが検知して終了します（自動生成はされません）。

### 実行エンジン（Execution）
ExecutionEngine を起動:
```
python -m kabusys.run_execution
```
- `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録します（本番 DB と完全分離）。
- 起動時、`data/stop_requested.flag` が既に存在すると起動せず終了します。
- 停止は `data/stop_requested.flag` を作成すると検知して安全に停止します（または KillSwitch による `data/kill.flag` が書き込まれる場合は監視側から停止指示が出る設計）。

### Paper Trading 検証レポート
Paper Trading の検証レポートを生成（SQLite DB を参照）:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
- デフォルトの DB: `data/paper_trading.db`
- オプション `--db PATH` で別パス指定可。

### Streamlit ダッシュボード（監視）
Streamlit を使って監視ダッシュボードを起動:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- `--db` で監視用 SQLite のパスを指定。監視が動いていないと read-only で開けない場合のメッセージを表示します。

### AI 機能（ニュース NLP / レジーム判定）
- OpenAI API を利用する機能は `OPENAI_API_KEY` を設定する必要があります。
- ニューススコアリング:
  - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
- これらは DuckDB 接続を受け取り、raw_news / prices_daily などのテーブルを参照します。

---

## フラグファイルと停止制御

- data/stop_requested.flag
  - run_execution / run_monitoring で参照される手動停止フラグ。存在すると起動／ループ継続を停止します。
- data/kill.flag
  - KillSwitch（監視側）がリスク条件に達したときに書き込むフラグ。ExecutionEngine に停止指示を出す目的で使用。
- KillSwitch の `clear()` を使うか、ファイルを手動で削除して再開できます。

---

## ディレクトリ構成（概観）

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / Settings
  - run_monitoring.py                   -- SystemMonitor ポーリングループ起動
  - run_execution.py                    -- ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py      -- Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py                       -- ニュースセンチメント（OpenAI）関連
    - regime_detector.py                -- レジーム判定（MA200 + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py                  -- SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/ (想定される実行時フォルダ)
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (paper_trading 用 DB)
    - kabusys.duckdb (default DUCKDB_PATH)
    - execution.pid
    - kill.flag / stop_requested.flag

---

## 開発時の注意・補足

- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時に冪等でテーブル・カラムの作成・追加を行います。
- Paper Trading モードは本番 DB と完全に分離されます。実運用前の検証に利用してください。
- OpenAI やブローカー API 呼び出しは例外／レート制限に対してリトライやフェイルセーフ（0 にフォールバック等）処理が組み込まれていますが、API キーやネットワーク状況に依存します。
- process priority（高優先度設定）は psutil を使用して行います。OS と権限によっては設定できない場合があります（警告ログが出ます）。
- .env のパースはシェルライクですが完全な互換性を保証しない独自実装があるため、複雑な .env の記述は避けると安全です。

---

## 例: 最低限の起動フロー（ローカルでの簡易確認）

1. 必要パッケージをインストール
2. data ディレクトリ作成
3. .env を作成（最低限の変数）
   - KABUSYS_ENV=development
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...  （AI 機能を使う場合）
4. 監視を起動:
   ```
   python -m kabusys.run_monitoring
   ```
5. 別ターミナルで実行エンジンを起動（paper_trading を試す場合）
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
6. Paper Trading レポート:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
7. ダッシュボード:
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

---

## 貢献 / 開発者向け

- コードはモジュール毎に責務を分離しています。ユニットテストを追加する場合、各純粋関数（portfolio/*, research/* など）は依存を差し替えやすい設計です。
- OpenAI 呼び出し等はテスト時にモックすることを想定しており、実際の呼び出し関数に対して unittest.mock.patch 等で差し替え可能です。
- 新しい DB カラムを追加する際は monitoring_db.init_monitoring_db を拡張してマイグレーション処理を追加してください（既存 DB に対して冪等に動作するよう注意）。

---

この README はコードベースから抽出した主要点をまとめたものです。実際の運用・デプロイ時は環境変数や権限、運用ルール（PID 管理、ログ回転、バックアップ等）を考慮してください。必要であれば、各モジュールに対する詳しい使用例や API ドキュメントも作成できます。