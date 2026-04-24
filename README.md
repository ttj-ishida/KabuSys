# KabuSys

日本株自動売買システムの一部モジュール群。ポートフォリオ構築、リスク制御、モニタリング、研究用ファクター計算、LLM を用いたニュース/NLP 周りの処理などを含みます。

この README はリポジトリ内の主要なスクリプト / モジュールの説明、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたライブラリ兼実行環境です。主な機能は以下の通り：

- 実行エンジン（ExecutionEngine）と監視（Monitoring）コンポーネントの起動スクリプト
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リスク調整（セクター上限、レジーム乗数）
- モニタリング（システム・注文・リスク監視、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI（OpenAI を用いたニュースセンチメント、レジーム検出）
- ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 各種永続化（SQLite：監視ログ、DuckDB：価格データ・分析用）

設計方針の例：
- 本番環境とペーパートレードは DB を分離して扱える
- LLM 呼び出しはエラー耐性（リトライやフォールバック）を持たせる
- .env を利用した環境変数ベースの設定管理
- DuckDB を用いた分析処理（prices_daily / raw_financials 等）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
- 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 指定で MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite）による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor：ドローダウン監視、ポジション上限監視、アラート記録
- KillSwitch：条件に応じて data/kill.flag を作成して ExecutionEngine を停止
- AI モジュール：
  - news_nlp.score_news(): ニュース記事を LLM でスコアリングして ai_scores に書込
  - regime_detector.score_regime(): ma200 とマクロニュースの LLM 評価を合成して market_regime を更新
- 研究用：
  - calc_momentum / calc_volatility / calc_value（DuckDB 経由でファクターを計算）
  - feature_exploration: 将来リターン計算、IC（情報係数）等
- ツール：
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

---

## セットアップ手順（開発環境向け）

1. リポジトリを取得
   - git clone ... ; cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージ（例）
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証（validate_config の YAML 検証）で任意：pip install PyYAML
   - 実際の requirements.txt がない場合は上記を参考に追加してください。

4. 環境変数設定
   - 推奨: python -m kabusys.config_setup を実行して .env を作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を環境変数に設定
   - 自動 .env ロードはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告を FAIL とみなします

6. データディレクトリ
   - デフォルトで以下のファイルを使用します（必要に応じて .env で上書き）
     - data/kabusys.duckdb （DuckDB）
     - data/monitoring.db （監視用 SQLite）
     - data/paper_trading.db （ペーパートレード用 SQLite、KABUSYS_ENV=paper_trading 時）
     - logs/ ディレクトリ（ログ出力先）

---

## 使い方（起動例・コマンド）

- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - ペーパートレードモード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は data/paper_trading.db に記録され、本番 DB と分離されます

- Paper Trading 検証レポート（DB 解析）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- プログラム API（例）
  - AI スコアリング（プログラムから呼ぶ例）
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn = duckdb.connect(...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます
  - LOG_DIR 環境変数や setup_logging の引数で変更可能

- 停止 / Kill Switch
  - 実行停止を指示するファイル:
    - data/stop_requested.flag — run_monitoring / run_execution がこのファイルを検知すると停止します
    - data/kill.flag — KillSwitch が作成すると ExecutionEngine に停止シグナルとして機能します
  - KillSwitch をクリアするにはファイルを削除します（設定により起動時に自動クリア可）

---

## 主要環境変数（主なもの）

- KABUSYS_ENV: execution 環境（development, paper_trading, live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使う場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番での自動 kill.flag クリア（0 推奨）

自動 .env ロード:
- プロジェクトルートにある .env / .env.local を自動で読み込みます（OS 環境変数を優先）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理
- config_setup.py          — .env 作成ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — 監視ループ起動スクリプト
- run_execution.py         — 実行エンジン起動スクリプト

modules / サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py     — レジーム判定（ma200 + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（テーブル作成・DB 操作）
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — 注文監視（概念）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch 管理（flag ファイル）
  - monitoring_engine.py   — Monitor をまとめるエンジン
  - alert_manager.py       — （アラート送信機構）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・資金配分
  - risk_adjustment.py     — セクター制限・レジーム乗数
- research/
  - factor_research.py     — Momentum/Volatility/Value 等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — 共通ログ設定
  - process_priority.py    — プロセス優先度 / CPU affinity
- monitoring/monitoring_db.py  — DB スキーマ初期化、MonitoringDB クラス

（注）実行エンジン（ExecutionEngine）や broker 関連の実装はこの README の時点のコードベースに依存します。実際の完全な機能はリポジトリ内の他ファイルにも依存します。

---

## 注意事項・運用上のヒント

- 本番運用時は KABUSYS_ENV=live を正しく設定し、LINE 通知等の設定を確認してください。validate_config が本番向けの追加チェックを行います。
- OpenAI を使う機能は API キーが必要で、コストが発生します。API の失敗はフェイルセーフ（ゼロフォールバック等）を備えていますが、運用ポリシーを検討して下さい。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。ログディレクトリの権限を確認してください。
- Monitoring は監視 DB を用いて本番 sqlite_path を参照します（環境にかかわらず監視 DB パスを使用）。
- ペーパートレードは本番 DB と分離されます。KABUSYS_ENV=paper_trading を利用してください。

---

README はここまでです。プロジェクトの各スクリプトやモジュールについてより詳しい使い方や API 例が必要であれば、対象モジュール（例: news_nlp, regime_detector, portfolio.position_sizing 等）について具体的なドキュメントを作成しますので教えてください。