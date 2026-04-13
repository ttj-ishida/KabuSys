# KabuSys — README (日本語)

本リポジトリは日本株向け自動売買 / 研究 / 監視のためのライブラリ群および実行スクリプト群です。ここではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

注意: この README はソースコード（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は、日本株自動売買システムを構成する以下の機能群をモジュール化した Python パッケージです。

- 注文管理・発注・実行エンジン（Execution）
- リコンシリエーション（再起動後の同期）
- リスク管理・監視（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- 研究用ファクター計算・特徴量探索（Research）
- ニュース NLP を用いた AI スコアリング・レジーム判定（AI）
- 運用サポートツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）
- 環境変数管理・ユーティリティ（Settings / process priority 等）

設計方針の要点：
- DuckDB / SQLite を使ったデータ格納および分析
- Production と Paper Trading（模擬）を分離するための環境切替
- 外部 API 呼び出し（OpenAI 等）を呼び出し元で制御可能に設計
- 監視は永続化・アラート・kill flag による安全停止機構を備える

---

## 主な機能（一部）

- Execution
  - OrderManager／OrderRepository による注文ライフサイクル管理
  - Reconciler による再起動時の注文・ポジション同期
  - BrokerClientFactory による本番とモック（paper_trading）クライアント切替

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス状態・データ鮮度チェック
  - TradeMonitor: 注文滞留（stale）・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch: ディスク上のフラグファイル (data/kill.flag 等) で Execution を停止
  - AlertManager: LINE Messaging API への通知（クールダウン管理付き）
  - Streamlit ダッシュボード（簡易 UI）でモニタリング表示

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - 候補選定、等重・スコア重み、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイズ算出（単元株丸め、利用可能現金によるスケーリング）

- AI
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースをセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定を行い DB に書き込み

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit 監視ダッシュボード（kabusys.monitoring.streamlit_dashboard）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上を推奨（typing や構文を利用）
- 仮想環境の使用を推奨（venv / poetry 等）

例（venv + pip）:
1. リポジトリをクローンし、作業ディレクトリへ移動
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

（本プロジェクトに付属の requirements.txt があればそれを使用してください。）

環境変数
- .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（OS 環境 > .env.local > .env の優先）。
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI 呼び出しに使用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading の模擬約定モード（instant | partial | never | reject）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパス
- MONITOR_POLL_INTERVAL — 監視ループの秒間隔（実行スクリプトで上書き可、デフォルト 60 秒）

ファイルパーミッション
- プロセス優先度変更や CPU affinity の設定は os/プラットフォーム・権限に依存します。set_process_priority は psutil を使い失敗時は警告でスキップします。

---

## 使い方（実行例）

基本的な実行はパッケージモジュールとして直接起動できます。

- ExecutionEngine を起動（本番/模擬は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading にすると MOCK ブローカーが使われ、デフォルトで data/paper_trading.db に記録されます。
    - 起動時に PID ファイルへの書き込みなどを行い、set_process_priority("high") を呼びます。

- Monitoring の簡易ループ起動
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
    - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 DB（SQLite）を read-only で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI（プログラムから呼ぶ）
  - ニューススコアリング（DuckDB 接続が必要）
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- 設定の強制無効化（自動 .env 読み込みをスキップするテスト等）
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意点
- Paper Trading モードでは production DB と分離するため PAPER_TRADING_SQLITE_PATH が使用されます。
- OpenAI API 呼び出しはエラー時にリトライやフェイルセーフ（スコア 0.0）を行う実装です。API キーの管理に注意してください。
- 監視コンポーネントは SQLite に監視ログを永続化し、必要に応じてリスクイベントを記録します。init_monitoring_db() はスキーマ作成と簡易マイグレーションを行います。

---

## 主要コマンドまとめ

- 実行エンジン（Execution）
  - python -m kabusys.run_execution

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
  - パッケージ名・バージョン定義

- config.py
  - Settings クラス: 環境変数管理・自動 .env ロード・バリデーション

- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB接続・エンジン起動）

- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL 対応）

- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py: MA200 とマクロニュースを組み合わせてレジーム判定
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite スキーマ定義・CRUD ラッパー（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - alert_manager.py: LINE への通知（クールダウン）
  - kill_switch.py: kill.flag 制御
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの簡易ダッシュボード
  - __init__.py

- execution/
  - order_manager.py: 注文作成・送信・同期等の外向き API（OrderManager）
  - reconciler.py: 起動時の注文・ポジション照合（Reconciler）
  - order_repository.py, order_record.py, broker_factory.py, execution_engine.py など（発注・ブローカー抽象化を含む）
    - （注）残りの execution サブモジュールは本リストに含まれますが、README 内では省略（実装参照）

- portfolio/
  - portfolio_builder.py: 候補選定・等重/スコア重み計算
  - risk_adjustment.py: セクターキャップ・レジーム乗数
  - position_sizing.py: 発注株数計算（単元株丸め・aggregate cap）
  - __init__.py

- research/
  - factor_research.py: momentum / volatility / value 等ファクター計算（DuckDB 利用）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
  - __init__.py

- tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成 CLI
  - __init__.py

- utils/
  - process_priority.py: set_process_priority / set_cpu_affinity（psutil 利用）
  - __init__.py

データファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag

---

## 補足・運用上の注意

- DB マイグレーションは monitoring_db.init_monitoring_db 内で最小限の変更（カラム追加）を行いますが、本格的なマイグレーションは別途管理することを推奨します。
- OpenAI API を使う処理はレート制限・一時エラーに対してエクスポネンシャルバックオフやフェイルセーフを実装していますが、API キーの漏洩や使用量には注意してください。
- kill.flag による停止は冪等で、既に存在する場合は再書き込みしません。Execution 側はこのフラグを見て安全に停止する実装になっている必要があります。
- Paper Trading 環境は本番 DB と完全に分離されるよう設計されています（settings.is_paper による sqlite path 切替など）。

---

必要であれば、README に以下を追加できます：
- 具体的な環境変数のサンプル（.env.example 形式）
- 詳細なデータベーススキーマ説明（各テーブルの列説明）
- 実行例のログサンプル・トラブルシュート項目

追加希望があれば教えてください。