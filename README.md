# KabuSys

日本株向けの自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
AI を用いたニュース評価・レジーム判定、研究用ファクター計算等を含む総合的な自動売買プラットフォームの一部です。

---

## 主な概要

- モジュール設計により「発注ロジック」と「監視/記録」を分離。
- Paper Trading（ペーパートレード）と Live（本番）を環境変数で切替可能。
- DuckDB を用いた研究用データ分析、SQLite を用いた監視・取引ログ永続化。
- OpenAI を利用したニュースのセンチメント評価や市場レジーム判定（任意）。
- 監視モジュールがドローダウンや滞留注文などを検知すると kill flag を書き込み、ExecutionEngine を安全停止させる仕組みを持つ。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading 用 DB と MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（監視ログの記録）
- 設定管理 / ツール
  - config_setup.py: 対話的に .env を生成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の整合性チェック（--strict オプションあり）
- 監視（monitoring）
  - system_monitor: システムリソース・データ鮮度・実プロセス存在チェック
  - trade_monitor: 発注ログの整合性チェック（滞留注文・約定異常など）
  - risk_monitor: ドローダウン・ポジション上限監視
  - kill_switch: 条件を満たした際に data/kill.flag を書き込む
  - monitoring_db: SQLite による監視ログ保存（テーブルの初期化・マイグレーション含む）
  - monitoring_engine: 各モニタを束ねるポーリングエンジン
- 発注関連（execution）
  - BrokerClientFactory / ExecutionEngine / OrderManager / Reconciler / RiskManager（設定に基づくリスク制御）
  - ペーパートレード用に本番 DB と分離された data/paper_trading.db を使用可能
- ポートフォリオ構築（portfolio）
  - 候補選定、ウェイト計算、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ決定（単元丸め等）
- 研究（research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上で実行）
  - feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリー等
- AI（任意）
  - ai.news_nlp: OpenAI を使った銘柄ごとのニュースセンチメント集計と ai_scores への書き込み
  - ai.regime_detector: ETF MA とマクロニュースを統合した市場レジーム判定
- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーションファイル）
  - process_priority: プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

---

## 必要条件（推奨）

- Python 3.10 以上（型ヒントの union 演算子 (|) を使用）
- 必要パッケージ（代表）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML 検証を行う場合に推奨）
- SQLite（Python に標準搭載）
- ネットワーク（本番 API や OpenAI を使用する場合）

インストール例（仮に requirements.txt がある場合）:
  python -m venv .venv
  source .venv/bin/activate
  python -m pip install -r requirements.txt

特定パッケージを個別に入れる場合:
  python -m pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - python -m pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで必要な値（J-Quants トークン、kabu API パスワード、KABUSYS_ENV など）を入力

4. 設定検証
   - python -m kabusys.validate_config
   - 本番準備時は --strict を付けて警告も失敗扱いにする:
     python -m kabusys.validate_config --strict

5. デフォルトのデータディレクトリ作成（必要な場合）
   - mkdir -p data logs

注意:
- 自動的に .env を読み込む仕組みが入っています（プロジェクトルートに .env / .env.local があれば読み込み）。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途）。

---

## 主要な環境変数

必須（主要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用

運用系
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
  - paper_trading の場合、発注は MockBroker を使い paper_sqlite_path に記録
- LOG_LEVEL — ログレベル（例: INFO）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## 使い方

### 1) .env の準備
- 対話式:
  python -m kabusys.config_setup
- あるいは .env を手動作成（.env.example を参照して値を埋める）

### 2) 設定検証
  python -m kabusys.validate_config
  # 本番チェック:
  python -m kabusys.validate_config --strict

### 3) ExecutionEngine（発注エンジン）の起動
- 通常起動:
  python -m kabusys.run_execution
- 仕様:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録し、本番 DB と分離します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中に同フラグを置くことで停止を促すことができます。
  - 起動時に PID を data/execution.pid に書きます。

### 4) Monitoring（監視）の起動
  python -m kabusys.run_monitoring
- 設定:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で変更可能（デフォルト 60）。
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します（監視データは常に本番 DB を想定）。
  - data/stop_requested.flag の検出でループを安全終了します。

例: ポーリングを30秒にする
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

### 5) Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
- 出力: 稼働率、注文成功率、送信率、レイテンシ統計、PASS/FAIL 判定

### 6) AI 機能
- OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で渡す）
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、ai_scores テーブルに書き込みます
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- AI 呼び出しは外部 API に依存するため、失敗時は安全にフォールバックする設計ですが、API キーは必要です。

---

## 開発・テスト向けメモ

- ログ設定: 各スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します。ログは stdout と logs/<app_name>.log に出力されます（logs ディレクトリを作ること）。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil の権限がない場合は警告を出してスキップ）。
- .env 自動読込: プロジェクトルート（.git または pyproject.toml を探索）を見つけると自動的に .env / .env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可。

---

## ディレクトリ構成（主要ファイル）

src/kabusys
- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック
- config_setup.py               — .env 対話ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor 起動スクリプト

subpackages:
- ai/
  - news_nlp.py                 — ニュースセンチメント（OpenAI）
  - regime_detector.py          — 市場レジーム判定（OpenAI + MA）
- monitoring/
  - monitoring_db.py            — SQLite のテーブル初期化 / ラッパー
  - system_monitor.py           — システム・データ鮮度監視
  - trade_monitor.py            — 発注ログ監視（滞留・約定異常 等）  ※（ファイル内で参照）
  - risk_monitor.py             — ドローダウン / ポジション上限監視
  - kill_switch.py              — kill.flag の作成/クリア
  - alert_manager.py            — 通知（LINE 等）を行う想定の管理クラス
  - monitoring_engine.py        — 各モニタの統合ポーリング
- portfolio/
  - portfolio_builder.py        — 候補選定 / 重み計算
  - position_sizing.py          — 発注株数計算（単元丸め・aggregate cap）
  - risk_adjustment.py          — セクターキャップ・レジーム乗数
- research/
  - factor_research.py          — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py      — 将来リターン, IC, 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py            — ログ設定ユーティリティ
  - process_priority.py         — プロセス優先度 / CPU affinity
- monitoring、execution、data などの補助モジュール群（発注系モジュールは execution 下に分離）

データ / ログ（デフォルト）
- data/
  - monitoring.db               — 監視用 SQLite（デフォルト）
  - paper_trading.db            — ペーパートレード用 SQLite（paper_trading 時）
  - kill.flag                   — Kill Switch が発動した理由を保存
  - stop_requested.flag         — 外部からプロセス停止を要求するためのフラグ
  - execution.pid               — ExecutionEngine の PID
- logs/
  - execution.log
  - monitoring.log
  - その他アプリログ

---

## 注意事項 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live を使用し、LINE 通知や各種監視設定（しきい値）を入念に確認してください。
- 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に kill.flag が自動でクリアされます。誤った自動クリアは危険なので本番では 0 を推奨します。
- .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください。
- OpenAI を利用する機能は API 負荷やコストに注意し、実行頻度やバッチサイズを運用に合わせて調整してください。
- DuckDB/SQLite のバックアップ・スナップショットを定期的に取得してください。

---

この README はコードベース（src/kabusys 内）に基づいて作成しました。追加の実装（broker クライアント、ExecutionEngine の詳細、TradeMonitor 実装など）に応じて、本ドキュメントを更新してください。必要であれば各モジュールの API 例や具体的な運用手順を追記します。