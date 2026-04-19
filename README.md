# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買システム「KabuSys」の内部モジュール群です。戦略の研究、ポートフォリオ構築、注文実行（実取引/ペーパートレード）、監視、AI を使ったニュース解析などを含む設計になっています。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成のまとめです。

---

## プロジェクト概要

KabuSys は次の主要機能を分離して実装した自動売買フレームワークです：

- 戦略・ファクター計算（DuckDB を用いた価格データ処理）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限）
- 注文実行エンジン（本番/ペーパートレードを分離）
- 監視（システム状態・注文状態・リスク監視・Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント・レジーム判定）
- 開発・運用支援ツール（環境セットアップウィザード、設定検証、検証レポート生成）

設計上のポイント：

- 環境変数 / .env による設定管理（`kabusys.config`）
- DuckDB（分析）と SQLite（監視/履歴）の併用
- フェイルセーフ設計（API失敗やデータ不足時も稼働継続）
- モジュールはユニット的に分離され、テストしやすい純粋関数が多い

---

## 主な機能一覧

- 環境設定ウィザード: `kabusys.config_setup`（.env を対話的に作成/更新）
- 設定検証 CLI: `kabusys.validate_config`（起動前のチェック）
- 実行エンジン起動: `kabusys.run_execution`（本番 / paper_trading の分岐）
- 監視ループ起動: `kabusys.run_monitoring`（CPU/メモリ/ディスクやデータ鮮度、プロセス状態を監視）
- 監視 DB 層: `kabusys.monitoring.monitoring_db`（SQLite）
- リスク監視: `kabusys.monitoring.risk_monitor`
- Kill Switch: `kabusys.monitoring.kill_switch`（停止フラグ書き込み）
- Monitoring Engine: `kabusys.monitoring.monitoring_engine`（各モニタの統合）
- ポートフォリオ構築: `kabusys.portfolio.*`（候補選定、重み計算、ポジションサイズ）
- 研究用モジュール: `kabusys.research.*`（ファクター、特徴量探索）
- AI モジュール: `kabusys.ai.*`（ニュース分析・レジーム判定。OpenAI を使用）
- ツール: `kabusys.tools.paper_verification_report`（ペーパートレードの検証レポート生成）

---

## セットアップ手順 (開発環境向け)

1. Python の推奨バージョンを用意する（例: 3.10〜3.11 推奨）。
2. 仮想環境を作成・有効化：
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML
   - 実際にはプロジェクトの要件に応じて追加パッケージが必要になる場合があります（例: requests 等）。
4. 環境変数の設定:
   - 開発中はリポジトリルートに `.env` を作成するか、`kabusys.config_setup` を使って対話的に作成してください（必須の変数などは下記参照）。
   - 自動ロード: `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（起動前に設定すること）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

主要な任意/上書き可能な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用。デフォルト 60）

推奨: 実行前に `python -m kabusys.validate_config` を実行して設定に問題がないか確認してください。

---

## 使い方（主要スクリプト）

プロジェクトルートで以下のように実行します（python がパッケージを見つけられるようにカレントディレクトリはリポジトリルートにすること）。

1. .env を生成（対話式）
   - python -m kabusys.config_setup
   - 対話に従って .env を作成してください。

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

3. 監視ループの起動
   - python -m kabusys.run_monitoring
   - オプション: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔秒を上書き可能（例: MONITOR_POLL_INTERVAL=30）
   - 注意: 監視は常に production の sqlite_path（SQLITE_PATH）を使用します（環境に関係なく監視 DB は本番 DB に書き込まれます）。

4. 実行エンジンの起動（注文処理）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全に分離されます）。
   - 実行中に `data/stop_requested.flag` が存在するとエンジンは停止します。停止用のフラグファイルパスは実行スクリプト内で参照されます。

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - DB パス指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数 または `data/paper_trading.db`

6. AI 機能（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。プログラム内の関数から呼び出します。
   - 例: kabusys.ai.score_news（DuckDB 接続と target_date を渡して利用）
   - AI モジュールは失敗時に安全側のフォールバックを行う設計です（例: API失敗時は無視または中立値で継続）。

ログ:
- デフォルトでは `logs/` にアプリ名毎のログ（例: logs/execution.log, logs/monitoring.log）を日次ローテートで出力します。ログの設定は `kabusys.utils.logging_setup.setup_logging` で制御できます。

停止 / Kill:
- `kabusys.monitoring.kill_switch` は `data/kill.flag` を書き込むことで ExecutionEngine 停止のトリガーとして機能します。Kill flag をクリアしたい場合は手動でファイルを削除するか、KillSwitch の clear() を使用します。

---

## よく使うファイル / エントリポイント一覧

- python -m kabusys.config_setup            # .env 対話ウィザード
- python -m kabusys.validate_config         # 設定検証
- python -m kabusys.run_monitoring          # 監視ループ
- python -m kabusys.run_execution           # 実行エンジン（発注）
- python -m kabusys.tools.paper_verification_report  # ペーパートレード検証レポート

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・自動 .env ロード
    - config_setup.py               # .env 対話式ウィザード
    - validate_config.py            # 設定検証ツール
    - run_monitoring.py             # Monitoring ポーリングループ起動スクリプト
    - run_execution.py              # ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py            # ログ設定ユーティリティ
      - process_priority.py         # プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py            # SQLite の監視 DB 層
      - system_monitor.py
      - trade_monitor.py            # （trade 監視実装）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py            # アラート送信実装（LINE 等）
    - execution/                     # 注文実行関連（Engine, BrokerFactory, OrderManager, RiskManager など）
    - portfolio/                     # ポートフォリオ構築（builder, position_sizing, risk_adjustment）
    - research/                      # ファクター計算・特徴量探索
    - ai/
      - news_nlp.py                  # ニュース NLP（OpenAI）
      - regime_detector.py           # レジーム判定（OpenAI + MA200）
    - data/                           # データパイプライン（DuckDB 用テーブル操作等）
    - tools/
      - paper_verification_report.py

その他:
- data/                          # 実行時に利用する DB / フラグファイル等（デフォルト）
  - monitoring.db  (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid

---

## 運用上の注意・補足

- 監視は常に `SQLITE_PATH`（本番監視 DB）を使用する設計になっているため、運用環境では DB パスの設定に注意してください。
- ペーパートレードは `KABUSYS_ENV=paper_trading` を設定すると本番 DB と分離して `PAPER_TRADING_SQLITE_PATH` に記録されます。
- OpenAI を使う機能は API コストと利用規約に注意して運用してください。API キーは .env や環境変数で管理してください。
- ログディレクトリ作成や高権限操作（プロセス優先度変更）では権限不足により一部機能がスキップされる可能性があります。ログやプロセス設定の失敗は警告出力されます。
- `.env` は絶対にリポジトリにコミットしないでください（`config_setup.py` の生成コメントにも記載あり）。

---

README は以上です。実行や運用に関して具体的な設定例や追加の手順（Broker クライアント実装、データ投入手順、DuckDB のスキーマ作成など）が必要であれば、その目的に合わせたドキュメントを追って作成できます。必要な出力例や .env のサンプルも作成可能です。どちらを希望しますか？