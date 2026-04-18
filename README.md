# KabuSys

日本株向け自動売買システムの一部を収めた Python パッケージ（ドキュメント化用 README）。  
この README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

> 前提: Python 3.10+ を想定（型記法に | を使用しているため）。実行に必要な外部ライブラリは後述します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を支援するモジュール群です。本リポジトリには以下の主要機能が含まれます。

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution）
  - 本番 / ペーパートレードの分離（paper_trading 環境では MockBroker を使用し、専用 DB に記録）
- Monitoring（監視）機能（run_monitoring / MonitoringEngine）
  - システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期モニタリング
  - Kill Switch（停止フラグ）により外部から安全にエンジンを停止可能
- ポートフォリオ構築・ポジションサイジング（portfolio）
  - 候補選定、重み計算、セクター制限、単元丸め、資金配分ロジック
- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value 等）、IC 計算、将来リターン算出
- AI 補助モジュール（ai）
  - ニュース NLP による銘柄センチメント、マクロニュースを用いた市場レジーム判定
- ユーティリティ（utils）
  - ロギング設定、プロセス優先度設定、その他共通処理
- 各種 CLI ユーティリティ
  - .env 対話式設定ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - Paper Trading 検証レポート（tools/paper_verification_report）

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV に応じて本番/ペーパー切替。
  - 発注管理、リスク管理、リコンサイルを統合してセッション実行。
- run_monitoring.py
  - SystemMonitor をポーリング実行し system_status / trade_logs / risk_logs / dashboard を更新。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
- config_setup.py
  - 対話式に .env を作成・更新するウィザード。
- validate_config.py
  - .env / config/*.yaml の存在や基本整合性を起動前にチェック。
- tools/paper_verification_report.py
  - Paper Trading 用 SQLite から期間指定の検証レポートを出力（稼働率・注文成功率・レイテンシ等）。
- monitoring/*（MonitoringDB, RiskMonitor, SystemMonitor, TradeMonitor, KillSwitch, AlertManager 等）
  - 監視ログの永続化、ドローダウン監視、滞留注文検出、kill/alert ロジック。
- portfolio/*
  - 候補選定（select_candidates）、重み（equal/score）、ポジションサイズ算出（risk_based 等）、セクター制限、レジーム乗数。

---

## 必要な依存パッケージ（代表）

実行には以下の外部パッケージが必要です（プロジェクトで要求されるバージョンに合わせてください）。

- duckdb
- psutil
- openai
- PyYAML（config ファイル検証をする場合。省略可）
- （SQLite3 は標準ライブラリ）

もし requirements.txt がある場合はそれを利用してください。なければ下記のように最小限をインストールします:

```bash
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開し、仮想環境を作成して有効化します。

2. 依存パッケージをインストールします（上記参照）。

3. 初期環境変数（.env）を作成します（対話式）:

```bash
python -m kabusys.config_setup
```

- J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）や kabuステーション API パスワード（KABU_API_PASSWORD）は必須です。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかを設定します。

4. 設定検証を実行して問題がないか確認します:

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. 必要に応じてデフォルトのデータディレクトリ（例: data/）を作成します。多くのスクリプトは起動時に自動作成しますが、権限等に注意してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant / partial / never / reject) — MockBroker の挙動
- OPENAI_API_KEY (AI モジュールを使う場合)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
- KILL_FLAG_CLEAR_ON_START (0/1) — 実行時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数上書き）

---

## 使い方（起動・ツール）

基本的にモジュールとして起動するのが簡単です（パッケージのルートで実行）。

- 監視ループを起動（SystemMonitor の定期ポーリング）:

```bash
# デフォルト: MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
# ポーリング間隔を変更する例:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- Execution エンジンを起動（本番 / ペーパーはいずれも Settings に従う）:

```bash
python -m kabusys.run_execution
```

- .env の対話式作成:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
```

- Paper Trading の検証レポート生成:

```bash
# デフォルト DB は data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI / リサーチ関数はモジュール API として利用できます（例: kabusys.ai.score_news、kabusys.research.calc_momentum など）。スクリプトから呼ぶ場合は DuckDB 接続や API キーを適切に渡してください。

---

## 停止 / Kill Switch の扱い

- 強制停止シグナルはファイルベースで実装されています:
  - 停止リクエスト（運用用）: data/stop_requested.flag — run_monitoring / run_execution が検知して順次終了します。
  - Kill Switch（自動停止）: data/kill.flag — KillSwitch が書き込むと ExecutionEngine に停止指示を与えます。
- 実行開始時に kill.flag を自動でクリアしたい場合は `.env` の KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番環境では 0 を推奨します。

---

## ログ

- ログは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
  - コンソール（stdout）出力 + 日次ローテーションファイル（デフォルト logs/<app_name>.log）を利用。
  - LOG_DIR 環境変数でログディレクトリを上書き可能。
  - LOG_LEVEL 環境変数または引数でログレベルを制御します。

---

## よくあるトラブルシューティング

- OpenAI API を使うモジュールで "API key が未設定" エラーが出た場合:
  - 環境変数 OPENAI_API_KEY を設定するか、該当関数に api_key 引数で渡してください。
- PyYAML 未インストール時:
  - validate_config は YAML の内容検証をスキップしますが、ファイルの存在チェックは行います。PyYAML を入れるとパース検証が有効になります。
- DuckDB / SQLite のファイルが見つからないとき:
  - 環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を確認。config_setup で指定可能。
- process priority の設定に失敗しても多くの場合は警告で済みます（権限不足など）。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要ファイル / サブパッケージの一覧（本リポジトリに含まれるものを抜粋）。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照用; 実装あり)
    - kill_switch.py
    - alert_manager.py (参照用; 実装あり)
  - execution/
    - execution_engine.py (実行エンジン本体)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に用いるファイル)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db / paper_trading.db / kabusys.duckdb 等

（注）上記はコード上で参照される主要モジュール群の一覧で、実際のリポジトリに含まれるファイル構成に依存します。

---

## 開発者向けメモ

- Settings クラス（config.py）を通じて環境変数を一元管理しています。直接 os.environ を参照するのではなく Settings を利用してください。
- MonitoringDB の init_monitoring_db は冪等でテーブル・インデックスを作成し、簡単なスキーママイグレーションも行います。
- AI 関連の外部 API 呼び出しはリトライ・フォールバックを組み込んでおり、失敗時はフェイルセーフ（スコアを 0 にするなど）の動作があります。
- データベースは運用上 DuckDB（分析）と SQLite（監視 / 発注ログ等）を併用します。Paper Trading 時は sqlite を分離して記録します。

---

必要であれば README にサンプル .env の雛形、より詳細なディレクトリツリー、各モジュールの API 使用例（コードスニペット）なども追記できます。どの情報を優先して追加しますか？