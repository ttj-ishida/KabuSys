README
=====

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリには以下の主要コンポーネントを含みます:

- ExecutionEngine: 発注・注文管理・リスク管理を実行するエンジン（本番 / ペーパートレード対応）
- Monitoring: システム監視・ログ収集・Kill Switch による停止制御
- Research / Portfolio: ファクター計算、特徴量解析、ポートフォリオ構築（候補選定・比率計算・ポジションサイジング）
- AI ユーティリティ: ニュース NLP（OpenAI を使用したセンチメント）、市場レジーム判定
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- 設定ユーティリティ: .env 対話式ウィザード / 設定検証 CLI

主な機能
--------
- 環境別動作: KABUSYS_ENV により development / paper_trading / live を切替
  - paper_trading 時は MockBroker を使用し、ペーパートレード用 DB に記録（本番 DB と分離）
- 実行エンジン:
  - ブローカー抽象化、注文管理、リスク管理、reconciler による整合性維持
- 監視:
  - CPU / メモリ / ディスク・プロセス稼働監視、データ鮮度チェック、リスク監視（ドローダウン・ポジション上限）
  - kill.flag による安全停止（モニタが条件を満たすとフラグを書き込み）
- 研究/ファクター:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン、IC 計算、統計サマリー
- AI:
  - OpenAI を使ったニュースセンチメント集計と市場レジーム判定（gpt-4o-mini 想定）
  - 失敗時のフェイルセーフ、バッチ処理、結果の DB 書き戻し
- ツール:
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

前提 / 必要環境
---------------
- Python 3.10+
- 推奨パッケージ（requirements.txt を用意している想定）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML 検査を行う場合）
- ファイルシステムに書き込み可能な data/ および logs/ ディレクトリ

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します。生成後、以下の必須環境変数が設定されていることを確認してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合は OPENAI_API_KEY を環境変数に設定してください（.env に含めても可）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)（デフォルト: development）
  - paper_trading の場合、MockBrokerClient と別 SQLite DB を使用
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）: DuckDB ファイルパス
- SQLITE_PATH（デフォルト: data/monitoring.db）: 監視用 SQLite
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）: ペーパートレード専用 SQLite
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）: ペーパートレードの約定挙動
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（秒、デフォルト: 60）: monitoring のポーリング間隔
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0）: Execution 起動時に kill.flag を自動クリア（本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを抑止できます（テスト用）

使い方（起動コマンド）
--------------------
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 機能:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に書き込み
    - 起動時に data/stop_requested.flag が存在する場合は起動しません（安全機構）
    - 実行中に data/stop_requested.flag が作成されると安全に停止します

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）
  - 監視は常に production 用の sqlite_path を参照する（環境に依らず本番 path を使用）
  - run_monitoring も data/stop_requested.flag の存在でループを終了します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルトを上書き可能

- AI / レジーム判定・ニューススコアリング（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、DB テーブルを参照して結果を書き込みます。
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY で指定

停止と Kill スイッチ
-------------------
- 停止要求（即時停止ではなく順次終了を促す）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検出して終了します
- Kill Switch（モニタ側から強制停止シグナル）
  - Monitoring が条件を評価して data/kill.flag を書き込むと Execution 側で別経路（設定に応じて）停止できます
  - kill.flag を手動で削除する場合:
    - rm data/kill.flag
  - Settings.kill_flag_clear_on_start を 1 に設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）

ログ
----
- デフォルトは logs/ ディレクトリに出力（app_name ごとに daily ローテートされたファイル: e.g. logs/execution.log）
- setup_logging() でルートロガーを統一的に設定（コンソール stdout + 日次ローテーション）
- LOG_DIR 環境変数で出力先を変更可能

開発者向けメモ / 注意事項
-----------------------
- .env は絶対に Git にコミットしないこと
- validate_config は起動前チェックに有用（YAML のパースチェックは PyYAML が必要）
- DuckDB / SQLite のファイルはデフォルトで data/ 以下に配置。バックアップに注意
- AI 機能は外部 API（OpenAI）に依存するため API 呼び出し失敗時のフォールバックが組み込まれていますが、API キー設定と利用制限に留意してください
- process priority の設定は psutil を使用。権限不足でワーニングが出る場合があります

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイルの一覧と簡単な説明（実際のツリーは src/kabusys 以下）:

- src/kabusys/
  - __init__.py                — パッケージ定義・バージョン
  - config.py                  — 環境変数 / Settings 管理、.env 自動ロード機構
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/                 — 発注エンジン関連（broker_factory, execution_engine, order_manager 等）
  - monitoring/
    - monitoring_db.py         — 監視 DB（SQLite）初期化・永続化 API
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視（該当ファイルはプロジェクトに含まれる想定）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — 各 monitor を束ねるループ
    - alert_manager.py         — 通知管理（LINE 等 — 実装は別ファイル）
  - portfolio/
    - portfolio_builder.py     — 候補選定・等重／スコア重み計算
    - position_sizing.py       — 発注株数算出・スケーリング・単元丸め
    - risk_adjustment.py       — セクター上限適用・レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI で銘柄ごとのスコア算出）
    - regime_detector.py       — マクロ + ETF MA200 によるレジーム判定（OpenAI 併用）
  - data/                      — 既定の data ファイル群（DB やフラグファイルを配置）
  - logs/                      — 既定のログ出力先

サンプル .env（抜粋）
--------------------
以下は .env の例（config_setup で対話式に生成可能）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

ライセンス / 貢献
-----------------
- 本ドキュメントはコードベースに基づく概要説明です。実運用環境での使用前に必ず設定検証と十分なテストを行ってください。
- 貢献やバグ報告は Pull Request / Issue にてお願いします。

お問い合わせ
------------
- README に不足がある箇所や起動時の問題があれば、どのコマンドでどのエラーが出たかを添えて質問してください。具体的なログや環境変数の（機密情報を除いた）内容があると助かります。