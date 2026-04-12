# KabuSys — 日本株自動売買システム（抜粋）

このリポジトリは KabuSys の主要モジュール群（監視・実行・ポートフォリオ構築・リサーチ・AI 補助等）を含むコードベースの抜粋です。ここではプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムで、主に以下の責務を持つコンポーネント群で構成されています。

- ExecutionEngine：ブローカーとのやりとり（発注・状態同期・リスク管理）を行う実行部
- Monitoring（監視）：システム稼働・注文状態・リスク指標を定期的にチェックしてログ・アラートを出す
- Portfolio construction：シグナルに基づく候補選定・配分・株数算出
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI 補助：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価や市場レジーム判定
- ユーティリティ：環境設定読み込み、プロセス優先度設定、Streamlit ダッシュボード等

注意：ここに示すコードはプロダクション向けの設計思想・説明注釈を多数含みますが、実際に稼働させる際はローカル環境やブローカークレデンシャルの管理、法規制の確認を行ってください。

---

## 主な機能一覧

- システム監視（CPU/メモリ/ディスク/プロセス生存確認）
  - system_monitor: system_status テーブルに定期記録
- 注文監視（滞留注文、約定価格の異常検出）
  - trade_monitor: trade_logs / risk_logs への記録、アラート発行
- リスク監視（ドローダウン、ポジション上限）
  - risk_monitor: dashboard を参照し警告・kill flag 発行
- Kill Switch（ファイル書き込みによる ExecutionEngine 停止シグナル）
  - kill_switch: data/kill.flag を生成 / 削除
- 監視エンジン（複数 Monitor の統合ポーリング）
  - monitoring_engine: アラート送信（LINE）や kill switch 連携
- モニタリング DB レイヤ（SQLite）
  - monitoring_db: テーブル作成 / マイグレーション / 永続化 API
- 実行エンジン立ち上げスクリプト
  - run_execution: 本番/紙トレード切替、Engine 起動フロー
- 監視ループ起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL）
- Streamlit ダッシュボード（監視データの可視化）
  - monitoring/streamlit_dashboard.py
- Paper Trading 検証レポート生成
  - tools/paper_verification_report.py
- ポートフォリオ構築ユーティリティ
  - portfolio/{portfolio_builder, position_sizing, risk_adjustment}
- ファクター計算・リサーチツール
  - research/{factor_research, feature_exploration}
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
  - ai/news_nlp.py（バッチ化、リトライ・レスポンス検証、DuckDB への書込み）
- 市場レジーム判定（MA + マクロニュースセンチメントの合成）
  - ai/regime_detector.py
- 環境変数読み込み・Settings 管理
  - config.py（.env 自動ロード、必須値検査、各種パス・閾値の取得）
- プロセス優先度 / CPU affinity ユーティリティ
  - utils/process_priority.py

---

## セットアップ手順（ローカル実行向け）

前提：Python 3.9 以上を推奨（duckdb や openai パッケージ互換性に依存）。

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests streamlit openai
   - 必要に応じて他の依存を追加してください（sqlite3 は標準ライブラリ）。

   （プロジェクトに requirements.txt があればそれを使ってください。）

4. data ディレクトリを作成
   - mkdir -p data

5. .env の作成（必要な環境変数を設定）
   - 主要な環境変数例は下記「環境変数一覧」を参照。
   - .env を作成すると config.py が自動で読み込みます（プロジェクトルートに .git または pyproject.toml がある場合）。

6. DuckDB / SQLite DB の準備
   - duckdb はファイル path（デフォルト data/kabusys.duckdb）を使用します。最初は空ファイルでも OK。monitoring 側では init_monitoring_db が自動でテーブルを作成します。
   - paper_trading 時は data/paper_trading.db を使用します（必要なら先にスキーマ作成スクリプトを実行してください）。

---

## 環境変数（主要なもの）

（config.Settings で取得されるキー名とデフォルト／要件を抜粋）

- 必須（ランタイムにより必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須とされている箇所あり）
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 既定値あり
  - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
  - LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（未設定なら通知をスキップ）
  - LINE_USER_ID — LINE 通知先ユーザー ID
  - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH — デフォルト "data/monitoring.db"
  - PAPER_FILL_MODE — paper_trading の MockBroker の約定動作 ("instant"|"partial"|"never"|"reject")、デフォルト "instant"
  - PAPER_TRADING_SQLITE_PATH — デフォルト "data/paper_trading.db"
  - PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト "data/execution.pid"）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト "data/kill.flag"）
  - KILL_FLAG_CLEAR_ON_START — "1" にすると起動時に kill.flag をクリア
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
  - KABUSYS_ENV — "development"|"paper_trading"|"live"（デフォルト "development"）
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
  - MONITOR_POLL_INTERVAL — run_monitoring によるポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" をセットすると自動 .env 読み込みを無効化

例（.env）:
    KABUSYS_ENV=development
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=secret
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=

---

## 使い方（主要なスクリプト・コマンド）

- 監視ループを起動（SystemMonitor の単独ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を用いる（KABUSYS_ENV にかかわらず monitoring は本番 DB を使用する設計）。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開いてダッシュボードを表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH に代わる指定）
  - 検証指標（稼働率、注文成功率、送信率、P95 レイテンシ）を出力します。

- AI 関連
  - ai.score_news（kabusys.ai.score_news）や ai.score_regime（kabusys.ai.regime_detector.score_regime）を呼ぶには OPENAI_API_KEY を設定してください。
  - news_nlp は銘柄別ニュースをまとめてスコア化し ai_scores テーブルへ書き込みます。リトライ・レスポンス検証が組み込まれています。

---

## 重要な挙動・運用メモ

- pid / kill flag
  - ExecutionEngine は起動時に PID を pid_file に書きます。SystemMonitor はこの PID をチェックしてプロセスの生存を確認します。
  - RiskMonitor が危険閾値を検出すると KillSwitch が data/kill.flag を生成し、ExecutionEngine 側で存在を検出して安全停止させる設計です。Kill flag は冪等に扱われます（既存がある場合は上書きしません）。

- DB マイグレーション（軽量）
  - init_monitoring_db は監視用 SQLite にテーブルを作成し、既存スキーマにカラムが欠けている場合は ALTER TABLE による追加を試みます（例: latency_ms, peak_value）。

- Paper Trading（分離）
  - 紙トレード時は本番 DB を汚さないよう PAPER_TRADING_SQLITE_PATH に完全分離して記録します（run_execution 内で切替）。

- 安全性
  - AI 呼び出し失敗や API エラー時はフェイルセーフ（空スコア / 0.0 など）で継続し、例外を大きく広げないよう設計されています。
  - 外部 API を使うパス（kabu API、OpenAI 等）は設定必須。ローカルテストでは適宜モックを使ってください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py
- utils/
  - __init__.py
  - process_priority.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - (Execution 関連モジュール: order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory 等)
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- tools/
  - __init__.py
  - paper_verification_report.py
- data/ (実行時に使用される DB ファイルや出力ファイル用の想定ディレクトリ)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db

（実際のプロジェクトでは execution 以下にブローカー連携実装や order_repository、engine 実装が含まれます。）

---

## 開発者向け補足

- config.py はプロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 多くの関数は「ルックアヘッドバイアス防止」の観点から date.today()/datetime.today() を直接参照しない実装指針を守っています（研究・バックテスト用）。
- 単体テストを行う際は外部 API 呼び出し部分（OpenAI、requests、psutil 等）をモックすることを推奨します。ai.news_nlp._call_openai_api などはテスト差替え用に分離されています。

---

必要であれば、以下の内容も追加で作成できます：
- requirements.txt の草案
- .env.example の完全版
- デプロイ / systemd ユニットファイルの例（run_monitoring/run_execution 用）
- よくあるトラブルシューティング（DB ロック、OpenAI エラー、PID 管理 など）

どれを追加しましょうか？