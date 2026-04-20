# KabuSys

バージョン: 0.1.0

日本株自動売買システムの一部（バックエンドライブラリ・起動スクリプト・監視/検証ツール群）です。本リポジトリはポートフォリオ構築、注文発注エンジン、監視・アラート、ファクター/リサーチ、AI（ニュースNLP/レジーム判定）などのコンポーネントを含みます。

---

## 概要

KabuSys は日本株の自動売買を想定したモジュール群です。モジュールは責務ごとに分離されており、起動スクリプトから組み合わせて利用します。主な設計方針は次の通りです。

- 設定は環境変数（`.env`）で管理。対話式のウィザードで `.env` を生成可能。
- 本番（live）とペーパートレード（paper_trading）を明確に分離。ペーパートレードは専用 SQLite DB を使用。
- DuckDB を分析・リサーチ用途に使用、SQLite は監視・発注ログ用。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントやレジーム判定サポート（API キー必須）。
- 監視コンポーネントは kill flag ファイルで ExecutionEngine 停止をトリガできる。

---

## 主な機能一覧

- 設定管理
  - `.env` 自動ロード / 対話式ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）

- 起動スクリプト
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使い `data/paper_trading.db` に記録
  - Monitoring 起動スクリプト（`run_monitoring.py`）
    - 監視ポーリングループ。環境変数 `MONITOR_POLL_INTERVAL` で間隔上書き可

- 監視（monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス、データ鮮度監視
  - TradeMonitor：注文・約定ログの健全性チェック（滞留注文・約定異常など）
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch：条件に応じて `data/kill.flag` を書いて ExecutionEngine 停止を指示
  - Monitoring DB（SQLite）スキーマ管理（`monitoring_db.py`）

- ポートフォリオ構築（pure functions）
  - 候補選定、等配分/スコア加重配分、ポジションサイズ算出、セクター制限、レジーム乗数

- リサーチ / ファクター計算（DuckDB）
  - Momentum, Volatility, Value ファクター計算
  - 将来リターン, IC（Information Coefficient）, 統計サマリー 等

- AI（OpenAI）
  - ニュース NLU（ニュースを集約して銘柄ごとにセンチメントを算出、`news_nlp.py`）
  - レジーム判定（ETF MA + マクロニュースセンチメントの合成、`regime_detector.py`）

- ツール
  - Paper Trading 検証レポート生成（`tools/paper_verification_report.py`）

- ユーティリティ
  - ログ設定（`utils/logging_setup.py`）
  - プロセス優先度 / CPU affinity 設定（`utils/process_priority.py`）
  - 設定クラス（`config.py`）

---

## 動作要件（想定）

- Python 3.9+（型アノテーションや pathlib 利用のため）
- 外部ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
  - PyYAML（config YAML 検証に任意で使用）
- SQLite（標準ライブラリで利用可能）

requirements.txt は本リポジトリに含まれていないため、上記パッケージを手動でインストールしてください。

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（概略）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（`.env.example` を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: `.env` は絶対にバージョン管理にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備（自動作成されることが多いですが手動で作る場合）
   - mkdir -p data logs

---

## 使い方（主要コマンド/スクリプト）

- 環境設定ウィザード（`.env` 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視サービス起動（フォアグラウンド）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で上書き可能:
    - export MONITOR_POLL_INTERVAL=30

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV 環境変数により挙動が変わります（paper_trading・live・development）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

- AI 機能（ニューススコア/レジーム判定）
  - OpenAI API キーを環境変数に指定（または API 呼び出し時に引数で渡す）
    - export OPENAI_API_KEY=sk-...
  - モジュール API を呼び出して利用:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/利用に応じて:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合はモックブローカー・専用 DB を使用
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE: paper trading の fill 動作（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番での kill.flag 自動クリア（要注意）

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると `.env` の自動読み込みを抑止します。

---

## kill.flag / stop フラグ

- 停止指示:
  - 監視コンポーネント（KillSwitch）が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
- 起動停止フラグ:
  - run_monitoring/run_execution は `_STOP_FLAG`（path: data/stop_requested.flag）を検知してループを終了します。
- ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` 設定に基づき kill.flag を自動クリアするかを決めます（本番ではオフ推奨）。

手動でクリアする場合:
- rm data/kill.flag

---

## ログについて

- ログはルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト: logs/<app_name>.log、日次ローテーション・30日保持）を設定します。
- ログレベルは、関数引数 -> 環境変数 `LOG_LEVEL` -> デフォルト `INFO` の順で決まります。
- ログディレクトリが作れない場合はファイル出力をスキップしてコンソール出力のみになります。

ログ設定ユーティリティ:
- kabusys.utils.logging_setup.setup_logging(app_name="execution")

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings クラス（自動 .env ロード含む）
- config_setup.py                — .env 対話ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — Monitoring 起動スクリプト

src/kabusys/utils/
- logging_setup.py               — ログ設定ユーティリティ
- process_priority.py            — プロセス優先度 / CPU affinity
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py               — SQLite スキーマ & 永続化 API
- system_monitor.py              — システム状態 / データ鮮度監視
- trade_monitor.py               — 注文/約定監視（ファイル中のトリガ参照）
- risk_monitor.py                — ドローダウン・ポジション監視
- kill_switch.py                 — Kill Switch 管理
- monitoring_engine.py           — 各 Monitor を束ねるエンジン
- alert_manager.py               — （アラート送信、実装部分）

src/kabusys/execution/
- execution_engine.py            — ExecutionEngine（エントリは run_execution）
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py                    — ニュースセンチメント（OpenAI）
- regime_detector.py             — 市場レジーム判定（OpenAI）
- __init__.py

src/kabusys/tools/
- paper_verification_report.py   — ペーパートレード検証レポート生成
- __init__.py

データ / ログ等（リポジトリルート想定）
- data/                          — デフォルト DB / flag / pid ファイル置き場
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 時)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/

---

## 注意点 / 運用メモ

- KABUSYS_ENV によって DB 分離やブローカーの挙動が変わります。特に `live` は実取引になるため設定を慎重に確認してください。
- `.env` 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。CI やテストで自動ロードを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使用する AI 機能は API 利用料が発生します。API キー管理・呼び出し頻度に注意してください。
- SQLite / DuckDB のパスは Settings 経由で変更できます（環境変数で上書き）。
- ログ/DB ディレクトリへの書き込み権限を事前に確認してください。ログディレクトリが作成できない場合はファイル出力が無効化されます。

---

## 開発者向け補足

- 主要コンポーネントは可能な限り副作用を小さく保つ設計になっています（例: portfolio モジュールは純粋関数）。
- モジュール単体のユニットテストを推奨します（外部 API 呼び出しはモックすること）。
- DuckDB クエリは SQL を使って高効率に集計する設計です。テーブルスキーマやインデックスを変更する場合はリサーチ/AI モジュール側の期待を確認してください。

---

README は簡潔に要点をまとめています。さらに詳細な API 使用例や ExecutionEngine の内部仕様（ブローカー実装・注文フロー等）については該当するモジュールの docstring とソースを参照してください。必要であれば README に追記しますので、注力してほしい箇所を教えてください。