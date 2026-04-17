# KabuSys — README

このリポジトリは日本株自動売買システム KabuSys の一部コードベースです。本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

注意：この README は提供されたソースコード（src/kabusys 以下）に基づいて作成しています。実行には外部依存ライブラリや環境変数の設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステム群です。主に以下の責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: シグナルに基づく発注、注文状態管理、リスク管理の実行
- 監視（Monitoring）: システム稼働状況・注文状況・リスク（ドローダウン等）を定期的に監視してログ保存や通知、必要に応じて ExecutionEngine 停止（kill flag 書き込み）
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限など
- 研究用モジュール: ファクター計算、将来リターン・IC 計算等（DuckDB を利用）
- AI 関連: ニュースのセンチメント解析（OpenAI）や市場レジーム判定（LLM と価格指標の合成）
- ユーティリティ: 環境設定、プロセス優先度設定、ツール類

設計方針の一例:
- DB（監視ログ等）への永続化は SQLite、大規模集計等は DuckDB を使用
- Paper Trading 環境では本番 DB と厳密に分離（data/paper_trading.db を使用）
- .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）

---

## 主な機能一覧

- Monitoring
  - システムリソース（CPU / メモリ / ディスク）監視
  - 実行プロセスの存在チェック（PID ファイル）
  - データ鮮度チェック（prices_daily の最終日付）
  - 注文滞留・約定異常価格検出
  - ドローダウン・ポジション上限の監視とリスクログ記録
  - LINE によるアラート送信（AlertManager）
  - kill.flag / stop_requested.flag を用いた ExecutionEngine 停止制御
  - Streamlit ダッシュボード（監視情報の可視化）

- Execution / Order
  - 注文作成 → ブローカー送信 → 状態管理のワークフロー（OrderManager）
  - 起動時リコンシリエーション（Reconciler）で OrderSent 等をブローカーと突合
  - Paper Trading モードでは MockBrokerClient を用い、本番 DB と分離

- Portfolio construction
  - 候補選定（スコア・ランキング）
  - 等重み・スコア加重の重み計算
  - リスク調整（セクターキャップ、レジームに応じた乗数）
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分、単元株丸め、aggregate cap）

- Research
  - モメンタム / ボラティリティ / バリュー等ファクター計算（DuckDB）
  - 将来リターン・IC 計算、ファクター統計要約

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア算出（ai_scores へ書き込み）
  - マクロニュースと 1321 (ETF) MA200 を組み合わせた市場レジーム判定

- ツール
  - Paper Trading 検証レポート出力（指定期間の稼働率・注文成功率・レイテンシ等）

---

## 必要な依存（概略）

実行には少なくとも以下パッケージが必要です（バージョンはプロジェクトに合わせて調整してください）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit

（requirements.txt は本コード配布に含まれていないため、プロジェクトの実際の環境に合わせて準備してください）

---

## セットアップ手順（例）

1. リポジトリをクローン / 展開
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成してアクティブ化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. data ディレクトリを作成（アプリがファイルを書き込むため）
   ```
   mkdir -p data
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作り、必要なキーを設定できます。config.py は自動で .env を読み込みます（ただし OS 環境変数が優先されます）。
   - 主な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効にする場合
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper トレード用 DB（default: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）

6. 初期 DB 作成
   - 監視（Monitoring）は run_monitoring や run_execution 内で init_monitoring_db を呼びます。手動で初期化したい場合は Python REPL から init_monitoring_db を呼ぶことも可能です。

---

## 使い方（主な実行コマンド）

以下はソース配置が `src/` の場合の実行例（プロジェクトルートで実行する想定）。

- 監視ループを起動（Monitoring）
  ```
  # KABUSYS_ENV に関係なく monitoring.db は本番 sqlite_path を使う（Settings のデフォルト）
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL を変更したい場合
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  動作概要:
  - プロセス優先度を high に設定
  - Settings からパスや環境を読み込み
  - SQLite / DuckDB に接続し monitoring DB を初期化（冪等）
  - SystemMonitor.check_once() をポーリング実行しログ保存
  - data/stop_requested.flag を検知すると安全に停止

- ExecutionEngine（実際の注文処理）を起動
  ```
  # development / live / paper_trading を切り替えて使用
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  ポイント:
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - Execution 起動時もプロセス優先度を high に設定
  - 起動中に data/stop_requested.flag が作られると停止処理を実行

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成ツール
  ```
  # 全期間（デフォルト DB）
  python -m kabusys.tools.paper_verification_report

  # 期間指定と DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す例）
  - ニューススコアリング（DuckDB 接続を渡す）
    - 使用関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定
    - 使用関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が必要（引数で上書き可能）。API 呼び出しはリトライやフェイルセーフ処理を備えています。

- kill.flag / stop フロー
  - ExecutionEngine を安全停止させる場合は `data/kill.flag` を書き込むか、KillSwitch 経由で作成することで停止シグナルを送信します。
  - run_monitoring / run_execution は `data/stop_requested.flag` を見て終了する仕組みがあります。

---

## 主要ファイル・ディレクトリ構成（概要）

この節では src/kabusys 以下の主要なモジュールを概説します。実ファイルはすでにコードベースに含まれています。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 読み込みロジック、Settings クラス（各種パス・閾値・フラグ）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モードは専用 DB を使用）
  - tools/
    - paper_verification_report.py
      - Paper Trading 結果の稼働率・成功率・レイテンシ等を集計してレポート出力
  - monitoring/
    - monitoring_db.py
      - SQLite に対する永続化層（テーブル作成・CRUD ライクなメソッド）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス/PID/データ鮮度チェック
    - trade_monitor.py
      - 注文滞留・約定異常価格チェック
    - risk_monitor.py
      - ドローダウン監視・ポジション上限監視
    - kill_switch.py
      - kill.flag の作成・評価
    - alert_manager.py
      - LINE 通知（クールダウン管理付き）
    - monitoring_engine.py
      - 各 Monitor を束ねるランナー（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py
      - Streamlit を使った簡易ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...（ブローカー API や Engine 実装は別ファイル）
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
      - プラットフォーム間の違いを吸収してプロセス優先度や CPU affinity を設定するユーティリティ

- data/
  - monitoring.db（デフォルトの監視 SQLite DB）
  - paper_trading.db（Paper Trading 用 DB）
  - kabusys.duckdb（DuckDB ファイル）
  - execution.pid, stop_requested.flag, kill.flag などの管理用ファイル

---

## 環境変数（主要なもの・デフォルト）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- PID_FILE_PATH: data/execution.pid（デフォルト）
- KILL_FLAG_PATH: data/kill.flag（デフォルト）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default 60）

config.py により `.env` と `.env.local`（プロジェクトルート）が自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用上の注意点

- Paper Trading では本番 DB と完全に分離されますが、設定ミスで本番 DB を参照しないよう環境変数の管理に注意してください。
- OpenAI API の呼び出しは外部サービス依存のためレート制限・課金に注意。score_news / regime_detector はリトライとフェイルセーフを含みますが、API キーは適切に管理してください。
- kill.flag / stop_requested.flag / pid ファイルはファイルベースのシグナリングを使用します。マニュアルで作成・削除する場合は意図した動作を確認してください。
- process priority / cpu affinity の設定には権限が必要な場合があります。permission のない環境では設定が失敗して警告ログが出ますが処理は継続します。
- DuckDB や SQLite のアクセスは同時接続に注意してください（読み取り専用 URI 等を活用）。

---

## 開発・テストヒント

- MonitoringEngine.run_once() や各 Monitor の check_once() は単体テストが容易な設計（引数で時間や接続を与えられる）になっています。
- AI / API 呼び出し部分は内部で呼び出す関数を分離してあり、unittest.mock.patch 等でモック可能です（score_news._call_openai_api や regime_detector._call_openai_api など）。
- DB 初期化は init_monitoring_db() で冪等に行えます。スキーマ変更はこの関数に反映されます（マイグレーション処理あり）。

---

この README はコードベースの理解用の概要です。実運用時はセキュリティ、監査、フェイルオーバー、取引所 API の利用契約等に十分配慮してください。必要であれば README を拡張してデプロイ手順・CI/CD・モニタリング設定等を追加できます。