# KabuSys

日本株自動売買システムのモジュール群の README です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注（Execution）・監視（Monitoring）・リサーチ・AI 補助（ニュースセンチメント、レジーム判定）などを含む小規模な自動売買基盤を想定した実装です。

以下はコードベース（src/kabusys 以下）に基づく概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群です。主要コンポーネントは次の通りです。

- Execution（ExecutionEngine / OrderManager / Reconciler）: ブローカーとの発注・状態管理・再起動時リコンシリエーション
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）: システム監視・データ鮮度・滞留注文・リスク監視・アラート送信
- Portfolio（候補選定・重み付け・ポジションサイズ計算・リスク調整）: 純粋関数群で配分と株数を決定
- Research（factor / feature exploration）: DuckDB を用いたファクター計算・IC 等の分析
- AI（news_nlp, regime_detector）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- Tools（paper_verification_report, streamlit dashboard）: Paper Trading の検証レポート生成や監視ダッシュボード

設定は環境変数 (またはプロジェクトルートの `.env` / `.env.local`) で管理します。

---

## 主な機能一覧

- システム監視
  - CPU / メモリ / ディスク / 実行プロセスのヘルスチェック
  - データ鮮度チェック（DuckDB の prices_daily を参照）
  - 監視ログの永続化（SQLite）
  - LINE へのプッシュ通知（AlertManager）

- トレード監視
  - 滞留注文（stale orders）の検出
  - 約定異常（価格乖離）の検出
  - リスクイベントのログ化（risk_logs）

- リスク管理 / Kill Switch
  - ドローダウン閾値超過やポジション数上限超過で `kill.flag` を書き込み、ExecutionEngine に停止シグナルを送出

- Execution（発注）
  - 本番／Paper Trading 切替（KABUSYS_ENV）
  - Paper Trading 時は MockBroker を用いて専用 SQLite に記録（完全分離）
  - 起動時のリコンシリエーション（Reconciler）で OrderSent 等の状態を同期

- ポートフォリオ構築
  - 候補選定、等重配分・スコア配分、リスクベースのポジションサイズ計算
  - セクターキャップとレジーム乗数の適用

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ

- AI
  - ニュースのセンチメントスコアを OpenAI で算出し ai_scores テーブルに保存
  - マクロニュースと ETF MA200 を組み合わせた日次レジーム判定（bull/neutral/bear）

- ツール
  - Paper Trading 検証レポート生成 (kabusys.tools.paper_verification_report)
  - Streamlit ベースの監視ダッシュボード

---

## 必要環境 / 依存パッケージ（主なもの）

この README はコードの参照に基づく推奨依存関係例です。実際の requirements.txt があればそちらを優先してください。

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード用)
- その他（標準ライブラリのみで済む部分も多い）

例:
pip install duckdb psutil requests openai streamlit

---

## 設定と環境変数

設定は環境変数を通して行います。プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動的に読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。

主な環境変数（デフォルト値や必須の説明）:

- 必須（使用する機能により必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD: kabuステーション API のパスワード

- OpenAI
  - OPENAI_API_KEY: OpenAI を使う場合に必須（news_nlp, regime_detector）

- 実行環境・ログ
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL: "DEBUG" | "INFO" | ...（デフォルト: INFO）

- DB パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: Monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

- Paper Trading 設定
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト: instant）

- 監視 / 実行制御
  - PID_FILE_PATH: 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値

- Monitoring ポーリング間隔
  - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト: 60）。1 未満や 0/負の値は無効と見なされ、デフォルトにフォールバックします。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業ディレクトリに入る

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（例）
   - pip install duckdb psutil requests openai streamlit

4. data ディレクトリを作成
   - mkdir -p data

5. 必要な環境変数を設定（`.env` を作るかシェルで export）
   - 最小例（ファイル `.env`）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - OPENAI_API_KEY=your_openai_key  # AI 機能使用時に必要

6.（Paper Trading を使う場合）PAPER_TRADING_SQLITE_PATH が自動的に data/paper_trading.db を使用します。

---

## 使い方（主要スクリプト / コマンド）

ソースはパッケージとして配置されているため、モジュール実行や個別関数を呼び出して利用します。

- 監視（MonitoringEngine を使う単体起動）
  - python -m kabusys.run_monitoring
    - 監視ループを起動します。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）。
    - 停止するにはプロセスを SIGINT（Ctrl+C）するか、リポジトリルートの data/stop_requested.flag を作成します（run_monitoring はこのフラグをチェックしてループを終了します）。
    - 監視は Settings.env にかかわらず本番 sqlite_path を使用する点に注意。

- 実行エンジン（ExecutionEngine 起動）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録されます（本番 DB と完全分離）。
    - 起動前に data/stop_requested.flag が存在する場合は起動を行わず終了します。
    - 停止指示は data/stop_requested.flag の作成、または kill.flag による停止シグナル（KillSwitch が書いた場合）があります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: data/paper_trading.db
    - 期間を指定し、稼働率・注文成功率・送信率・レイテンシ（P95）などを表示します。

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 SQLite を読み取り専用で開いてダッシュボードを表示します。

- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶか、スクリプトから利用します。OPENAI_API_KEY が必要です。

---

## 停止・フラグファイルについて

- stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクトルートの data/stop_requested.flag を定期チェックし、存在したら安全に停止します。ファイルのパスは run スクリプト内で決められています。

- kill.flag
  - KillSwitch（RiskMonitor の判定等で使用）が書き込むフラグ。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）を参照して停止する挙動を持ちます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動的にクリアします。

- PID ファイル
  - ExecutionEngine は data/execution.pid（デフォルト）に自分の PID を書きます。SystemMonitor はこの PID をチェックしてプロセスの存否を判定します。

---

## 重要な実装上の注意点

- Settings はプロジェクトルートの `.env` / `.env.local` を自動読み込みしますが、OS 環境変数が優先され、`.env.local` は `.env` の上書きを行います。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Monitoring 側は環境（KABUSYS_ENV）に関係なく本番用の sqlite_path を使用する設計です（監視ログは一箇所に集めるため）。

- run_execution は Paper Trading 環境では mock ブローカーを使用し DB を分離します。実際の本番ブローカー使用時は適切な BrokerClient の実装と認証情報が必要です。

- OpenAI API 呼び出しに対してはリトライやレスポンスバリデーションが厳格に実装されていますが、API キー未設定だと例外が投げられます。AI 機能を利用する場合は OPENAI_API_KEY を事前に設定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の読み込みと Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/ (実行時に作成される想定)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db
    - kabusys.duckdb (DuckDB ファイル)
    - execution.pid
    - kill.flag
    - stop_requested.flag

- src/kabusys/execution/
  - execution_engine.py (エンジン本体)*
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - order_record.py
  - ...（発注に関する各種実装）

- src/kabusys/monitoring/
  - monitoring_db.py         — monitoring 用 SQLite テーブル定義 & MonitoringDB クラス
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py              — ニュースセンチメント (OpenAI)
  - regime_detector.py       — レジーム判定 (OpenAI)

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

※ 上記は主要なファイルのみを列挙しています。細かなモジュールはソースツリーを参照してください。

---

## よくある運用コマンド（例）

- 監視の起動（バックグラウンドで systemd 等に組み込む想定）
  - python -m kabusys.run_monitoring

- エンジンの起動
  - python -m kabusys.run_execution

- Paper Trading レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（ローカル）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 強制停止（実行中プロセスへの安全な停止要求）
  - touch data/stop_requested.flag

---

## 開発上のメモ

- DuckDB を使ったリサーチ/AI 前処理は副作用を持たない設計（読み取り専用の SQL）です。テストやオフライン分析で安全に使えます。
- MonitoringDB（monitoring_db.py）はスキーマのマイグレーション（欠落カラム追加）ロジックを持ち、冪等にテーブルを作成します。
- process_priority / cpu_affinity の変更はプラットフォームに依存するため、アクセス権限不足などで失敗してもワーニングを出してスキップする実装です。

---

必要であれば、README に追記する具体的な .env.example、requirements.txt、systemd ユニットのサンプル、または個別コンポーネントの詳細な使用例（API 呼び出し例や単体テストの実行方法）を作成します。どの情報を優先して追加しますか？