# KabuSys

日本株向け自動売買・リサーチ基盤（ライブラリ群）  
このリポジトリは戦略の研究、ポートフォリオ構築、注文実行、監視、AIを使ったニュース評価などの機能を持つモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能を分離して実装したモジュール群です。

- リサーチ（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine や OrderManager を通じた発注管理、paper/live 切替）
- 監視（System / Trade / Risk の監視、Kill Switch）
- AI 支援（ニュース NLP による銘柄スコアリング、レジーム判定）
- ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証ツール）
- ツール（ペーパートレード検証レポート生成 等）

設計方針の一部：
- 本番 DB とペーパートレード用 DB を分離（KABUSYS_ENV=paper_trading）
- ルックアヘッド（現在時刻参照）により将来データを参照しない実装
- フェイルセーフ（API 失敗時は安全なデフォルトで継続）
- モジュールはできるだけ純粋関数・DB書き込みは永続層に限定

---

## 主な機能一覧

- config_setup: 対話式で .env を生成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env / config/*.yaml の起動前検証ツール（python -m kabusys.validate_config）
- run_execution: ExecutionEngine の起動スクリプト（本番/ペーパートレード切替）
  - KABUSYS_ENV=paper_trading の場合は MockBroker に切替え、専用 SQLite（data/paper_trading.db）を使用
- run_monitoring: SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor と MonitoringDB（SQLite）によるログ保存とアラート判定
- Kill Switch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
- portfolio: 候補選定、等重/スコア重み付け、ポジションサイズ計算、セクター上限・レジーム乗数
- research: DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン・IC 計算等
- ai: OpenAI（gpt-4o-mini）を利用したニュースセンチメント（score_news）・市場レジーム判定（score_regime）
- tools.paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 動作環境・依存

- Python 3.10+
- 推奨パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検査を有効にする場合)
- SQLite3 は標準ライブラリで利用

インストール例（仮想環境推奨）:
- pip install -r requirements.txt  # requirements.txt がある場合
- または:
  - pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン/チェックアウト
2. Python 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を設定
   - 注意: .env は決して Git にコミットしないこと
5. 設定検証（必須項目が揃っているか確認）
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

環境変数の主な一覧（代表）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能使用時）
- LOG_LEVEL（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアする場合は 1）

特殊な設定:
- PAPER_FILL_MODE（paper_trading の MockBroker の fill モード）
  - instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）

---

## 使い方（主要コマンド）

- 設定ウィザード（.env を作る）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード専用 DB と MockBrokerClient を使用します
  - 起動前に data/kill.flag が存在する場合はエンジンは起動しません
  - 実行中に data/stop_requested.flag を作るとループが停止します

- 監視ループを起動（定期的に SystemMonitor.check_once を実行）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず監視 DB を一元化）

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を使って記事を集約し OpenAI に投げる。OPENAI_API_KEY 必須（引数でも指定可）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースでレジーム判定を行い market_regime に書き込む

注意点:
- AI 機能を使うには OPENAI_API_KEY を設定してください。
- AI 呼び出しは失敗してもシステム側で 0.0 等のフェイルセーフを用意していますが、APIキー未設定は例外になります。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル・モジュールの概観です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定、等重・スコア重み
    - risk_adjustment.py           — セクターキャップ、レジーム乗数
    - position_sizing.py           — 発注株数計算、aggregate cap
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py       — 将来リターン、IC、統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py                  — raw_news を LLM で評価して ai_scores へ書き込み
    - regime_detector.py           — マクロ + MA200 を合成して market_regime に書き込み
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag の管理（Execution 停止トリガ）
    - monitoring_engine.py        — 複数モニタを束ねて実行
    - alert_manager.py            — （アラート送信を担う、実装はここに）
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ
  - portfolio, execution, data, research などのサブパッケージ（上で説明したもの）
  - （execution 関連の実装や data/pipeline 等は別ファイルに分かれています）

データ/メタファイル（デフォルトパス）
- data/kabusys.duckdb      — DuckDB（分析・価格データ等）
- data/monitoring.db       — 監視用 SQLite（system_status 等）
- data/paper_trading.db    — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading）
- data/execution.pid       — ExecutionEngine の PID ファイル（プロセス監視用）
- data/kill.flag           — Kill Switch 用フラグファイル（存在で停止シグナル）
- data/stop_requested.flag — run_* スクリプトの停止制御に使用されるフラグ

---

## 実運用時の注意点

- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch 設定などを慎重に確認してください（validate_config が警告を提示します）。
- .env を機密情報として厳重に管理してください（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY 等）。
- run_monitoring は監視 DB に常に「本番」sqlite_path を使う設計です（Monitoring は環境に依存しません）。
- ペーパートレードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- プロセス優先度の変更や CPU affinity の設定は管理者権限が必要な場合があるため、権限やプラットフォーム差に注意してください。

---

## 参考・開発者向けメモ

- DuckDB 接続を渡してファクター計算や AI 評価を行う設計になっています。データ取得は DuckDB の prices_daily / raw_financials / raw_news 等のテーブルに依存します。
- AI の呼び出し部分は OpenAI SDK を利用しており、API レスポンスのバリデーションや再試行ロジックが組み込まれています。
- MonitoringDB はマイグレーション処理（カラム追加）を簡易的に行います。既存 DB 互換をある程度保つ設計です。
- ユニットテストを書く際は、AI 呼び出しや外部接続部分（OpenAI, psutil など）をモックすることを推奨します（コード中でも patch を想定した設計あり）。

---

必要であれば、README に以下を追加できます：
- より詳しい .env のサンプル（.env.example からの説明）
- systemd / Supervisor 等でのサービス化手順
- DuckDB / SQLite の初期データロード手順
- 各モジュール（ExecutionEngine, AlertManager 等）の詳細 API ドキュメント

追記希望があれば、どの箇所を拡張するか教えてください。