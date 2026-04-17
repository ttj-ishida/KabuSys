# KabuSys

日本株向け自動売買システムのバックエンドライブラリ群および実行ユーティリティ集です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI（ニュースセンチメント）などの主要コンポーネントを含み、ローカル開発 / ペーパートレード / 本番（live）での運用を想定しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数一覧（主要なもの）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム売買を支える共通ライブラリ群と実行用スクリプトを提供します。  
主な役割は以下の通りです：

- ファクター計算・リサーチ（DuckDB を用いた過去価格・財務データ参照）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注エンジン（ExecutionEngine）と注文管理
- 監視（System / Trade / Risk）とアラート（LINE）
- AI モジュール：ニュースの NLP スコアリング / 市場レジーム判定（OpenAI を利用）
- ペーパートレード用 DB 分離、検証用レポート生成ツール

---

## 機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials からファクターを算出
  - calc_forward_returns / calc_ic / factor_summary：特徴量の探索・IC 計算
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes：各銘柄の発注株数計算（単元株丸め・aggregate cap）
  - apply_sector_cap / calc_regime_multiplier：セクター集中抑制・レジームによる乗数
- execution（発注系）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（paper_trading 時はモックを使用）
- monitoring（監視系）
  - SystemMonitor / TradeMonitor / RiskMonitor：状態・滞留注文・ドローダウン等の監視
  - MonitoringEngine：複数モニタを束ねて定期実行
  - KillSwitch：フラグファイルで ExecutionEngine を停止する仕組み
  - AlertManager：LINE によるプッシュ通知（クールダウンあり）
  - DB 永続化（monitoring_db.py）：SQLite に監視ログを格納。既存 DB 用の簡易マイグレーションを実装
- ai
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）に送り銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF（1321）の MA とマクロニュースを合成して market_regime を書き込み
- tools
  - paper_verification_report：ペーパートレード DB から検証レポート（稼働率、成功率、レイテンシ等）を生成
- config
  - Settings クラスで環境変数/.env を統一管理
  - config_setup：.env を対話式に作成するウィザード
  - validate_config：起動前に設定を検証する CLI

---

## セットアップ手順

必要条件（代表例）
- Python 3.9+
- DuckDB （Python パッケージ）
- psutil
- requests
- openai
- （オプション）PyYAML（config/*.yaml の構文検証用）

推奨：仮想環境を作成してから依存パッケージをインストールしてください。

例：
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai

   （config YAML の検証を行う場合）
   - pip install PyYAML

3. .env の用意
   - 対話式ウィザードを使う：
     - python -m kabusys.config_setup
   - あるいはルートに .env ファイルを手動で作成（下記サンプル参照）

4. 設定検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 問題がある場合は出力されるエラーや警告に従って修正

5. データディレクトリ等
   - デフォルトでは data/ に DB ファイルや PID/flag を作成します。必要に応じて DB パスを .env で指定してください。

---

## 使い方（主要コマンド）

基本的にはモジュールを python -m で実行します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit code 1）

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注：KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録し本番 DB と分離します。
  - 停止: data/stop_requested.flag（または kill.flag の運用）を作成するとループが検知して停止します。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視データは本番 DB に格納）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 機能（ライブラリを直接呼ぶ例）
  - from kabusys.ai.news_nlp import score_news
    - 必要: OpenAI API キー（env OPENAI_API_KEY または引数）
  - from kabusys.ai.regime_detector import score_regime

注意:
- run_execution/run_monitoring は内部でプロセス優先度を "high" に設定しようとします（psutil の権限や OS に依存）。
- ペーパートレードと本番の SQLite DB は分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨・設定:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI の API キー（ai モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知に使用

監視関連:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH — KillSwitch のフラグパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

paper_trading:
- PAPER_FILL_MODE — MockBroker の約定モード: instant | partial | never | reject

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します（テスト時などに有用）

サンプル .env（最低限の必須要素を含む）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## ディレクトリ構成（主要ファイルの説明）

（リポジトリ内の src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — Settings クラス（.env / 環境変数の読み込み・検証・ユーティリティ）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 初期化・エンジンスレッド）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント合成）
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite での監視ログ永続化（テーブル作成・簡易マイグレーション）
    - system_monitor.py — システム状況・データ鮮度監視
    - trade_monitor.py — 滞留注文・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知
  - execution/ (発注関連) — OrderRepository, OrderManager, ExecutionEngine 等（実装の各モジュール）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 運用上の注意

- 本番運用（KABUSYS_ENV=live）時は .env の取り扱いに注意し、絶対にリポジトリにコミットしないでください。
- validate_config は起動前に必ず実行し、出力される警告やエラーを確認してください。--strict モードは本番デプロイ前の最終チェックに有用です。
- OpenAI の呼び出しを行う機能（ai.news_nlp, ai.regime_detector）は API レートやコストが発生します。API キーの管理、呼び出し頻度、チャンクサイズなどは運用ポリシーに合わせて調整してください。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）と kill.flag（データ/運用上の kill スイッチ）で安全に停止/起動制御できる設計です。運用スクリプトや systemd 等と組み合わせて利用してください。
- プロセス優先度の設定や CPU affinity の設定は psutil の権限に依存します。権限が不足するとログに警告が出て設定はスキップされます。
- monitoring_db は簡易マイグレーション（カラム追加）を行いますが、重要なデータ移行については本格的なマイグレーション手順を別途用意してください。

---

必要であれば README に「デプロイ手順」「systemd ユニット例」「実例の .env.example」や「よくあるトラブルシューティング」を追加できます。どの情報を優先して追加しますか？