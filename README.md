# KabuSys

日本株自動売買システムの一部を集めた Python パッケージ。  
市場データの集計・ファクター計算、ポートフォリオ構築、発注エンジン（実行/ペーパートレード）、監視、LLM を用いたニュースセンチメント評価などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## 主な機能

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モード：MockBrokerClient を使用し、本番 DB と分離した `data/paper_trading.db` に記録
  - Kill Switch（フラグファイル）で外部からエンジンを停止

- 監視系
  - System / Trade / Risk の各 Monitor を束ねた MonitoringEngine（run_monitoring.py）
  - SQLite に監視ログを永続化（monitoring_db）
  - しきい値超過や滞留注文などでアラート発行・kill flag 生成

- 研究・因子計算
  - モメンタム、ボラティリティ、バリュー等のファクター算出（DuckDB を使用）
  - 将来リターン / IC（Information Coefficient）計算、統計サマリー

- ポートフォリオ構築
  - 候補選定、等ウェイト／スコア重み、リスクベースの株数算出、セクターキャップ適用

- AI（LLM）連携
  - ニュース記事を LLM（OpenAI）でセンチメント評価して ai_scores に保存（news_nlp）
  - マクロニュース＋ETF MA 乖離から市場レジームを判定（regime_detector）

- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU アフィニティ設定（utils.process_priority）
  - Paper Trading 検証レポート出力ツール（tools/paper_verification_report.py）

---

## 動作要件

- Python 3.10+
  - 型アノテーション（X | None）を使用しているため 3.10 以上を推奨
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のため任意）
- 標準ライブラリ
  - sqlite3, logging, threading, datetime, pathlib 等

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   ※ 実際の開発では `requirements.txt` や `pip install -e .` を利用してください。

4. .env を作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（既存 .env があれば読み込んで更新）

5. 設定検証（必須項目の確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリの確認
   - デフォルトで SQLite / DuckDB / PID / kill.flag などは `data/` 下を使用します。必要なら .env でパスを上書きしてください。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）

- データベース / パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- ロギング / プロセス
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログファイルディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH — Execution の PID ファイルパス（デフォルト: data/execution.pid）

- AI（OpenAI）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用）

- 監視系
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" でオン。production では推奨しない）

- その他
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）

注意: .env 自動読み込み機能はデフォルトで有効です（プロジェクトルートに .env / .env.local がある場合）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 実行方法（抜粋）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）

- Execution（エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコア / レジーム判定（スクリプトや REPL から）
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

---

## 停止・Kill Switch の仕組み

- 実行中の ExecutionEngine は `data/kill.flag` の存在を監視し、kill flag が書き込まれるとシャットダウンされます（KillSwitch により監視で条件が満たされると書き込まれる）。
- 外部から強制停止したい場合は `data/stop_requested.flag`（run_monitoring/run_execution の停止フラグ）や `data/kill.flag` を作成します。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動で kill.flag をクリアしますが、本番では推奨されません。

---

## ログ

- 共通ログ設定 util: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- デフォルト:
  - コンソール出力（stdout）
  - 日次ローテーションで logs/<app_name>.log に保存（30日分保持）
- ログ出力ディレクトリは LOG_DIR 環境変数または引数で変更可能。ディレクトリ作成に失敗するとファイル出力はスキップされ、コンソールのみになります。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイル・モジュールの概観（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード機能）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (※プロジェクトによって存在)
  - execution/                 — 発注エンジン関連（BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（上記以外にも data/, config/ 等の補助ファイル、ドキュメントが存在する場合があります）

---

## 開発上の注意 / 補足

- KABUSYS_ENV=live の設定は本番モードです。validate_config は本番向けの追加チェックと警告を行います。運用時は設定・権限を慎重に確認してください。
- Paper Trading モードは本番 DB と分離されるため、発注ロジックの検証に使えます（ただし挙動が本番と完全一致するとは限りません）。
- AI 関連は OpenAI API を利用します。API 料金やレート制限、エラー時のリトライ設計等に注意してください。
- DuckDB は大量の時系列データ処理に利用されます。prices_daily / raw_financials / raw_news 等のテーブル定義とデータ準備が必要です。
- テストでは環境変数の自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して isolation を保つと便利です。

---

以上がこのコードベースの README です。必要であれば以下を追加できます：
- より詳細な起動例（systemd / supervisor 用 unit サンプル）
- CI / テスト実行手順
- 各コンポーネントの API（関数の呼び出し方）サンプルコード

どの追加情報が必要か教えてください。