# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・検証ツールを含む日本株向け自動売買フレームワークです。設計方針として、本番データベースやブローカー API への影響を最小化するために paper_trading モードや各種フェイルセーフを備えています。

バージョン: 0.1.0

---

## 概要

主なコンポーネント

- execution: 注文の組み立て・発行を行う ExecutionEngine（本番 / ペーパートレード対応）
- monitoring: システム稼働状況、注文滞留、リスク（ドローダウン等）を監視する監視エンジン
- portfolio: 候補選定・配分・位置サイズ計算などのポートフォリオ構築ロジック（純粋関数）
- research: ファクター計算・将来リターン計算・統計解析用モジュール（DuckDB 前提）
- ai: ニュース NLP（OpenAI）を用いたセンチメント評価、レジーム判定
- tools: Paper Trading の検証レポート生成などのユーティリティ

設計上のポイント

- 環境変数 / .env による設定管理（自動ロード機能あり）
- paper_trading を明確に分離（専用 SQLite DB に記録）
- Kill Switch（data/kill.flag）による外部停止シグナル対応
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に利用
- OpenAI（gpt-4o-mini）を使った NLP モジュール（APIキー必須）

---

## 機能一覧

- Execution
  - 実際のブローカー接続または MockBroker を用いたペーパートレード
  - Risk Manager（ポジション上限、利用率、ドローダウン等）
  - Reconciler / OrderManager / OrderRepository による注文追跡

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン、ポジション数の監視・アラート記録
  - KillSwitch: 条件により data/kill.flag を生成して ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor をまとめてポーリング

- Research / Portfolio
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン・IC 計算、ファクター統計
  - 候補選定、等重/スコア重み、位置サイズ計算、セクター上限適用、レジーム乗数

- AI
  - ニュースの銘柄ごとセンチメントスコア生成（OpenAI）
  - マクロニュース+ETF 指標を用いた市場レジーム判定（OpenAI）

- Tools
  - Paper Trading 検証レポート出力（成功率・稼働率・レイテンシ等）

---

## 必要条件（概略）

- Python 3.9+
- 主要ライブラリ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証で任意）
- SQLite（Python 標準ライブラリで利用可能）
- ネットワーク接続（ブローカー API / OpenAI を使う場合）

パッケージはプロジェクトの requirements.txt があれば `pip install -r requirements.txt` を推奨します。存在しない場合は上記ライブラリを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. 初期 .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - このウィザードは .env（デフォルトはプロジェクトルート/.env）を作成します。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定

   備考:
   - 自動環境読み込みはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - .env は必ず Git にコミットしないでください（シークレットを含みます）。

5. 設定検証
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱い（exit 1）になります。

6. データディレクトリ作成（必要に応じて）
   - デフォルト DB/フラグパスは data/ 以下に作成されます。自動で作られる場合もありますが、権限確認等のため手動作成を推奨します。

---

## 主要な環境変数（抜粋）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 認証
- KABU_API_PASSWORD — kabuステーション API パスワード

オプション / 代表値
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 DB（production 用）: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading モード）
- OPENAI_API_KEY — OpenAI を使用する場合に必要
- PAPER_FILL_MODE — ペーパートレード時の約定挙動: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に既存の kill.flag を自動クリアするか（0/1）

監視関連
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID/フラグパスは Settings 経由で調整可能（デフォルト: data/execution.pid, data/kill.flag）

---

## 使い方（主なコマンド）

※ いずれもプロジェクトルートで実行してください。

- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（注文エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV を paper_trading にすると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。

  挙動:
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中に同フラグが作られるとエンジンは停止します
  - 実行時に data/execution.pid を生成してプロセス存在を管理

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）

  挙動:
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に関わらず）
  - stop_requested.flag を検知するとループ終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示したい場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール実行（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 運用上の注意点

- .env に秘密情報を置くため、絶対に Git にコミットしないこと。
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（validate_config は注意喚起を行います）。
- Kill Switch（data/kill.flag）を用いると ExecutionEngine を安全に停止できます。必要に応じて KILL_FLAG_CLEAR_ON_START を設定してください（本番では 0 推奨）。
- run_monitoring は MONITOR_POLL_INTERVAL が短すぎる設定だと CPU 使用量が増える可能性があるため 1 秒未満は避けること。
- OpenAI を利用する AI 機能は API レートやコストに注意してください。API エラー時はフェイルセーフ（0.0 など）で続行する設計です。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動読み込みロジック、Settings クラス
- config_setup.py           — .env 作成対話ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
- execution/                — Execution 関連（Engine, OrderManager, BrokerFactory, ...）
- monitoring/
  - monitoring_db.py        — SQLite に対する永続化層（テーブル初期化 / CRUD）
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常検出
  - risk_monitor.py         — ドローダウン・ポジション数監視
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - kill_switch.py          — Kill Switch 実装
  - alert_manager.py        — （アラート送信管理、未掲載）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — 市場レジーム判定（OpenAI）
- tools/
  - paper_verification_report.py

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を確認してください）

---

## サンプル .env（例）

（config_setup を使うことを推奨します。以下は例示）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 開発・検証のヒント

- research や ai モジュールは DuckDB の prices_daily / raw_news テーブルを参照します。テストデータを投入してから関数を実行してください。
- validate_config は PyYAML が無い場合に YAML 検査をスキップします（警告表示）。
- run_execution は paper_trading モード時に paper_trading.db を使用して本番 DB と完全分離します。
- MonitoringDB は初回実行時に必要なテーブルを自動作成し、既存 DB のマイグレーション（カラム追加）も行います。

---

## 貢献 / ライセンス

本 README は内部ドキュメント用途です。外部公開時はシークレットの取り扱い、ライセンス条項、CI/CD の手順を追記してください。

---

補足が必要であれば、実行例・設定ファイルテンプレート・各モジュールの API ドキュメント（関数引数・返り値の詳細）などを追記します。どの部分を詳しく書いて欲しいか教えてください。