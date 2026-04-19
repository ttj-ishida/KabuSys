# KabuSys

日本株向け自動売買システムのコードベース（ドキュメント化された主要コンポーネント群）。  
この README はソースコード（src/kabusys 以下）を基に、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

※ 本リポジトリは実運用を想定した構成になっており、環境変数や秘密情報（APIキー等）を .env に格納して利用します。`.env` を絶対にリポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。主要な役割は以下です。

- ExecutionEngine：発注・リスク管理・注文管理を行う実行エンジン
- Monitoring：システム稼働状況・注文状態・リスク（ドローダウン／ポジション上限等）を定期監視し、必要に応じて Kill Switch を発動
- Research：DuckDB 上の市場データからファクター（モメンタム、ボラティリティ、バリュー等）や統計情報を算出
- Portfolio：候補選定・重み付け・ポジションサイズ計算・セクター制限などのポートフォリオ構築ロジック
- AI（OpenAI 統合）：ニュースを LLM でスコアリング（ニュース NLP）／マクロセンチメントを用いた市場レジーム判定
- ユーティリティ：ロギング設定、プロセス優先度設定、設定ウィザード、構成検証、DB 初期化等

設計方針として、運用安全性（本番・ペーパートレード分離、Kill Switch、フェイルセーフ）やルックアヘッドバイアス回避（date.now を直接参照しない等）に注意して実装されています。

---

## 機能一覧（主要）

- 環境設定関連
  - 対話式 .env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config [--strict]

- 実行／監視
  - Execution エンジン起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db）に記録
  - Monitoring 起動: python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視 DB 初期化（SQLite）を行い、System / Trade / Risk の各監視をポーリング
    - kill.flag による Execution 停止（KillSwitch）

- ポートフォリオ構築
  - 候補選定（スコア・ランキング）
  - 等金額／スコア加重配分
  - リスクベースのポジションサイズ計算（lot 単位丸め、aggregate cap、利用可能現金スケール）
  - セクターキャップ適用、レジーム乗数計算

- リサーチ／分析
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB ベース）
  - 前方リターン・IC（スピアマン）・ファクター統計サマリー
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

- AI（OpenAI）
  - ニュース記事から銘柄別センチメントを得て ai_scores に書き込む（kabusys.ai.score_news）
  - マクロ記事 + ETF MA200 乖離を用いて market_regime を判定・書き込み（kabusys.ai.regime_detector.score_regime）
  - API 呼び出しは retry/backoff 対応・部分失敗に対するフェイルセーフを備える

- ユーティリティ
  - 統一ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - MonitoringDB：SQLite を使った監視ログの永続化層（初期化・マイグレーション含む）

---

## 動作要件（依存）

主な Python パッケージ（使用部分のみ。環境により追加が必要）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（validate_config で YAML 内容検証を行う場合）
- sqlite3（標準ライブラリ）
- その他標準ライブラリ（logging, threading 等）

推奨インストール例:
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil
   - （AI 機能を使う場合）pip install openai
   - （validate_config の YAML チェックを有効にする場合）pip install PyYAML

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他: KABUSYS_ENV（development|paper_trading|live）、DUCKDB_PATH、SQLITE_PATH、OPENAI_API_KEY（AI 利用時）など

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict

6. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）は起動スクリプトが初回に init します（init_monitoring_db）。
   - DuckDB（デフォルト: data/kabusys.duckdb）は research / ai コンポーネントが参照します。必要に応じてデータを投入してください。

---

## 使い方（主要コマンド / モジュール）

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - 対話式に .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（注文実行）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、MockBroker を利用します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中、停止させるには data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）を利用して停止を促します。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
    - Monitoring は Settings.env にかかわらず本番 sqlite_path を使用して監視ログを記録します（監視 DB は常に共通で運用）。
    - 起動中に data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI（ニューススコア／レジーム判定） — ライブラリ API
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースをスコアリングし ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込み
  - これらは OpenAI API キー（OPENAI_API_KEY 環境変数または api_key 引数）を必要とします。

- ロギング
  - setup_logging(app_name="execution") を各起動スクリプトが呼び出します。
  - 標準出力（stdout）とファイル（logs/<app_name>.log、日次ローテート）に出力されます。
  - ログレベルは LOG_LEVEL 環境変数で変更可能（デフォルト INFO）。
  - ログディレクトリは LOG_DIR 環境変数で変更可能（デフォルト logs/）。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げようとします（プラットフォームに依存、失敗は警告でスキップ）。

- Kill Switch / 停止フラグ
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込むことで ExecutionEngine の停止を誘導します。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアする挙動になります（本番では 0 推奨）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 重要:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR（ログレベル）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- LOG_DIR: ログ出力先ディレクトリ
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1）

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## 実行例

- .env を作成
  - python -m kabusys.config_setup

- 設定をチェック
  - python -m kabusys.validate_config

- 監視を起動（デフォルト 60s）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート（2026-04-01〜2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 注意事項 / 運用上のヒント

- Production（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config は live 時に注意喚起を出します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。通常は 0 を推奨します。
- Monitoring の DB（SQLITE_PATH）は監視データを保持するため共通化されており、本番・ペーパートレードで分離されていない点に注意してください（run_monitoring は常に sqlite_path を使用）。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用して本番 DB と分離します。
- OpenAI API の呼び出しはレート制限・一時的なエラー時にバックオフしてリトライしますが、API コスト・呼び出し回数に注意してください。

---

## ディレクトリ構成（src/kabusys 内の主要ファイル）

- __init__.py
  - パッケージ定義、バージョン

- run_monitoring.py
  - SystemMonitor ポーリングループの起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）

- config.py
  - Settings クラス：環境変数・.env の自動読み込み / 値取得・検証

- config_setup.py
  - 対話式 .env 生成ウィザード

- validate_config.py
  - 起動前設定検証 CLI（必須環境変数チェック、ファイル存在チェック等）

- utils/
  - logging_setup.py：統一ロギング設定（stdout + 日次ローテート）
  - process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py：監視用 SQLite テーブル作成・読み書きラッパー（MonitoringDB）
  - system_monitor.py：システム状態・データ鮮度監視
  - trade_monitor.py：発注ログ・滞留注文・約定異常チェック（ファイル内に実装）
  - risk_monitor.py：ドローダウン・ポジション上限監視
  - kill_switch.py：kill.flag 書き込みロジック
  - monitoring_engine.py：各 Monitor を束ねるエンジン
  - alert_manager.py：アラート送信（LINE 等） — 実装参照

- execution/
  - execution_engine.py：ExecutionEngine（注文実行ループ）
  - broker_factory.py：ブローカークライアント生成（Mock or real）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など（発注・管理・リスク関連）

- portfolio/
  - portfolio_builder.py：候補選定・重み付け
  - position_sizing.py：株数計算・スケーリング・lot丸め
  - risk_adjustment.py：セクター制限・レジーム乗数

- research/
  - factor_research.py：モメンタム・ボラ・バリュー等ファクター計算（DuckDB ベース）
  - feature_exploration.py：前方リターン・IC・統計サマリー等

- ai/
  - news_nlp.py：ニュースを LLM（OpenAI）で銘柄別にスコアリングし ai_scores に書き込む
  - regime_detector.py：ETF MA200 乖離 + マクロニュースによる市場レジーム判定

- tools/
  - paper_verification_report.py：ペーパートレードの検証レポート生成（期間指定可）

- data/ （実行時に使用）
  - *.db（SQLite / DuckDB）、kill.flag、execution.pid、stop_requested.flag などを配置

---

以上がこのコードベースの概観と使い方です。README に書かれていない内部実装の詳細や API 仕様は各モジュール（src/kabusys 以下）の docstring・コメントを参照してください。運用前には必ず python -m kabusys.validate_config で設定チェックを行い、安全に配慮した上で起動してください。