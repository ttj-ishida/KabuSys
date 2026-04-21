# KabuSys

日本株を対象とした自動売買システムのコードベースです。戦略の研究/ファクター計算、ポートフォリオ構築、発注実行、監視（モニタリング）や AI（ニュースセンチメント／レジーム判定）を含むコンポーネント群で構成されています。

注意: これはプロジェクトの一部ソースに基づく概要ドキュメントです。実運用前に .env の設定や config/*.yaml の内容を十分に確認してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・実行コマンド）
- 環境変数（主要項目）
- ファイル・ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュールで構成された自動売買フレームワークです。

- データ処理 / 研究: DuckDB を使ってファクター計算や将来リターン・IC などの研究処理を行う（kabusys.research）。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限など（kabusys.portfolio）。
- 発注・実行エンジン: ブローカークライアント経由で注文を発行する ExecutionEngine（kabusys.execution）。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading DB に記録して本番 DB と完全分離。
- 監視: System / Trade / Risk のモニタリング、アラート管理、Kill Switch（kabusys.monitoring）。
- AI モジュール: ニュースを LLM（OpenAI）に投げて銘柄ごとのセンチメントを算出、レジーム判定（kabusys.ai）。
- ユーティリティ: ロギング設定、プロセス優先度や CPU affinity 設定、設定読み込みウィザードなど（kabusys.utils, kabusys.config_*）。
- CLI ツール: 設定ウィザード、設定検証、Paper Trading 検証レポート生成など（config_setup.py, validate_config.py, tools.paper_verification_report）。

---

## 主な機能一覧

- 設定読み込み・検証
  - .env 自動ロード（プロジェクトルートに基づく）
  - 対話式ウィザードで .env 作成（kabusys.config_setup）
  - 設定ファイル（config/*.yaml）含め起動前チェック（kabusys.validate_config）
- 発注実行
  - 実ブローカー or ペーパートレード切替（KABUSYS_ENV）
  - リスク制御（RiskManager）、OrderManager、Reconciler を内蔵
- モニタリング
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、プロセス稼働監視
  - 取引ログ監視、滞留注文や約定異常の検出
  - リスク監視（ドローダウン、ポジション上限）および Kill Switch（data/kill.flag）
  - 永続化は SQLite（data/monitoring.db 等）
- 研究・分析
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC（スピアマン）やファクター統計量
- AI（OpenAI）連携
  - ニュースから銘柄ごとのセンチメントスコアを生成（JSON モード・バッチ）
  - マクロニュースと ETF MA を合成した市場レジーム判定
- レポート
  - Paper Trading データから検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

以下は開発/試用環境向けの簡易手順です。プロダクション配備は追加の運用設定（サービス化、監視、権限管理等）が必要です。

1. Python 環境の準備
   - Python 3.10+ 推奨（コードは型注釈に Python 3.10+ 機能を使っています）
   - 仮想環境を作ることを推奨:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 主要依存:
     - duckdb
     - psutil
     - openai （OpenAI Python SDK）
     - pyyaml（設定検証で YAML をパースする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - ※ requirements.txt がある場合はそれを使ってください（この README を作成したソースには同梱されていない可能性があります）。

3. プロジェクトルートに移動
   - このリポジトリ構成ではパッケージソースが `src/` 下にある想定です。
   - 開発時は PYTHONPATH を設定するか、パッケージをインストールします:
     - export PYTHONPATH=$(pwd)/src
     - あるいは pip install -e . （setup.py/pyproject.toml が整備されている場合）

4. .env の準備
   - `python -m kabusys.config_setup` を使うと対話形式で .env を生成できます。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他：KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY など

5. 設定検証
   - `python -m kabusys.validate_config` を実行して起動前チェックを行ってください。
   - `--strict` を付けると警告もエラー扱いになります。

6. データディレクトリ
   - デフォルトで `data/` 以下に DB やフラグファイルを作成します。必要に応じて .env でパスを変更してください。
   - ログは `logs/` に日次ローテートで出力されます。

---

## 使い方

主要コマンド（パッケージ参照パスが通っている前提: プロジェクトルートで `export PYTHONPATH=src` など）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中の PID は data/execution.pid に書き込まれます。
    - プロセス優先度を high に設定します（権限が必要な場合あり）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（monitoring DB）を使用します。
    - 停止指示はプロジェクトルート/data/stop_requested.flag により検知します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能（デフォルト: data/paper_trading.db）

- AI 関連
  - ニューススコアリング (プログラム API)
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用上のフラグ/ファイル
- 停止リクエスト: data/stop_requested.flag
- Kill Switch（Execution 停止）: data/kill.flag（KillSwitch が作成）
- PID ファイル（Execution）: data/execution.pid
- ログ: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）

---

## 環境変数（主要項目）

以下はこのコードベースで参照される代表的な環境変数です。重要なものは .env に設定してください。

- 必須（運用により必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境・挙動
  - KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- 監視/実行制御
  - PID_FILE_PATH — Execution の pid ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

- 実行オプション（短期上書き）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

---

## ディレクトリ構成（抜粋）

以下はソースの主要ファイル・モジュールを抜粋した構成例です（src 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / Settings 管理
    - config_setup.py                 — .env 対話ウィザード
    - validate_config.py              — 設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート
    - utils/
      - __init__.py
      - logging_setup.py              — ロギングの初期化ユーティリティ
      - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py              — SQLite ログ永続化層
      - system_monitor.py             — システム状態・データ鮮度監視
      - trade_monitor.py              — 取引ログ監視（該当ファイルはここに実装想定）
      - risk_monitor.py               — ドローダウン・ポジション数監視
      - monitoring_engine.py          — 各モニタ束ねるエンジン
      - kill_switch.py                 — kill.flag 書き込みユーティリティ
      - alert_manager.py              — アラート送信（LINE など。該当ファイルはここに実装想定）
    - execution/
      - execution_engine.py           — 実行エンジン（EngineConfig 等）
      - broker_factory.py             — BrokerClient の生成（Mock/実ブローカー切替）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py          — 候補選定 / 重み計算
      - position_sizing.py            — 発注株数計算
      - risk_adjustment.py            — セクター制限 / レジーム乗数
      - __init__.py
    - research/
      - factor_research.py            — momentum/value/volatility 計算
      - feature_exploration.py        — forward returns / IC / summary
      - __init__.py
    - ai/
      - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
      - __init__.py

（注）上記はこの README を作成した時点で確認できる主要ファイル群の抜粋です。実際のリポジトリではさらにファイル・モジュールが存在する可能性があります。

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）での起動前に必ず `python -m kabusys.validate_config` で設定を確認してください。LINE の通知設定や Kill Switch の挙動など本番特有の警告があります。
- Kill Switch（data/kill.flag）は本番環境で誤ってクリアされないよう注意してください（KILL_FLAG_CLEAR_ON_START=0 推奨）。
- OpenAI を使う処理は API 呼び出し費用が発生します。キーの管理やレート制限に注意してください。news_nlp/regime_detector は失敗時にフォールバックする設計ですが、運用ポリシーを明確にしてください。
- ログと DB の保守（古いログのアーカイブ、DB バックアップ）を定期的に行ってください。
- プロセス優先度や PID 書き込みは OS 権限に依存します。必要に応じて systemd / supervisor 等でプロセス管理してください。

---

必要であれば、README に追記する内容（例: requirements.txt の具体的な内容、systemd ユニットファイルの例、詳細な設定ファイルテンプレート、各モジュールの API リファレンスなど）を教えてください。