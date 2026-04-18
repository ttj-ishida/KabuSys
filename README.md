# KabuSys

日本株自動売買システムのコアライブラリ（README 日本語版）

このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、Execution（発注）エンジン、監視（Monitoring）、および AI/LLM を用いたニュース評価を含む自動売買プラットフォームの主要コンポーネント群を提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成されています。

- 環境設定・読み込み（.env の自動読み込み / ウィザード / 検証）
- ExecutionEngine（実際の発注ロジック、paper_trading モード対応）
- Monitoring（システム稼働監視、注文ログ・リスク監視、Kill Switch）
- Portfolio（候補選定、重み計算、サイズ計算、セクター制限）
- Research（DuckDB を用いたファクター計算・特徴量解析）
- AI（ニュースの LLM ベースセンチメント評価、市場レジーム判定）
- 便利なツール（paper trading 検証レポート生成 等）
- ユーティリティ（ログ設定、プロセス優先度設定など）

設計の要点としては、「外部副作用を最小にした純粋関数化」「本番 DB とペーパートレード DB の分離」「LLM 呼び出しは安全にリトライしフェイルセーフにする」等が挙げられます。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config — .env と config/*.yaml の検証）
- Execution エントリ（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring エントリ（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
- Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
- RiskMonitor（ドローダウン、ポジション数上限の監視）
- Trade/Order ロギング（trade_logs）
- Research: ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI: ニュース NLP（OpenAI を使った銘柄ごとのセンチメント算出）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ログ設定ユーティリティ（標準化されたコンソール + 日次ローテーションファイル）

---

## セットアップ手順（開発 / 実行）

※ 依存パッケージはプロジェクトの requirements.txt あるいは pyproject.toml を参照してインストールしてください。主な依存（抜粋）: duckdb, psutil, openai, sqlite3（標準）、PyYAML（config 検証で任意）など。

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -r requirements.txt
   - もしくは pyproject.toml がある場合はそれに従ってください。

4. 初期環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

5. データディレクトリ（logs, data 等）は自動で作成される場合がありますが、必要に応じて手動で作成してください。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/..、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 関連処理で必要）
- PAPER_FILL_MODE — ペーパートレードの約定動作（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

.env の自動読み込みルール:
- OS 環境変数 > .env.local > .env の順で読み込まれます。
- プロジェクトルートは .git または pyproject.toml を基準に定義されます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（代表的なコマンド例）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - 通常（開発/本番）:
    - python -m kabusys.run_execution
  - ペーパートレード（mock broker、専用 DB 使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  注意:
  - run_execution は data/stop_requested.flag を監視してログで停止します。
  - 実行時に data/execution.pid が生成されます（PID ファイル）。

- Monitoring（監視ループ）起動
  - デフォルト（60 秒ポーリング）:
    - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  監視対象:
  - システム稼働（CPU / memory / disk / Execution プロセス生存）
  - trade_logs / risk_logs / dashboard の更新
  - Kill Switch の評価（ドローダウン・ポジション上限 など）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / Regime / News スコア関連（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=...) — raw_news を LLM で評価して ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...) — 市場レジーム判定

---

## 停止・Kill Switch の扱い

- 手動停止: プロセスを Ctrl+C（KeyboardInterrupt）で停止できます。
- 停止フラグ: data/stop_requested.flag が存在すると run_monitoring/run_execution は起動中に検知して優雅に停止します。
- Kill Switch: KillSwitch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine 側は設定された kill_flag_path を参照して停止等の対応を取る設計です。
- 起動時に kill.flag を自動クリアしたい場合は .env の KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番環境では推奨されません）。

---

## ロギング

- ログは標準出力（stdout）に出力され、加えて日次ローテートされるファイルハンドラ（logs/<app_name>.log）へ書き込まれます。
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定できます。

---

## ディレクトリ構成（概要）

以下は主要なファイル・モジュールのツリー（src/kabusys 配下を抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — Settings クラス, .env 自動ロードロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコア
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算（リスクベース等）
    - risk_adjustment.py     — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / summary 等
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ・永続化ロジック
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の作成・管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - trade_monitor.py       — （注文滞留・異常チェック等、参照）
    - alert_manager.py       — （LINE 等へ通知する機能、参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（発注セッション）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - data/                    — 実行時に生成されることがあるディレクトリ（data/*.db, pid, flag 等）
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

（注）上記のファイルはリポジトリ全体から抜粋したものです。実際の構成はリポジトリ内のファイル一覧をご確認ください。

---

## 開発者向けメモ / 注意点

- DB 分離:
  - monitoring（監視）用の SQLite は settings.sqlite_path（デフォルト data/monitoring.db）
  - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離
- LLM 呼び出し:
  - OpenAI API 呼び出しにはリトライロジックと JSON バリデーションが組み込まれています。API キーは OPENAI_API_KEY で指定してください。
- DuckDB:
  - 分析向けテーブル（prices_daily, raw_financials, raw_news など）は DuckDB を用いて高速に集計します。パスは DUCKDB_PATH 環境変数で変更できます。
- テスト可能設計:
  - LLM 呼び出しなど副作用のある関数は差し替え可能（テスト時に patch などでモック化しやすい構造）。

---

## よくある操作例（まとめ）

- .env を作成する:
  - python -m kabusys.config_setup

- 設定を検証する:
  - python -m kabusys.validate_config
  - (問題がなければ exit 0)

- monitoring を起動する（ポーリング 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレードで Execution を起動する:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張します（詳細な設定項目、config/*.yaml の説明、ExecutionEngine の操作方法、AlertManager の設定例、CI / デプロイ手順 など）。どの項目を追加したいか教えてください。