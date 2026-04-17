# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ向け README（日本語）。

以下はこのコードベースの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成のまとめです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な目的は次のとおりです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine による発注（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュース NLP を用いた銘柄 / マクロの LLM ベーススコアリング
- ペーパートレードの検証レポート作成ツール

設計方針として、DB 書き込み・読み出しは明確に分離され、ルックアヘッドバイアスを避ける実装が多く用いられています。

---

## 機能一覧（ハイライト）

- 環境設定ウィザード（.env 作成）: `kabusys.config_setup`
- 設定検証 CLI: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、別 DB（data/paper_trading.db）に分離
  - 起動時にプロセス優先度を High に設定
- Monitoring 起動スクリプト: `kabusys.run_monitoring`
  - SystemMonitor を定期ポーリングして system_status 等を記録
  - 環境に関わらず本番 monitoring DB パスを使用（設定の意図的な動作）
  - ポーリング間隔は環境変数で上書き可能
- 監視コンポーネント
  - SystemMonitor: CPU/Mem/Disk・プロセス生存・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション数監視とアラート記録
  - KillSwitch / AlertManager による自動停止・通知連携
- ポートフォリオ構築
  - 候補選定、等分配 / スコア加重、リスクベースの株数算出、セクター上限適用、レジームによる乗数
- リサーチ / ファクター計算（DuckDB ベース）
  - モメンタム、ボラティリティ、バリュー、将来リターン、IC 計算、統計サマリなど
- AI モジュール（OpenAI 利用）
  - news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: ma200 乖離 + マクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを標準出力に出す

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone ... （この README はパッケージ配布後でも動作するよう設計されています）

2. Python 仮想環境
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （パッケージ一覧が setup/requirements にある場合はそれに従ってください）

4. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式で .env を作成・更新できます
   - 重要な必須項目:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を環境変数または .env に設定

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正（--strict をつけると警告も FAIL 扱い）

6. DB 初期化
   - monitoring DB は起動時に `init_monitoring_db` によってテーブル生成・簡易マイグレーションが行われます。
   - DuckDB（分析用）ファイルは .env の DUCKDB_PATH で指定。初回はスキーマ生成や data import が別途必要な場合があります（プロジェクト付属のスクリプト参照）。

---

## 使い方 / 実行方法

基本的にはモジュールを直接実行します。以下は主要な実行例です。

- ExecutionEngine（発注）を起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、実際のブローカー API を叩きません
    - 起動時にプロセス優先度を "high" に設定
    - data/stop_requested.flag が存在すると起動を停止
    - 実行中に data/stop_requested.flag を作成すると安全に停止処理が行われます

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - Settings.sqlite_path（監視 DB）に接続して monitoring テーブルを初期化
    - DuckDB に接続してデータ鮮度チェック等を行う
    - ポーリング間隔は環境変数で上書き可能:
      - MONITOR_POLL_INTERVAL（秒、デフォルト: 60）
    - 停止: data/stop_requested.flag を作成するとループを抜けます
    - 監視は本番 sqlite_path を環境に関係なく使用します（意図的）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- 環境設定ウィザード（再掲）
  - python -m kabusys.config_setup

- 設定検証（再掲）
  - python -m kabusys.validate_config [--strict]

- AI 機能（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が環境変数か引数で必要

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（news_nlp, regime_detector 用）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは data/ 以下）

注意: .env は Git にコミットしないでください（ウィザードは警告を出します）。

---

## 停止・Kill フラグについて

- 停止ループ用ファイル:
  - data/stop_requested.flag
    - run_execution / run_monitoring の両方で監視され、存在するとループを停止します
- Kill Switch:
  - KillSwitch は data/kill.flag（デフォルト）を書き込むことで ExecutionEngine 停止のトリガーを作成します
  - KillSwitch はリスクルール（ドローダウン超過、ポジション上限等）によって自動で flag を書きます
  - Settings.KILL_FLAG_CLEAR_ON_START が "1" の場合、ExecutionEngine 起動時に kill.flag を自動クリアします（本番では注意）

---

## 開発時の注意点 / 実装上の要点

- run_execution は KABUSYS_ENV に応じて DB を切り替え（paper_trading は paper_sqlite_path を使用）
- run_monitoring は監視 DB（sqlite_path）を常に使用（環境に関係なく）
- 起動時にプロセス優先度を "high" に設定する処理があります（psutil を使用）
- DuckDB は主にリサーチ・AI で利用する分析用 DB として使われます
- AI 呼び出しは OpenAI の Chat Completions（JSON Mode）を使用しており、レスポンス検証・リトライロジックが組み込まれています
- DB スキーマはコード内で作成 / マイグレーションされる箇所があります（例: init_monitoring_db）

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 以下の主要ファイルと各役割の一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動ロード、Settings クラス
  - config_setup.py
    - .env を対話式で作るウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注処理）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB の検証レポート生成
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み算出
    - position_sizing.py
      - 株数算出・制約処理
    - risk_adjustment.py
      - セクター上限・レジーム乗数
  - research/
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py
      - ニュース記事の LLM スコアリング（ai_scores 書き込み）
    - regime_detector.py
      - マクロ + ma200 で日次レジーム判定
  - monitoring/
    - monitoring_db.py
      - monitoring 用 SQLite のスキーマ初期化・読み書きラッパ
    - system_monitor.py
      - CPU/MEM/DISK・データ鮮度・プロセス生存チェック
    - trade_monitor.py
      - 滞留注文 / 価格異常チェック
    - risk_monitor.py
      - ドローダウン / position limit
    - kill_switch.py
      - フラグファイルを作成して Execution を停止させる
    - monitoring_engine.py
      - 各 Monitor を束ねたポーリング実行
    - alert_manager.py
      - （通知送信ロジックをまとめる想定。実装を追加してください）
  - execution/
    - order_repository.py, order_manager.py, execution_engine.py, broker_factory.py, reconciler.py, risk_manager.py, order_record.py
      - 発注処理とリポジトリ / ブローカークライアント周り（主要な責務は実行エンジンの構築）
  - utils/
    - process_priority.py
      - プロセス優先度と CPU affinity セットユーティリティ
  - monitoring/monitoring_db.py（DB スキーマ、MonitoringDB クラス）

（実際のソース内にはさらに多くの補助モジュールがあります。上は主要箇所の一覧です）

---

## よくある操作例（コマンドまとめ）

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔変更）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
- 停止（手動）
  - touch data/stop_requested.flag  # ループを抜けます
- Kill Switch 手動作成（Execution 停止トリガー）
  - echo "manual kill reason" > data/kill.flag

---

## 補足 / 注意事項

- 本システムは実際の発注処理を含みます。特に KABUSYS_ENV=live の場合は誤発注に十分注意してください。必ず設定・配列を確認し、必要に応じて paper_trading で十分検証してください。
- .env の内容（トークン・パスワード）は機密情報です。絶対にリポジトリにコミットしないでください。
- OpenAI API を使う機能は課金対象になる場合があります。API キーの管理・コストに注意してください。
- 一部の機能（YAML パースや OpenAI 呼び出し等）はオプションの外部ライブラリに依存します。validate_config は PyYAML が無い場合は YAML 検証をスキップします。

---

この README はコードベースから抽出した情報に基づく概要です。より詳細な挙動や追加オプション、内部 API を使ったカスタム実装については各モジュールの docstring を参照してください。必要なら README に実行例や設定例（.env.example）を追記できます — 追記希望があれば指示してください。