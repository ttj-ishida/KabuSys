# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README。  
このドキュメントはソースツリー（src/kabusys）に含まれる主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

> 注: 実装はモジュール単位で分かれており、本 README は開発者向けの運用手順・簡易リファレンスを意図しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。主な機能は次のとおりです。

- ExecutionEngine（発注エンジン）：ブローカークライアントを使った発注やリスク管理（本番 / ペーパートレード対応）
- Monitoring（監視）：システム状態・注文状態・リスク指標をポーリングして SQLite に記録、Kill Switch による自動停止
- Portfolio construction：銘柄選定、重み算出、ポジションサイズ計算（純粋関数群）
- Research：DuckDB を利用したファクター計算・特徴量解析ユーティリティ
- AI サービス：ニュース NLP（OpenAI）を使った銘柄センチメント、レジーム判定
- ツール：Paper Trading 検証レポート生成などの実行ファイル

設計上のポイント：
- 環境変数（.env）を利用した設定管理
- DuckDB（分析用） / SQLite（監視・発注ログ）を使用
- 本番とペーパートレードは DB 分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI を利用する処理は API キー必須でフェイルセーフ実装

---

## 機能一覧（抜粋）

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine 起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループ起動
- 設定・検証
  - python -m kabusys.config_setup : .env 作成ウィザード（対話式）
  - python -m kabusys.validate_config : 設定検証 CLI（--strict オプションあり）
- 監視関連
  - system_monitor: CPU/Mem/Disk、プロセス PID、データ鮮度チェック
  - trade_monitor: 注文の滞留・異常約定検出（実装参照）
  - risk_monitor: ドローダウン、ポジション上限監視
  - KillSwitch: リスクトリガー時に data/kill.flag を書き、Execution を停止
- ポートフォリオ
  - 銘柄候補選定、等重/スコア重み計算、ポジションサイズ算出、セクター制約、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、ファクター統計
- AI
  - news_nlp.score_news: raw_news を OpenAI で解析して ai_scores に書き込む
  - regime_detector.score_regime: MA200 とマクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB からレポート生成（PASS/FAIL 判定）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ例：
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がない場合は上記を個別にインストールしてください。実行時に不足エラーが出るパッケージを追加でインストールしてください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動ロード:
     - プロジェクトルート（.git か pyproject.toml がある場所）にある .env / .env.local が自動で読み込まれます
     - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. データディレクトリ（自動作成されるが権限に注意）
   - ログ：デフォルト logs/
   - DB：data/kabusys.duckdb（duckdb）、data/monitoring.db（sqlite）等
   - 実行時ファイル：data/execution.pid、data/stop_requested.flag、data/kill.flag

---

## 必須 / 主要な環境変数

必須（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意設定（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db など）を使用して本番 DB と分離
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- PAPER_FILL_MODE: ペーパートレードの注文約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

小ネタ:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。0 以下は無効でデフォルトにフォールバック。

---

## 使い方（主要コマンド）

- 環境作成（.env 対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を指定

- AI / レジーム判定・ニュース NLP
  - AI 関連はライブラリ関数として提供（例: kabusys.ai.score_news）
  - 実行には OPENAI_API_KEY が必要。CLI ラッパーは用意されていないため、スクリプトやジョブから呼び出してください。

ログ出力:
- ログはデフォルトで標準出力 + 日次ローテートファイル（logs/<app_name>.log）に出力されます。
- setup_logging(app_name="...") により統一設定されます。

停止手順:
- run_monitoring / run_execution は data/stop_requested.flag を監視しています。停止を促すには該当ファイルを作成してください（通常は運用ツールやシェルで作成）。
- KillSwitch（監視側）によりリスクトリガーで data/kill.flag を書き込むと Execution 側で停止判定に使われます。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。

権限注意:
- ログディレクトリや data ディレクトリの作成権限を確認してください。ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数自動読み込み、Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化・永続化層
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文監視（滞留／約定異常等）
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - monitoring_engine.py — 各 Monitor を統合するループ
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — （アラート送信ロジック）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - ExecutionEngine の主要実装（発注・リスク管理）
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数計算・制約処理
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計
- ai/
  - news_nlp.py — ニュースセンチメント API ラッパー（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — 共通ログ初期化
  - process_priority.py — プロセス優先度 / affinity 設定ユーティリティ
- data/ (運用時に生成される)
  - monitoring/DB ファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）
  - stop_requested.flag, kill.flag, execution.pid
- logs/（デフォルト、ログファイル格納）

（上記は主なファイル群の要約です。詳細はソースを参照してください）

---

## 運用上の注意・トラブルシューティング

- DB の親ディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることがあります。権限不足に注意。
- ログディレクトリの作成に失敗した場合、ファイルログは無効になりコンソールのみとなります。stderr に警告が出力されます。
- OpenAI API 呼び出しはネットワークエラーやレート制限に対してリトライ実装がありますが、API キーの管理は厳重に行ってください（.env を Git にコミットしない）。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を調整できます。1 未満や 0 は無効扱いでデフォルトに戻ります。
- Execution 起動時は stop_requested.flag / kill.flag の存在をチェックします。必要に応じて削除（clear）してください。
- process_priority.set_process_priority は OS に依存します。Windows/Linux/Mac に対応したフォールバックあり。psutil の権限エラーが発生する場合、警告が出て続行します。

---

## 開発者向けメモ

- DuckDB を利用した解析関数は接続オブジェクトを引数で受け取り、副作用を持たない設計です（テストが容易）。
- portfolio / research の多くの関数は純粋関数で DB を直接変更しないため単体テストがしやすい設計です。
- monitoring/monitoring_db.py は冪等なテーブル初期化とマイグレーションを含みます（ALTER TABLE を実行してカラム追加を行う）。
- 設計方針として「ルックアヘッドバイアス防止」のため、date.today() や datetime.today() を参照しない実装方針が守られています（関数引数で date を受け取る）。

---

もし README に追加してほしい情報（例: 具体的な ExecutionEngine の起動オプション、Broker の設定方法、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記・詳細化します。