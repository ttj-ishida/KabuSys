# KabuSys

日本株自動売買システムの一部（ライブラリ・起動スクリプト・ユーティリティ群）です。  
このリポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、および AI を使ったニューススコアリング等の機能を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境設定・使い方（起動例）
- よく使う環境変数
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買システムのコアロジック群（ポートフォリオ構築、ポジションサイズ計算、リスク調整、ファクター計算、AI ニューススコアリングなど）と
  実行エンジン／監視系の起動スクリプトおよび運用用ユーティリティを提供します。
- 本リポジトリはライブラリ群（pure functions や DB 書き込みユーティリティ）と、CLI / 起動用モジュールを含みます。

主な機能一覧
- Execution エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - PID管理、停止フラグ検知（data/stop_requested.flag, data/execution.pid）
- Monitoring（監視）起動スクリプト（run_monitoring）
  - システム（CPU/メモリ/Disk）・データ鮮度・Execution プロセス監視
  - RiskMonitor（ドローダウン・ポジション上限監視）および KillSwitch 連携
  - 監視結果は SQLite（monitoring.db）へ永続化
  - ポーリング間隔は環境変数で変更可能（MONITOR_POLL_INTERVAL）
- Monitoring DB ラッパー（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元丸め、aggregate cap 等）
  - セクターキャップ、レジーム乗数
- Research（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリ
  - DuckDB を用いた分析処理
- AI（ai）
  - ニュースを LLM（OpenAI）で解析して銘柄毎スコアを ai_scores に保存（news_nlp）
  - 市場レジーム判定（regime_detector）：ETF MA とマクロニュースセンチメントの合成
- ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

---

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.9+ を推奨（各環境に依存するため適切なバージョンを使用してください）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ このリポジトリに requirements.txt が無い場合、最低限次を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML （config ファイルチェックを有効化するため任意で推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. プロジェクトルートの確認
   - スクリプトはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. .env の作成
   - 対話式ウィザードで作成できます:
     - python -m kabusys.config_setup
   - 作成後、設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

6. データディレクトリ
   - デフォルトで下記ファイルを使用します（必要に応じて .env で変更してください）:
     - data/monitoring.db (SQLite monitoring DB)
     - data/paper_trading.db (Paper trading 用 DB)
     - data/kabusys.duckdb (DuckDB)
     - logs/ (ログ出力ディレクトリ)
   - ログは logs/<app_name>.log に日次ローテーションで保存されます

注意:
- OpenAI を利用する機能（ai.news_nlp, ai.regime_detector）は OPENAI_API_KEY 環境変数が必要です。
- Paper Trading は本番 DB と分離され、KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用します。

---

環境変数（よく使うもの / デフォルト）
- 必須（主に .env に設定）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - is_paper 判定により run_execution は paper DB を使用
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- ロギング
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring ポーリング間隔（秒、デフォルト: 60）
- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- その他
  - PAPER_FILL_MODE — Paper Trading 時の fill モード (instant | partial | never | reject)

---

使い方（起動例）
- 実行スクリプトはモジュールとして起動することを想定しています（プロジェクトルートで実行）。

1) 監視ループの起動
- 環境変数例:
  - export KABUSYS_ENV=development
  - export MONITOR_POLL_INTERVAL=60
- 起動:
  - python -m kabusys.run_monitoring
- 動作:
  - data/monitoring.db に system_status 等を書き込み
  - stop フラグファイル data/stop_requested.flag が存在するとループを停止します

2) Execution エンジン起動（実行）
- 環境変数例（ペーパートレード）:
  - export KABUSYS_ENV=paper_trading
- 起動:
  - python -m kabusys.run_execution
- 動作:
  - paper_trading 環境では mock ブローカーを使用し data/paper_trading.db に記録（本番 DB と分離）
  - data/execution.pid へ PID を書き、data/stop_requested.flag による停止を監視
  - Stop フラグが既にある場合は起動せず終了

3) 設定ウィザード / 検証
- ウィザード:
  - python -m kabusys.config_setup
- 検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

4) Paper Trading 検証レポート生成
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

5) AI モジュール（ニュース NLP / レジーム判定）
- 必要:
  - export OPENAI_API_KEY=sk-...
- API 呼び出しは内部で gpt-4o-mini を使用（JSON Mode を利用）
- 実行例（任意のスクリプトから呼ぶ）:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime

注意点（運用上）
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine に停止シグナルを送る仕組みがあります（KillSwitch）。
- MONITOR は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計です（監視は常に本番 DB を参照する意図）。
- run_execution は paper_trading 環境時に専用の paper_sqlite_path を使用し本番 DB を汚さないようになっています。
- ロギング: setup_logging が root ロガーを設定します。logs/<app_name>.log に日次ローテーションで保存されます。
- process priority: 起動時に utils.process_priority.set_process_priority("high") を呼びます。root 権限や OS によっては設定できない場合があります（警告でスキップ）。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下。抜粋）
- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（ETF MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite テーブル定義・永続化ユーティリティ
    - system_monitor.py        — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py         — （存在）取引ログ監視ロジック（モジュール参照）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込み・判定
    - monitoring_engine.py     — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py         — （存在）アラート送信管理（LINE など）
  - execution/
    - execution_engine.py      — 実行エンジン（EngineConfig 等）
    - broker_factory.py        — BrokerClientFactory（本番 / mock の生成）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数決定・スケールダウン・単元調整
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py       — momentum/volatility/value の計算
    - feature_exploration.py   — 将来リターン / IC / summary
    - __init__.py
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - data/                      — 実行時に使用する各種ファイル（DB / flag / pid 等。デフォルトパス）
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite, paper)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag
- logs/                        — ログ出力先（デフォルト）

（上記は主要なファイル・モジュールの一覧です。細かい実装ファイルはソースツリーを参照してください）

---

開発上の注意 / 推奨
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup でも警告あり）。
- 本番環境（KABUSYS_ENV=live）では必須設定・LINE 通知等を慎重にチェックしてください（validate_config に live 向けガードあり）。
- OpenAI を利用する機能には API レート・料金の考慮が必要です。テスト環境ではモック化して動作確認してください（score_news 内の _call_openai_api はパッチ可能）。
- DB スキーマ変更は monitoring_db.init_monitoring_db で互換性を保つようマイグレーション処理が一部入っていますが、慎重に運用してください。

---

ライセンス / 貢献
- README に記載が無い場合はリポジトリルートの LICENSE を参照してください。  
- バグ修正・改善提案は Pull Request をお願いします。

---

問題・質問
- 実行時のエラーや設定に関する質問があれば、発生したログメッセージ（logs/ 以下）と .env（機密情報は伏せる）を添えて問い合わせてください。