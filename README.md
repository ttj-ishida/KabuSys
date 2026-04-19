# KabuSys

日本株向け自動売買システムのコードベース（簡易説明書）。  
この README はリポジトリ内の主要スクリプト・パッケージと起動・設定手順、主要機能をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・注文実行・監視・検証）を想定したコードベースです。  
主な設計方針：

- DuckDB を使った分析（research / ai 用）
- SQLite を使った軽量な監視・トレードログ保存
- 本番とペーパートレードを分離（paper_trading は専用 SQLite を使用）
- モジュール毎に責務を分離（portfolio, research, ai, monitoring, utils 等）
- 環境変数および .env による設定管理。対話式ウィザードと検証 CLI を提供

---

## 機能一覧

- 環境設定ウィザード（.env を作成 / 更新）
  - `python -m kabusys.config_setup`
- 設定ファイル検証 CLI（.env と config/*.yaml の基本チェック）
  - `python -m kabusys.validate_config [--strict]`
- Execution Engine 起動スクリプト（実際の発注処理の司令塔）
  - `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に分離
- Monitoring 起動スクリプト（SystemMonitor のポーリングループ）
  - `python -m kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成ツール
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
- ポートフォリオ構築ロジック（選定・重み・ポジションサイズ算出・セクター制限 等）
  - モジュール: `kabusys.portfolio`
- ファクター計算 / リサーチツール（DuckDB ベース）
  - モジュール: `kabusys.research`
- ニュース NLP（OpenAI）による銘柄スコアリング、レジーム判定（AI 統合）
  - モジュール: `kabusys.ai`（OpenAI API を使用）
- 監視コンポーネント（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager）
  - モジュール: `kabusys.monitoring`
- ロギングとプロセス優先度設定ユーティリティ
  - `kabusys.utils.logging_setup` / `kabusys.utils.process_priority`

---

## セットアップ手順（開発 / ローカル実行向け）

前提:
- Python 3.10 以上（型ヒントの | 記法などを使用）
- Git、pip

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 推奨インストール（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（任意だが config 検証で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください）

4. .env の初期作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、`python -m kabusys.validate_config` で検証してください。

5. データディレクトリを作成（必要に応じて）
   - デフォルトの DB / PID / フラグファイルは `data/` 配下に作成されます。
   - logs ディレクトリは自動作成されますが権限等で失敗する場合あり。

---

## 主要な環境変数（代表）

必須（実行前にセットまたは .env に記載）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要な任意 / 既定値:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒。run_monitoring で参照）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

注意: 自動環境変数読み込みはプロジェクトルートから `.env` / `.env.local` を順に読み込みます（環境変数が優先）。自動読み込みを抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表コマンド）

- 環境セットアップ（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB を使用
    - 起動時に `data/stop_requested.flag` が存在すると起動しません
    - 停止するには `data/stop_requested.flag` を作るか、`KillSwitch` が `data/kill.flag` を生成します
    - PID ファイル: data/execution.pid（デフォルト。 Settings で上書き可）

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定（デフォルト 60）
  - Monitoring はどの KABUSYS_ENV でも本番 sqlite_path を使って監視 DB を操作します
  - 停止フラグ: data/stop_requested.flag を作るとループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム検出）
  - 関数として呼び出し: `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime`
  - 実行には OPENAI_API_KEY が必要

ログ:
- ログはデフォルト `logs/` に日次ローテーションで保存されます（設定は `kabusys.utils.logging_setup`）。

停止フラグと Kill Switch:
- `KillSwitch` は監視コンポーネントが条件を満たした場合 `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。Execution 側は起動時に kill.flag の存在や `KILL_FLAG_CLEAR_ON_START` の設定に注意して動きます。

---

## ディレクトリ構成（主要ファイル・モジュール）

（リポジトリの `src/kabusys/` 配下の主要ファイル例）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI を利用して ai_scores を書込）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py   — 銘柄選定・スコアソート等
    - position_sizing.py     — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・CRUD
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — （トレード監視用、ログ参照）
    - risk_monitor.py        — ドローダウン監視・位置数監視
    - kill_switch.py         — kill.flag の書き込み / 管理
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - alert_manager.py       — アラート配送（LINE 等を想定）
  - utils/
    - logging_setup.py      — 共通ログ初期化
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
    - __init__.py

補足:
- `monitoring_db.py` は監視用の SQLite スキーマ初期化 & マイグレーションロジックを持ちます。
- `ai` 系は OpenAI API を使用するため、API キーとネットワーク接続が必要です。
- 研究・分析関連は DuckDB（ローカルファイル）を前提にしています。

---

## 開発メモ / 注意点

- データ永続化:
  - 分析用の DuckDB（デフォルト data/kabusys.duckdb）
  - 監視ログは SQLite（data/monitoring.db）
  - ペーパートレードは分離された SQLite（data/paper_trading.db）
- .env の扱い:
  - .env は絶対に Git にコミットしないこと
  - config_setup.py により安全に初期化できます
- 実行停止:
  - 長期実行プロセスは `data/stop_requested.flag` の存在で安全に停止します
  - 監視が条件を満たすと `data/kill.flag` が生成され、ExecutionEngine に停止を促します
- テスト / CI:
  - 自動環境読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に便利）
- 依存パッケージ・バージョンは環境に合わせて固定してください（requirements.txt を準備することを推奨）

---

## よくあるコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper トレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は以上です。必要であれば以下を追記できます：
- 詳細な環境変数一覧（表形式）
- サンプル .env.example
- systemd / supervisor 用のプロセス起動ユニット例
- Dockerfile / docker-compose の例

追記希望があれば教えてください。