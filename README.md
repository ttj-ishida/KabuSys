# KabuSys

日本株自動売買システムの軽量コア（ライブラリ & 起動スクリプト群）。  
本リポジトリには以下の主要コンポーネントが含まれます：

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視ループ（Monitoring）
- 環境設定ウィザード / 設定検証ツール
- ポートフォリオ構築・ポジションサイズ計算ロジック（純粋関数群）
- 研究用ファクター計算・特徴量解析モジュール
- LLM を用いたニュースセンチメント / レジーム検出モジュール
- ペーパートレード検証レポート生成ツール

以下はこのコードベースの README（日本語）です。セットアップ方法、使い方、ディレクトリ構成などをまとめています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動例 / コマンド一覧）
- 環境変数（代表的なもの）
- 監視・停止フラグの説明
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買を目的としたシステムのコアライブラリおよび起動スクリプト群です。
- 取引実行ロジック（ExecutionEngine）は本番 / ペーパートレードを切り替え可能で、監視コンポーネントが稼働状況やリスクをチェックし、必要に応じて Kill Switch（停止フラグ）を発動します。
- データ分析用に DuckDB を利用し、監視ログや発注ログは SQLite に永続化します。
- OpenAI（例: gpt-4o-mini）を使ったニュースの NLP スコアや、レジーム検出（市場状態判定）機能を備えています。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite に記録して本番 DB と完全分離。
  - プロセス優先度の調整、PID ファイル管理、停止フラグ監視を行う。
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして監視ログを SQLite に保存。
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を参照してログを保存する（監視用 DB は分離しない設計）。
- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の対話式作成/更新を支援。
- 設定検証ツール（python -m kabusys.validate_config）
  - .env や config/*.yaml の存在・基本整合性を事前検証。
- ツール
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
    - 稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を行う。
- 研究用モジュール（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み付け（等配分 / スコア加重）、セクターキャップ、ポジションサイズ計算（lot 単位で丸め、aggregate cap のスケーリング）
- AI モジュール（kabusys.ai）
  - ニュースのセンチメントスコアリング（OpenAI）
  - レジーム判定（MA 乖離 + マクロニュースセンチメントの合成）
- 共通ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順（開発環境想定）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt がある場合はそれを使ってください（本公開コードでは省略）。
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - その他：KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, OPENAI_API_KEY（AI 機能を使う場合）など

5. データディレクトリ作成（必要に応じて）
   - デフォルトで使用されるディレクトリ: data/, logs/
   - 例:
     - mkdir -p data logs

6. （オプション）Kill Flag の初期化
   - KILL_FLAG_CLEAR_ON_START 設定が 1 の場合は起動時に kill.flag を自動クリアする挙動があります（本番では 0 を推奨）。

使い方（主要コマンド）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（デフォルト data/paper_trading.db）を使用し MockBroker 客を利用
    - 実行中、pid ファイル（data/execution.pid）を書き出す
    - data/stop_requested.flag が存在すると終了する

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は（設計上）環境にかかわらず本番 sqlite_path（SQLITE_PATH 環境変数）を使って監視ログを記録します
  - data/stop_requested.flag が存在すると監視ループを終了する

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（省略時は環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）

代表的な環境変数（主要項目）
- KABUSYS_ENV
  - 有効値: development / paper_trading / live
  - デフォルト: development

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用リフレッシュトークン（必須）

- KABU_API_PASSWORD
  - kabuステーション API パスワード（必須）

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視 DB（monitoring）用 SQLite ファイルパス（デフォルト: data/monitoring.db）
  - 監視は常にこの DB を使用（paper_trading でも同一）

- PAPER_TRADING_SQLITE_PATH
  - ペーパートレード専用の SQLite（ExecutionEngine が KABUSYS_ENV=paper_trading のときに使用）
  - デフォルト: data/paper_trading.db

- PAPER_FILL_MODE
  - ペーパートレード時の約定モード（instant / partial / never / reject）
  - デフォルト: instant

- OPENAI_API_KEY
  - OpenAI API キー（ニュース NLP / レジーム検出が必要な場合）

- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒）。デフォルト 60。

- LOG_LEVEL / LOG_DIR
  - ログレベル、ログ出力ディレクトリ（logs/<app_name>.log に日次ローテーションで出力）

監視・停止フラグ（ファイルベース）
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py の外部停止フラグ（存在すると起動ループが終了する）
  - 運用ではこれを作成してプロセスに停止を指示できます

- data/kill.flag
  - KillSwitch（監視コンポーネント）が条件に応じて生成する停止フラグ。ExecutionEngine 停止のトリガーとなる
  - KILL_FLAG_CLEAR_ON_START 環境変数で起動時に自動クリアするか制御可能（本番では 0 を推奨）

- data/execution.pid
  - 実行エンジンの PID を書き出すファイル（run_execution.py が使用）

ログ
- ロギングは共通ユーティリティで設定されます（kabusys.utils.logging_setup）。
- コンソール（stdout）とファイル（logs/<app_name>.log）に出力。ファイルは日次ローテーションで 30 日保持。

注意点 / 運用上のヒント
- .env は絶対に Git にコミットしないでください（config_setup.py でも注意喚起あり）。
- KABUSYS_ENV=live の場合は本番設定となるため、LINE 通知設定や KILL_FLAG_CLEAR_ON_START は特に慎重に確認してください。
- OpenAI を使う機能は API コスト・レイテンシ・利用規約に注意して運用してください。API エラー時はフェイルセーフで無効値やスキップで継続する設計です（例: macro_sentiment=0.0）。
- 監視は本番 sqlite_path を使うため、監視 DB を別途分離したい場合は環境変数でパスを変更してください。

ディレクトリ構成（主なファイル）
- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring 起動スクリプト
    - config.py                      — 環境変数 / Settings 管理（自動 .env ロード含む）
    - config_setup.py                — .env を対話式に作成するウィザード
    - validate_config.py             — 設定検証 CLI
    - utils/
      - __init__.py
      - logging_setup.py             — ログ設定ユーティリティ
      - process_priority.py          — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層（schema + MonitoringDB クラス）
      - system_monitor.py            — システム監視（CPU/mem/disk/データ鮮度）
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - trade_monitor.py             — （参照: TradeMonitor 実装、コードベースに含まれる想定）
      - monitoring_engine.py         — 各 Monitor を束ねる実行ループ
      - kill_switch.py               — kill.flag 書き込みユーティリティ
      - alert_manager.py             — （参照: 通知管理、実装ありの想定）
    - execution/
      - (ExecutionEngine, OrderManager, BrokerClientFactory, Reconciler, RiskManager など)
      - （本 README で参照するが、実装はリポジトリ内の別ファイル群に格納）
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 株数決定・スケーリング・単元丸め
      - risk_adjustment.py           — セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py           — モメンタム/バリュー/ボラティリティ等
      - feature_exploration.py       — 将来リターン / IC / 統計要約
      - __init__.py
    - ai/
      - news_nlp.py                  — ニュースセンチメントスコアリング（OpenAI）
      - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
      - __init__.py
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
      - __init__.py

（注）上記は主要ファイル群の抜粋です。細かな実装ファイルはリポジトリ内の各モジュールを参照してください。

ライセンス / 貢献
- 本リポジトリのライセンス情報（LICENSE）がある場合はそちらに従ってください。  
- バグ報告や機能提案は Issue を通じてお願いします。

---

簡単な起動例（ローカル開発）
1. .env をウィザードで作る
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config

3. 監視起動（別ターミナル）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

4. 実行エンジン起動（別プロセス）
   - python -m kabusys.run_execution

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

ご不明点や追加で README に入れたい項目（例: 具体的な設定例、requirements.txt、デプロイ / systemd ユニット例など）があれば教えてください。必要に応じて README を拡張します。