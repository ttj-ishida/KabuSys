# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ＋起動スクリプト群）です。本 README はリポジトリ内の主要モジュール構成、セットアップ手順、起動方法、及びディレクトリ構成を日本語でまとめたものです。

## プロジェクト概要
KabuSys は次を目的としたモジュール群を含みます。
- 戦略（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（Broker クライアントを介した発注管理、リスク制御、調整）
- 監視（システム状況・注文状況・リスク監視、Kill Switch）
- 研究／ツール（ペーパートレード検証レポート生成等）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）

設計方針の要点：
- DB：分析用に DuckDB、監視／履歴用に SQLite（実運用と paper_trading は分離）
- 設定：.env ファイル（config_setup による対話式生成）＋ Settings クラス経由で取得
- ロギング：共通ユーティリティで統一（コンソール + 日次ローテートファイル）
- 外部 API：kabuステーション、J-Quants、OpenAI（ニュース NLP / レジーム判定）を利用可能

## 主な機能一覧
- ExecutionEngine（実行エンジン）
  - ブローカーアダプタ（実運用 / Mock の切り替え）
  - 注文管理、リスク管理、照合（reconciler）
  - Kill Switch（データベースやリスク条件に基づく停止フラグ）
- Monitoring（監視）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
  - TradeMonitor：注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限監視、risk_logs の書込
  - MonitoringEngine：上記を束ねてポーリング・アラート送信
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重み付け、ポジションサイズ決定、セクター制限、レジーム乗数
- Research（研究）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI（OpenAI を用いた機能）
  - news_nlp: ニュース記事から銘柄ごとのセンチメントを取得して ai_scores に保存
  - regime_detector: ETF（1321）の MA200 とマクロニュースから日次レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB から性能レポート生成
- 設定/運用支援
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前チェック（必須環境変数や config/*.yaml の存在など）

---

## 前提（推奨環境）
- Python 3.10+
- 必須ライブラリ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の内容検証を行う場合）
- （任意）仮想環境（venv / pyenv など）

requirements.txt がある場合はそれを使ってください。なければ例えば:
pip install duckdb psutil openai PyYAML

---

## 環境変数と設定ファイル
主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
- KABUSYS_ENV: execution モード。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading 時は MockBrokerClient を使用して data/paper_trading.db に記録
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB のパス)
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (ログ出力先ディレクトリ、デフォルト: logs/)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）。run_monitoring で使用。

.env の作成は対話式ウィザードを推奨（下記参照）。

---

## セットアップ手順
1. リポジトリをクローン
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の作成（対話式）
   - python -m kabusys.config_setup
   - 推奨: .env を作成したら次へ
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. データディレクトリ確認
   - デフォルトで data/ と logs/ を使用します。必要に応じて .env でパスを上書きしてください。

※ 注意: 実運用（KABUSYS_ENV=live）の際は API キーやパスワードを適切に管理し、.env を Git にコミットしないでください。

---

## 使い方（起動・停止・ツール）
基本的に各起動スクリプトはモジュールとして実行します。

- ExecutionEngine を起動（デフォルトは .env の KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 動作: プロセス優先度を high に設定 → DB 接続（paper_trading の場合は専用 DB）→ ExecutionEngine.start（別スレッド）で実行
  - 停止: data/stop_requested.flag を作成すると本プロセスは検知して停止します（または kill.flag により外部から停止命令を送れます）。
  - PID ファイル: data/execution.pid（Settings.pid_file_path がデフォルト）

- Monitoring を起動（常駐監視）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 動作: SystemMonitor/TradeMonitor/RiskMonitor を初期化し、ループで check を実施。stop_requested.flag を検出すると終了。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB は --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH、あるいはデフォルト data/paper_trading.db を参照

### 停止・Kill Switch
- Kill Switch（プロセス外から ExecutionEngine に停止させたい場合）
  - KillSwitch は data/kill.flag（Settings.kill_flag_path）ファイルを作成すると ExecutionEngine 側で検出して停止（およびアラート）します。
  - KillSwitch は複数条件（ドローダウン・ポジション超過など）で自動的に書き込まれることがあります。
- Graceful stop for run scripts
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知し終了します（プロセスの自主停止フラグ）。

---

## ログとデータベース
- ログ
  - デフォルト出力先: logs/
  - ログはコンソール（stdout）とファイル（TimedRotatingFileHandler 日次）に出力されます。
  - ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定できます。
- DB
  - DuckDB: 分析用（prices_daily, raw_financials, ai_scores, market_regime 等）
    - デフォルト: data/kabusys.duckdb（DUCKDB_PATH）
  - SQLite: 監視・トレードログ / ペーパートレードデータ
    - 監視 DB: data/monitoring.db（SQLITE_PATH）
    - ペーパートレード DB（paper_trading の場合）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

init_monitoring_db() により監視 DB のテーブル（system_status, trade_logs, positions, risk_logs, dashboard 等）は起動時に（冪等的に）作成されます。

---

## 開発者向けポイント
- Settings クラス（kabusys.config）を通じて環境変数を集約しています。KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると .env の自動読み込みを無効化します。
- logging_setup.setup_logging(app_name=...) で全プロセスのログ設定を統一しています。
- process_priority.set_process_priority("high") を起動時に呼んでいるため psutil による優先度変更で権限エラーが出る場合があります（警告ログのみで継続）。
- AI モジュール（news_nlp, regime_detector）は OpenAI クライアントを用います。API 呼び出しロジックはリトライやレスポンス検証を含み、失敗時はフェイルセーフ（無効値 or スキップ）する設計です。
- research モジュールは DuckDB 接続を受け取り SQL を利用して計算する pure 関数群です（副作用なし）。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity 設定ユーティリティ
  - execution/               — ExecutionEngine 周りの実装（broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート処理用、ログや外部通知連携）
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
  - data/                    — データファイル置き場（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）

---

## よくある質問 / トラブルシュート
- psutil やファイルアクセス権限で優先度設定が失敗する
  - アクセス権限不足で設定ができない場合は警告が出ますが処理は継続します。必要なら root / 管理者権限で起動してください。
- OpenAI API 呼び出しで 429 やタイムアウトが発生する
  - モジュール側でエクスポネンシャルバックオフを行います。長時間安定しない場合は API キーやネットワーク、レート制限を確認してください。
- .env を更新したのに反映されない
  - config.py は起動時に自動でプロジェクトルートの .env/.env.local を読み込みます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定している場合は無効化されています。

---

README はここまでです。必要であれば以下を追記できます：
- 各モジュール（execution、monitoring、ai）の詳細な API / クラス図
- 開発用のユニットテスト実行方法
- デプロイ / サービス化（systemd ユニット例、Dockerfile など）

追加で欲しい内容があれば教えてください。