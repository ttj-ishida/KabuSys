# KabuSys

日本株向け自動売買システムのパッケージ（README）。  
この README はリポジトリ内の主要モジュール群に基づき、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究パイプラインを想定した Python モジュール群です。  
主な目的は以下：

- 戦略のファクター計算・特徴量探索（DuckDB を利用）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数）
- 実行エンジン（ExecutionEngine）とその監視（Monitoring）
- Paper Trading 用検証・レポート生成
- ニュースを用いた LLM ベースのセンチメント評価（OpenAI）
- 環境設定ウィザードと起動前検証ツール

設計方針としては「テストしやすい純粋関数」「DB と実行ロジックの分離」「フェイルセーフな API リトライ、ログ出力」を重視しています。

---

## 主な機能（抜粋）

- 環境設定関連
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前設定検証ツール（kabusys.validate_config）
- 実行 / 監視
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、Paper 用 SQLite（data/paper_trading.db）へ記録
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - システム状態、注文ログ、リスクなどをポーリングして監視 DB に記録
    - stop_requested.flag により監視ループ停止
- モニタリング
  - SystemMonitor（CPU/MEM/DISK、データ鮮度、プロセス生存チェック）
  - TradeMonitor（滞留注文、約定異常などの検出）※実行管轄モジュールと連携
  - RiskMonitor（ドローダウン・ポジション上限監視、Kill Switch 発動）
  - MonitoringDB（SQLite に永続化する読み書きレイヤ）
  - MonitoringEngine（各モニタを束ねたポーリング実行）
- ポートフォリオ関連（純粋関数）
  - 候補選定、等重・スコア重み付け（portfolio_builder）
  - セクターキャップ適用、レジーム乗数（risk_adjustment）
  - 発注株数・アグリゲートキャップ処理（position_sizing）
- リサーチ
  - ファクター計算（momentum/value/volatility）: duckdb を用いた SQL 実装（research.factor_research）
  - 将来リターン、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
- AI（OpenAI）連携
  - ニュース NLP による銘柄センチメント（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA 乖離で市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しはリトライ・フォールバックを組み込み（429/5xx 等）
- ユーティリティ
  - ロギングセッティング（utils.logging_setup）
  - プロセス優先度/CPU affinity 設定（utils.process_priority）
  - Paper Trading の検証レポート生成ツール（tools.paper_verification_report）

---

## 前提・依存関係（推奨）

- Python 3.10 以上（型注釈の union 演算子 (|) を使用）
- 主な外部パッケージ（プロジェクト環境に合わせてインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証にのみ必要）
- （任意）仮想環境の作成例:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -U pip
  - pip install duckdb psutil openai pyyaml

プロジェクトに requirements.txt がある場合はそちらを利用してください（この README はコードの内容に基づく説明です）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

2. .env を作成する（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
     - ウィザードに沿って J-Quants / kabu ステーション / DB パス 等を入力してください
   - あるいは `.env` を手動で作成（.env.example を参照）

3. 設定を検証する（起動前チェック）
   - python -m kabusys.validate_config
   - オプション: --strict を付けると警告も失敗扱いになります

4. デフォルト DB / ログディレクトリ
   - SQLite 監視 DB: data/monitoring.db （環境変数 SQLITE_PATH で変更可）
   - Paper Trading SQLite: data/paper_trading.db （PAPER_TRADING_SQLITE_PATH）
   - DuckDB: data/kabusys.duckdb （DUCKDB_PATH）
   - ログ: logs/<app_name>.log（デフォルト、logs ディレクトリに出力）

5. 必要に応じて environment variables を設定
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OPENAI_API_KEY は ai モジュール（score_news/score_regime）利用時に必須
   - 主要な環境変数の例は下記「環境変数」セクションを参照

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABUSYS_ENV : 実行環境（development / paper_trading / live）, default=development
- DUCKDB_PATH : DuckDB ファイルパス（default=data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（default=data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（default=data/paper_trading.db）
- PAPER_FILL_MODE : ペーパートレードの約定挙動（instant/partial/never/reject）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR : ログ保存先ディレクトリ（default=logs）
- OPENAI_API_KEY : OpenAI API キー（ai モジュールで使用）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒。run_monitoring で上書き可）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START : 実行監視・Kill switch 関連

---

## 使い方（主要コマンド）

※ いずれもプロジェクトルート（pyproject.toml または .git があるディレクトリ）で実行してください。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper DB に記録します
    - 起動時に data/stop_requested.flag が存在すると起動を行いません
    - 実行中は data/execution.pid に PID が書かれます

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）
    - run_monitoring は常に本番 sqlite_path を使用して監視 DB を初期化します
    - data/stop_requested.flag を作成すると監視ループは安全に停止します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH も参照）

- ai モジュール（プログラム内 API）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

- ライブラリとして関数を使う（例）
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - 各関数は DuckDB 接続と target_date（datetime.date）を受けます

---

## 停止・Kill Switch の挙動

- 監視ループを停止する（手動）
  - data/stop_requested.flag を作成するか、存在させれば run_monitoring / run_execution の起動ループは検知して停止します

- ExecutionEngine に対して強制停止（Kill Switch）
  - KillSwitch は監視結果に基づき data/kill.flag を書き込みます（既に存在する場合は再書き込みしない）
  - Kill flag があると ExecutionEngine は発注処理を停止します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では 0 を推奨）

---

## ロギング

- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- 出力先:
  - 標準出力（stdout）
  - ローテートされるファイル: logs/<app_name>.log（デフォルト、日次ローテーション、30日保管）
- ログレベルは引数・環境変数 LOG_LEVEL で制御可能

---

## ディレクトリ構成（主なファイル・モジュール）

リポジトリ内 src/kabusys 以下の主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py              — 対話式 .env 作成ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite 監視 DB レイヤ
    - system_monitor.py          — システム監視
    - trade_monitor.py           — 注文監視（コードベースの他部分と連携）
    - risk_monitor.py            — リスク監視（ドローダウンなど）
    - kill_switch.py             — kill.flag 制御
    - monitoring_engine.py       — 各モニタ束ねるエンジン
    - alert_manager.py           — （アラート送信管理、LINE などへ通知）
  - portfolio/
    - portfolio_builder.py       — 候補選定、重み計算
    - risk_adjustment.py         — セクターキャップ、レジーム乗数
    - position_sizing.py         — 発注株数計算（lot 単位の丸め、aggregate cap）
  - research/
    - factor_research.py         — Momentum/Value/Volatility 計算（DuckDB）
    - feature_exploration.py     — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                — ニュースを LLM で評価して ai_scores に書込
    - regime_detector.py         — ETF + マクロニュースで市場レジーム判定
  - data/ （実行時に作成される想定）
    - monitoring.db (default)
    - paper_trading.db (paper 用)
    - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル
  - logs/ （ログ出力先）

（上記はリポジトリ内の代表的なファイル群の抜粋です）

---

## 開発者向けメモ / 実装上のポイント

- Settings は .env をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を設定してください。
- run_execution と run_monitoring は起動直後にプロセス優先度を High にセットしようとします（psutil に依存、権限不足なら警告）。
- monitoring_db.init_monitoring_db は冪等でテーブルを作成し、マイグレーション（カラム追加）も行います。
- AI 関連は OpenAI の JSON Mode を用いる想定で、レスポンスのバリデーションやリトライ戦略を実装しています。API キー未設定時は例外を投げます。
- Paper Trading のログ・検証は本番 DB と分離されるよう設計されています（settings.is_paper 判定で paper_sqlite_path を使用）。

---

## よくある操作・トラブルシューティング

- ログファイルが作成されない：
  - 権限や LOG_DIR のディレクトリ作成に失敗している可能性があります。logs ディレクトリの作成と書き込み権限を確認してください。
- .env が反映されない：
  - Settings はプロジェクトルートを .git / pyproject.toml から探索します。CWD を変えて実行すると .env を見つけられない場合があります。プロジェクトルートで実行してください。
- OpenAI 呼び出しでエラーが出る：
  - OPENAI_API_KEY が環境変数に設定されているか、渡した api_key が正しいか確認。ネットワークや料金上限にも注意。

---

必要なら、README にさらに「実行例」「.env のサンプル」「ユニットテストの実行方法」「CI 設定」などを追加します。どの部分を詳細化したいか教えてください。