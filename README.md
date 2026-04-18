# KabuSys

日本株自動売買システム（KabuSys）。  
ポートフォリオ構築、シグナル生成・発注エンジン、監視・アラート、リサーチ／ファクター計算、および OpenAI を使ったニュース NLP / レジーム判定を含むモジュール群で構成されています。

バージョン: 0.1.0

## 概要
このリポジトリは自動売買システムのコアライブラリと起動スクリプトを含みます。主な用途は以下のとおりです。

- 発注エンジン（ExecutionEngine）：kabuステーション（またはペーパートレードのモック）と連携して注文を実行・管理
- 監視（Monitoring）：プロセス／システム状態・注文状況・リスクを定期的にチェックし、必要なら Kill Switch を作動
- ポートフォリオ構築：候補選定、重み付け、株数算出、セクター制限、レジーム乗数など
- リサーチ：DuckDB 上の価格・財務データを使ったファクター計算・特徴量解析
- AI モジュール：ニュースのセンチメントスコア化（OpenAI）、市場レジーム判定
- ユーティリティ／ツール：設定ウィザード、設定検証、紙上検証レポート等

設計方針の一部（ソースコードより）：
- DB（DuckDB / SQLite）を用いた分析・ログ保存
- 環境依存値は .env または環境変数で管理
- 本番とペーパートレードは SQLite を分離
- OpenAI 呼び出しは堅牢にリトライ・バリデーションを実装

## 主な機能一覧
- Execution:
  - 実際の broker クライアントまたは MockBrokerClient（KABUSYS_ENV=paper_trading）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
  - 発注ログの永続化（SQLite）
- Monitoring:
  - system_status/trade_logs/positions/risk_logs/dashboard の永続化
  - SystemMonitor: CPU/Mem/Disk、データ鮮度、Execution プロセス監視
  - TradeMonitor: 滞留注文・約定異常などの検出
  - RiskMonitor: ドローダウン、ポジション数監視・Kill Switch 発動
  - MonitoringEngine：定期ポーリングとアラート発行
- Portfolio:
  - 候補選定、等重・スコア重み付け、リスクベースの株数算出
  - セクター上限適用、レジーム乗数
- Research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（情報比）・統計サマリー
- AI:
  - news_nlp: raw_news を集約して OpenAI でセンチメントを算出し ai_scores に書き込み
  - regime_detector: ETF（1321）のMAとマクロニュースを統合して市場レジーム判定
- ツール:
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

## セットアップ手順（概略）
前提: Python 3.9+ を想定。仮想環境を推奨。

1. リポジトリをクローンしてワークディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config による YAML 検証を行う場合）
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
   （requirements.txt がある場合はそちらを使用）

4. .env の作成
   - ウィザードで対話的に生成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI モジュールを使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告を fail としたい場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ等の作成（必要に応じて）
   - ログディレクトリはデフォルトで `logs/`、DB は `data/` 配下が想定されています。`setup_logging` が自動作成しますが、書き込み権限を確認してください。

## 使い方（起動・実行）
エントリポイントとなる起動スクリプトが複数あります。

- ExecutionEngine（発注エンジン）起動
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、`data/paper_trading.db` に書き込みます（本番 DB と分離）。
  ```bash
  # 例: 開発/実行
  python -m kabusys.run_execution
  ```
  - 停止: モニタ側や手動で `data/stop_requested.flag` を作成するとバックグラウンドスレッドを終了します。停止要求に対応する PID ファイルは `data/execution.pid`。

- Monitoring（監視ループ）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を環境にかかわらず使用（監視ログは共通の monitoring DB に記録されます）。
  - 停止フラグファイル `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `PAPER_TRADING_SQLITE_PATH` 環境変数か `data/paper_trading.db`

- 設定ウィザード／検証（再掲）
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

## 主要な環境変数（まとめ）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存先（デフォルト: logs）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — プロセス制御・Kill Switch 関連

## ロギング
- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を起動スクリプトから呼び出すことで、stdout と日次ローテート（logs/<app_name>.log）へのログ出力が行われます。
- デフォルトで 30 日分保管（TimedRotatingFileHandler backupCount=30）。

## データベース / マイグレーション
- `monitoring_db.init_monitoring_db(conn)` が起動時に呼ばれ、必要なテーブルを冪等的に作成します（system_status, trade_logs, positions, risk_logs, dashboard）。
- マイグレーションロジック（列の追加など）も含まれており、既存 DB に対して安全に列追加を試みます。

## ディレクトリ構成（抜粋）
以下は主要ファイル / モジュールのツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み / Settings クラス
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py           — ロギング設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - execution/                    — 発注関連（Engine、OrderManager 等）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（監視ログ）
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
  - data/                         — データ / pipeline モジュール（DuckDB 関連）
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI）
    - regime_detector.py         — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - logs/                         — デフォルトのログ出力先（実行時作成）
  - data/                         — デフォルトの DB / flag ファイル（実行時作成）
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid

（実際のツリーはリポジトリ参照）

## 注意点 / トラブルシューティング
- .env は絶対に Git にコミットしないでください。config_setup はその旨を注意喚起します。
- OpenAI を利用する機能は API キーが必須です。API のレート制限や一時エラーに対してはリトライ実装がありますが、API キーの設定漏れは ValueError を発生させます。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能。0 や負値は無効扱いされ、デフォルト 60 秒にフォールバックします。
- ペーパートレードモード（KABUSYS_ENV=paper_trading）は発注処理を本番 DB と分離します。運用時は KABUSYS_ENV=live の設定に注意してください（validate_config が警告を出します）。
- Kill Switch（data/kill.flag）は安全上重要です。KILL_FLAG_CLEAR_ON_START を `1` に設定すると起動時に自動クリアされますが、本番では `0` を推奨します。
- ファイル書き込み権限やディレクトリ作成に失敗するとログファイル出力が無効化され、コンソールのみで出力されます。権限を確認してください。

## 開発者向けメモ
- 多くのモジュールは純粋関数（副作用なし）設計を心がけているため単体テストが書きやすくなっています（例えば portfolio の各関数や research の関数群）。
- DuckDB 接続を受け取る設計のため、テスト時は in-memory / テスト用 DuckDB ファイルを用意してテスト可能です。
- OpenAI API 呼び出し箇所はラッパー関数（_call_openai_api）を用意してあり、テストでのパッチ差し替えを想定しています。

---

README は以上です。さらに具体的な使い方（ExecutionEngine の設定項目、OrderManager の API、各 config/*.yaml のフォーマットなど）が必要であれば、追って詳細なドキュメントを作成します。どの部分の詳細を優先しますか？