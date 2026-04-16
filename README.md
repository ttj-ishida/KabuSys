# KabuSys

日本株向けの自動売買／研究プラットフォームの一部実装です。本リポジトリは以下の主要機能を含みます：注文実行エンジン、監視（Monitoring）サブシステム、ポートフォリオ構築ユーティリティ、ファクター計算・研究モジュール、ニュースNLP / レジーム検出（OpenAI を利用）、および検証ツール群。

以下はこのコードベースの概要、セットアップ方法、使い方、ディレクトリ構成の説明です。

## プロジェクト概要
- 目的：日本株アルゴリズムの実運用・検証を支援するための基盤コンポーネント群を提供する。
- 主なコンポーネント：
  - ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
  - Monitoring（システム状態、注文滞留、ドローダウン等の監視、LINE 通知）
  - Portfolio（候補選定・重み付け・株数決定・セクター制約）
  - Research（ファクター計算・特徴量探索）
  - AI（ニュースセンチメントスコアリング、マーケットレジーム判定、OpenAI を利用）
  - Tools（Paper Trading 検証レポート生成、Streamlit ダッシュボード起動スクリプト）

## 機能一覧
- 設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - Settings クラスで環境変数をラップ
- 発注・実行
  - ExecutionEngine：ブローカー抽象を通じた発注・注文管理
  - Reconciler：起動時の自動復旧（OrderSent の突合せ、ポジション差分検出）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBroker を利用し、専用 SQLite に記録
- 監視
  - SystemMonitor：CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限の監視と risk_logs への記録
  - KillSwitch：閾値到達で kill.flag を書き込み ExecutionEngine を停止させる仕組み
  - AlertManager：LINE Messaging API を用いた通知（クールダウン制御）
  - Streamlit ベースの簡易ダッシュボード（read-only）
- データ層
  - SQLite ベースの monitoring DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - DuckDB を用いた時系列データ参照（prices_daily / raw_financials 等）
  - init_monitoring_db で必要テーブル・マイグレーションを冪等に作成
- ポートフォリオ構築
  - シグナルの上位選定、等重／スコア重み化、リスクベースの株数計算、セクター制約
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini）でセンチメントを計算 → ai_scores へ書き込み
  - regime_detector: ETF(1321) の MA200 とマクロニュースセンチメントを合成して market_regime を更新
  - API 呼び出しにはリトライ・バックオフ・入力トリム・レスポンス検証などの安全策を実装
- ツール
  - Paper Trading 検証レポート生成（期間指定可）
  - streamlit ダッシュボード起動スクリプト

## セットアップ手順（開発 / 実行環境）
推奨 Python バージョン：3.10 以上（type | 演算子等を使用しているため）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   （requirements.txt が無い場合は下記の主要依存をインストールしてください）
   ```bash
   pip install duckdb psutil openai requests streamlit
   ```
   - 標準ライブラリの sqlite3 は追加インストール不要です。
   - 実際のブローカークライアント等は別途必要（本コードはブローカー抽象に依存）。

4. 環境変数 / .env 設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動で読み込まれます（既存 OS 環境が優先）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（monitoring DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - LOG_LEVEL（INFO 等）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、run_monitoring 用。デフォルト 60）

5. データディレクトリ
   - スクリプトは `data/` 下に DB・フラグファイル等を作成します。必要に応じて事前にディレクトリを作成してください。

## 使い方（起動 / 実行例）

- ExecutionEngine（発注エンジン）を起動
  - 本番モード（KABUSYS_ENV=live）や開発モードで同様に起動できます。paper_trading では専用 DB に記録されます。
  ```bash
  # 環境変数の例
  export KABUSYS_ENV=paper_trading
  export OPENAI_API_KEY=<your_api_key>   # AI 機能を使う場合
  # 起動
  python -m kabusys.run_execution
  ```
  - 実行時、`data/execution.pid` や `data/stop_requested.flag` の存在をチェックします。停止するには `data/stop_requested.flag` を作成します（手動または管理ツール経由）。

- Monitoring（ポーリング監視）を起動
  ```bash
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
  - 監視は Settings.sqlite_path を利用（run_monitoring の実装では KABUSYS_ENV にかかわらず本番 sqlite_path を使用）。
  - 停止は `data/stop_requested.flag` の作成で行います。

- Paper Trading 検証レポート（コマンドライン）
  ```bash
  # デフォルト DB は data/paper_trading.db。--db で指定可能
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10 --db data/paper_trading.db
  ```

- Streamlit ダッシュボード（監視用）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（プログラムからの呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して、指定日分（前日 15:00 JST ～ 当日 08:30 JST）の raw_news を集約して ai_scores に書き込みます。
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB を使って ma200 比やマクロニュースを評価し、market_regime テーブルを更新します。

## 設計上の重要な挙動 / 注意点
- .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行うため、カレントディレクトリに依存しません。
- run_execution は KABUSYS_ENV=paper_trading のときに paper_sqlite_path（デフォルト data/paper_trading.db）を使い、本番 DB と完全に分離されます。
- run_monitoring は監視専用に本番の sqlite_path を使う旨の実装コメントがあります（運用上、監視データは本番 DB を参照して監視する設計）。
- KillSwitch は条件（ドローダウンやポジション上限）に達した場合 `data/kill.flag` を作成します。Execution 側は kill.flag を検出して安全停止するべきです（実装上その仕組みを参照）。
- OpenAI 呼び出しはリトライや JSON バリデーション、スコアのクリップを行い、部分失敗時でも全体を壊さない設計です。
- process priority（高優先度）や CPU affinity の設定を行うユーティリティが含まれます。権限不足で設定できない場合は警告ログでスキップします。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/.env ローダーと Settings
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py          — monitoring SQLite 用の CRUD / マイグレーション
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー関連・エンジン等のモジュール)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - monitoring/ (監視関連の DB 初期化やログ保存ロジックを含む)

（リポジトリルート）
- data/ (実行時に DB / pid / flag 等を格納)
- pyproject.toml / setup.py 等（存在する場合はプロジェクトルート判定に使われます）

簡単なツリー表示（例）
```
src/
  kabusys/
    __init__.py
    config.py
    run_execution.py
    run_monitoring.py
    ai/
      news_nlp.py
      regime_detector.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ...
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    tools/
      paper_verification_report.py
    utils/
      process_priority.py
```

## よくある運用フロー
1. .env を作成して必要なキー（API キーやパス）を設定
2. データ（prices_daily 等）を DuckDB にロード
3. ExecutionEngine を起動（本番 or paper_trading）
4. Monitoring を別プロセスで起動して常時監視・LINE 通知・kill_flag 生成
5. 必要に応じて Streamlit ダッシュボードで監視データを確認
6. Paper Trading 実行後は tools の検証レポートで結果を確認

## 開発・拡張ポイント（メモ）
- Broker クライアントや ExecutionEngine の詳細実装はブローカー API に依存するため、実環境に合わせた実装が必要です。
- position の単元や手数料モデルを銘柄ごとに扱う場合は position_sizing の拡張を検討してください。
- AI 呼び出し部分のテストは外部 API を叩かないようにモック化可能です（コード中に差し替えポイントあり）。

---

不明点や README に追加してほしい項目があれば教えてください。例えば、よく使うコマンド一覧、想定する運用手順（デプロイ手順、Systemd ユニット例）、あるいは各設定項目の詳細なテンプレート（.env.example）などを追加できます。