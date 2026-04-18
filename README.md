# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト集です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視システム（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。主な目標は次のとおりです。

- 発注エンジンとリスク管理による安全な自動売買フロー
- 監視（システム状態・注文状況・リスク）と Kill Switch による運用保護
- ペーパートレーディング（本番 DB と分離）による検証
- DuckDB / SQLite を利用した分析およびログ保存
- ニュースを利用した LLM ベースのセンチメント評価とレジーム判定
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）やリサーチ用ユーティリティ

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注エンジン、別モジュールに実装）
  - BrokerClientFactory による実売買 / モック切替（KABUSYS_ENV=paper_trading）
  - 発注・約定ログの永続化（SQLite またはペーパートレード用 DB）

- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク・プロセス監視、データ鮮度チェック）
  - TradeMonitor / RiskMonitor による注文滞留やドローダウン監視
  - KillSwitch（条件に応じた data/kill.flag の書き込み）
  - MonitoringEngine（定期的に各モニタを呼ぶポーリングループ）
  - 監視ログ保存用 SQLite（monitoring_db: system_status, trade_logs, positions, risk_logs, dashboard）

- Portfolio / Position sizing
  - 候補選定（score / rank ベース）
  - 等配分・スコア加重配分
  - 単元株丸め、リスクベースの株数決定、aggregate cap（資金配分のスケーリング）
  - セクター制限（セクター集中の除外）、レジーム乗数

- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM でセンチメント評価 → ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 + マクロニュースで日次レジーム判定（bull/neutral/bear）
  - リトライ・JSON バリデーション・スコアクリップ等の実装

- ツール群
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

- ユーティリティ
  - logging 設定（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - 環境変数ロード（.env / .env.local、.git/pyproject.toml からプロジェクトルート検出）

---

## 前提 / 必要要件

- Python 3.10 以上（型記法や union | を使用しているため）
- 必要なパッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- SQLite（Python 標準ライブラリで利用）
- ネットワークアクセス（実運用で kabuステーション / OpenAI を使う場合）

環境依存パッケージは requirements.txt を用意している場合はそちらを使用してください。なければ手動でインストールします:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配布物を解凍
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env の作成
   - 自動で .env を読み込む仕組みがあります（プロジェクトルートに .env / .env.local があれば読み込み）。
   - 対話式ウィザードで作成するには:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE 等

4. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # 厳格モード（警告も FAIL とする）
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - デフォルトで使用するディレクトリ: data/ logs/
   - ログ出力先は LOG_DIR（デフォルト: logs/）

---

## 使い方（起動・運用）

### 実行エンジン（ExecutionEngine）を起動

- 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替:

  - ペーパートレード（MockBroker・専用 DB を使用）:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

  - 本番:
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```

- 起動時、プロセス優先度を高に設定し、SQLite / DuckDB に接続します。
- 実行中に停止したい場合:
  - 実行ループはプロジェクトルートの data/stop_requested.flag を監視しています。
  - 停止させるにはファイルを作成:
    ```bash
    mkdir -p data
    touch data/stop_requested.flag
    ```
  - また、Kill Switch によって data/kill.flag が書き込まれると、ExecutionEngine 側で検出して停止処理を行います（設定により起動時に kill.flag を自動クリアする挙動あり: KILL_FLAG_CLEAR_ON_START）。

- 実行時の PID ファイル: data/execution.pid（デフォルト）を使用します。

### 監視ループを起動

- Monitoring は監視専用プロセスです。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数指定（デフォルト: 60 秒）。

```bash
python -m kabusys.run_monitoring
# 例（30秒ごと）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 監視は常に本番用 sqlite_path を使います（KABUSYS_ENV にかかわらず）。監視スクリプトは data/stop_requested.flag を確認してループを抜けます。

### 設定関連ツール

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

### Paper Trading 検証レポート

- ペーパートレード DB の検証レポートを生成します。

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### AI / リサーチ機能の利用

- news_nlp.score_news、regime_detector.score_regime、research の各関数はプログラム的にインポートして使用します。OpenAI を使う処理は OPENAI_API_KEY を環境変数に設定してください。

---

## 運用時の注意点 / 実装上のポイント

- KABUSYS_ENV:
  - development, paper_trading, live のいずれか。live は本番なので注意して設定してください。
- ペーパートレード:
  - paper_trading の場合、発注は MockBrokerClient を使用し、データは data/paper_trading.db（デフォルト）に分離されます。
- Kill Switch / stop flag:
  - KillSwitch（監視側）によって data/kill.flag が書き込まれると ExecutionEngine に停止シグナルを送ります。
  - run_execution/run_monitoring は data/stop_requested.flag を使って終了を制御します。
- ログ:
  - ルートロガーは console (stdout) と 日次ローテートファイルに出力されます（logs/<app_name>.log）。
  - LOG_DIR 環境変数でログ出力先を指定可能。
- OpenAI / API 呼び出し:
  - API はリトライやバックオフ、レスポンス検証を備えていますが、キー未設定時はエラーとなります。AI モジュールはフェイルセーフとして失敗時に大きな障害を起こさないよう設計されています（スコア 0.0 フォールバックなど）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に不足するカラムがあれば ALTER を行います。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートにした主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/                — 発注エンジン関連（別途ファイル群）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py        — （参照のみ。trade 関連ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — レジーム判定（MA200 + マクロニュース）
    - __init__.py

  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

  - tools/
    - paper_verification_report.py

- config/
  - system_config.yaml (期待される設定ファイルのテンプレート等)
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/                      — デフォルトで使用するデータ・フラグファイル等（実行時に作成）
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kabusys.duckdb (DuckDB)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                      — ログ出力先（デフォルト）

---

## よくある操作例

- .env を作る（ウィザード）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定チェック:
  ```bash
  python -m kabusys.validate_config
  ```

- 監視を起動（60秒ごと）:
  ```bash
  python -m kabusys.run_monitoring
  ```

- 実行エンジンをペーパートレードで起動:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート出力:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- 強制停止（監視/実行ループ共通）:
  ```bash
  mkdir -p data
  touch data/stop_requested.flag
  ```

---

## 補足 / 推奨事項

- 本番運用時は KABUSYS_ENV=live にし、LINE 通知等のアラート設定を行ってください。validate_config は本番向けの注意点を表示します。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py でも注意書きあり）。
- OpenAI を利用する場合は利用コストとレイテンシを考慮し、必要に応じてバッチサイズやトークン制限の調整を行ってください。
- 監視・KillSwitch は運用安全のための重要機能です。設定（ドローダウン閾値、ポジション上限、KILL_FLAG_CLEAR_ON_START 等）を運用方針に従って適切に構成してください。

---

この README はコードベースの主要機能・使い方を簡潔にまとめたものです。実装の詳細や追加のコマンドライン引数は各モジュール（run_execution.py、run_monitoring.py、config_setup.py、validate_config.py、tools/*）のドキュメント文字列やソースコードを参照してください。もし README に追記したい内容（セットアップ手順の詳細、デプロイ例、Dockerfile、CI 設定など）があれば教えてください。