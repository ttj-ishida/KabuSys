# KabuSys

日本株自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・研究用機能（DuckDBベースのファクター計算等）や、AI を使ったニュースセンチメント評価などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- DuckDB / SQLite を用いてマーケットデータやログを保持し、ファクター計算・ポートフォリオ構築を行います。
- ExecutionEngine によりブローカーへ発注し、paper_trading モードでは MockBroker を使用して本番 DB と完全に分離します（Paper 用 SQLite を使用）。
- Monitoring 系はシステム状態・注文状態・リスク監視を定期的に行い、必要に応じて kill.flag を書き込んで Execution を停止できます。
- ai.news_nlp / ai.regime_detector は OpenAI を利用した NLP 評価を行い、DuckDB 上のテーブルへスコアを格納します。
- 研究用のモジュール（research）では DuckDB の prices_daily / raw_financials 等を使ったファクター計算・IC 計算等を提供します。

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（発注管理、リスク管理、オーダーリポジトリ等）
  - paper_trading 環境切替（MockBroker + data/paper_trading.db）
- 監視（Monitoring）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 約定・滞留注文・ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager による停止通知 / アラート（LINE など）
  - run_monitoring.py / monitoring_engine 経由のポーリングループ
- データ / 研究
  - DuckDB ベースのファクター計算（momentum, volatility, value）
  - forward returns / IC / factor summary 等の統計関数
- AI 関連
  - news_nlp: ニュースをまとめて LLM に投げ、銘柄ごとのセンチメント ai_scores に保存
  - regime_detector: ETF 1321 の MA200 乖離 + マクロニュース LLM を合成して市場レジーム判定
- CLI / ユーティリティ
  - config_setup.py: .env の対話式ウィザード生成
  - validate_config.py: .env および config/*.yaml の起動前チェック
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

## 必要条件（推奨）

- Python 3.10 以上（| 型注釈などを使用）
- 必須パッケージ（少なくとも次をインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- あると便利:
  - PyYAML（config/*.yaml のパース検証に使用される。無ければ検証はスキップされる）

例:
```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／配置。
2. Python 仮想環境を作る（推奨）。
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # requirements.txt がある場合
   # または最低限:
   pip install duckdb psutil openai pyyaml
   ```
3. 初回設定（.env の作成）
   - 対話式で .env を作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に .env を作成して環境変数を設定してください。
4. 設定確認:
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

注意:
- 自動環境読み込み: パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を検出できれば `.env` / `.env.local` を自動ロードします。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。

---

## 環境変数（主なもの）

（.env で設定することを想定）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — AI 機能を使う場合に必要
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
  - paper_trading のときは paper 用 DB を使用
- PAPER_TRADING_SQLITE_PATH — Paper DB のパス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアするか（1/0）

---

## 実行・使い方

作業ディレクトリはプロジェクトルートを想定します（data/ logs/ 等にアクセス）。

### ExecutionEngine を起動する
- 通常の起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 実行環境が `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い、Paper DB（PAPER_TRADING_SQLITE_PATH）にログを記録します。`KABUSYS_ENV` は .env か環境変数で指定してください。
- ExecutionEngine は data/execution.pid を使って PID を管理します。
- 停止: run_execution は data/stop_requested.flag の検知でエンジンを停止します。手動停止する場合はこのファイルを作成してください（あるいはプロセスを SIGINT）。

### Monitoring を起動する
- 単体起動スクリプト:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔: 60秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（正の整数）。
  - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）へ書き込みします（監視は環境にかかわらず本番 sqlite_path を使う設計）。
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

### MonitoringEngine を単発でテスト実行
- テスト用に各 Monitor を組み合わせて 1 回だけ動かすことができます（直接 import して run_once を呼ぶケースなど）。
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を用います。

### Paper Trading の検証レポート
- paper_verification_report を使って Paper DB の集計レポートを出力できます:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db、`--db` オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

### 設定ウィザード / 検証
- .env 生成:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

---

## ログ

- ログの初期設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- デフォルトはコンソール（stdout）出力と日次ローテートのファイル出力（logs/<app_name>.log）です。ログディレクトリは環境変数 LOG_DIR や引数で変更可能。
- デフォルトログレベルは LOG_LEVEL 環境変数（デフォルト INFO）。

---

## 停止フラグ / Kill Switch の動作

- ExecutionEngine / Monitoring の継続ループを止めたいとき:
  - file: data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して順次終了します。
- KillSwitch（監視側）:
  - リスク条件（例: ドローダウン超過、ポジション上限超過）が満たされると data/kill.flag に理由を書き込みます。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動的に kill.flag を消します（本番では危険なので注意）。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュール構成です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — Execution 関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / risk_logs / dashboard / positions）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores に記録
    - regime_detector.py     — 市場レジーム判定（MA200 + macro sentiment）
  - tools/
    - paper_verification_report.py
  - data/                    — 既定の DB・フラグファイル・pid 等を配置（実行時に作成される）
  - logs/                    — ログファイル（デフォルト）

---

## 注意点 / 実運用のヒント

- Paper Trading と Live は DB を分離してください。paper_trading 環境では PAPER_TRADING_SQLITE_PATH を使用します。
- AI 機能を使う場合は OpenAI の API キー（OPENAI_API_KEY）を安全に管理してください。API の呼び出しはレート制限や 5xx を適切にリトライする実装になっていますが、コスト・レート制限に注意してください。
- monitor 系は監視ログ用の SQLite（Settings.sqlite_path）を使用します。監視はどの KABUSYS_ENV でも同一の sqlite_path を参照するよう設計されています（運用上の注意）。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで動作を継続します。
- 必須環境変数が未設定だと起動に失敗（ValueError）する箇所があります。`python -m kabusys.validate_config` を使用して事前確認してください。
- DB スキーマは冪等に初期化・マイグレーションされるよう実装されています（monitoring_db.init_monitoring_db）。

---

README はここまでです。特定のスクリプトやモジュールの使い方（ExecutionEngine の詳細な設定、BrokerClient の実装、AlertManager の外部通知設定など）についてさらに詳しいドキュメントが必要であれば、その箇所を指定してください。