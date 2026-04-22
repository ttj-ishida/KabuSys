KabuSys — 日本株自動売買システム（簡易 README）
====================================

概要
----
KabuSys は日本株向けの自動売買・監視・リサーチ用ライブラリ／実行環境です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う（本番／ペーパートレード対応）
- 監視（Monitoring）: システム状態・注文状態・リスクを定期ポーリングして永続化・アラート送出
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限等
- リサーチ: ファクター計算（モメンタム/バリュー/ボラティリティ等）、特徴量解析
- AI連携: ニュースのLLMによるセンチメントスコアリング、レジーム判定（OpenAI利用）
- ユーティリティ: 環境設定ウィザード、設定検証、ペーパートレード検証レポート等

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution : 実行エンジンを起動
  - python -m kabusys.run_monitoring : 監視プロセスを起動
- 環境設定／検証
  - python -m kabusys.config_setup : .env を対話式に作成・更新
  - python -m kabusys.validate_config : 環境変数・config/*.yaml の検証
- ペーパートレード検証
  - python -m kabusys.tools.paper_verification_report : ペーパートレード DB から検証レポートを生成
- ポートフォリオ構築（純粋関数群）
  - select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
- AI 機能
  - kabusys.ai.score_news : ニュースを LLM でスコアリングして ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector : マクロ＋MAで市場レジームを判定して market_regime テーブルへ書き込み
- 監視 DB（SQLite）永続化：system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理

セットアップ手順
----------------
前提
- Python 3.9+ を想定（実際の互換性は環境に合わせて確認してください）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証用に任意）

インストール例
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール
   - pip install duckdb psutil openai PyYAML

3. 必要ディレクトリを作成（最初だけ）
   - mkdir -p data logs

環境変数（重要なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN : （J-Quants API 用）
  - KABU_API_PASSWORD : kabuステーション API パスワード
- 推奨/オプション
  - KABUSYS_ENV : execution の実行モード（development / paper_trading / live）デフォルト: development
  - DUCKDB_PATH : DuckDB の保存先（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL : ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY : OpenAI API キー（AI 機能利用時）
  - PAPER_FILL_MODE : ペーパートレードでの約定モード（instant / partial / never / reject）
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒）※デフォルト 60

.env の作成
- 対話式ウィザードを使うのが簡単です:
  - python -m kabusys.config_setup
- 手動で .env を作る場合は .env.example を参照してください（リポジトリに例がない場合は上記キーを設定してください）。
- .env は絶対に Git にコミットしないでください。

設定検証
- python -m kabusys.validate_config
  - --strict をつけると警告も失敗として扱います

使い方（起動・停止・運用）
-------------------------

ログの準備
- デフォルトでは logs/ ディレクトリに日次ローテーションでログが保存されます（例: logs/execution.log, logs/monitoring.log）。
- 環境変数 LOG_DIR で変更可能。

ExecutionEngine（発注エンジン）起動
- 本番・テスト（ペーパー）両対応
  - 本番: KABUSYS_ENV=live
  - ペーパー: KABUSYS_ENV=paper_trading（この場合 MockBrokerClient が使用され、ペーパートレード DB に記録される）
- 起動:
  - python -m kabusys.run_execution
- 停止:
  - run_execution はプロセス内で data/stop_requested.flag を監視しています。停止したい場合はファイルを作成してください（例: touch data/stop_requested.flag）。起動時にこのフラグが存在すると起動をしません。
  - kill スイッチ（自動停止）: 監視側から data/kill.flag が書き込まれると ExecutionEngine 停止を促します。

Monitoring（監視プロセス）起動
- 起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔:
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（デフォルト 60）
- 注意:
  - run_monitoring は監視用 DB に関して、KABUSYS_ENV に関係なく本番 sqlite_path（settings.sqlite_path）を使用します。監視 DB を完全に分離したい場合は設定を調整してください。
- 停止:
  - data/stop_requested.flag を作成すると監視ループが終了します。

ペーパートレード検証レポート
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可 / 環境変数 PAPER_TRADING_SQLITE_PATH も可）

AI 機能（ニューススコアリング / レジーム判定）
- 要: OPENAI_API_KEY を設定
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None) をプログラムから呼び出し
  - または利用するスクリプト内から適宜呼ぶ
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止フラグ・kill.flag（運用上の重要点）
- 停止要求ファイル: data/stop_requested.flag — 明示的な停止要求（手動 or 管理スクリプト）
- Kill Switch フラグ: data/kill.flag — 監視側が条件を満たすと書き込み（ExecutionEngine を停止させる）
- フラグをクリアするには手動でファイルを削除: rm data/kill.flag（または KillSwitch.clear() を使う実装部分）

注意点／運用メモ
- set_process_priority("high") が起動時に呼ばれ、プロセス優先度の設定を試みます（権限により失敗する場合あり）。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップして標準出力のみになります。
- validate_config は PyYAML を利用して config/*.yaml の構文チェックを行います。PyYAML がない場合は YAML 検証をスキップします。
- OpenAI 呼び出しはリトライロジックを備えていますが、APIキーやレート制限には注意してください。
- データベースパスや重要な挙動（本番/ペーパー切替など）は .env による環境変数で制御されます。必ず validate_config でチェックしてください。

ディレクトリ構成（主要ファイル）
------------------------------
（本 README が扱っているコードベースに含まれる主なファイル / モジュール）

- src/kabusys/
  - __init__.py                   — パッケージ定義（__version__ 等）
  - config.py                     — Settings クラス（環境変数の読み込み・検証）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 簡易設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py          — 市場レジーム判定
  - monitoring/
    - monitoring_db.py            — SQLite テーブル初期化・永続化層
    - system_monitor.py           — システム状態 / データ鮮度監視
    - trade_monitor.py            — (注文監視ロジック) ※一部ファイル省略あり
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — kill.flag の書き込みロジック
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - alert_manager.py            — (アラート送信：LINE など) ※実装箇所あり
  - execution/
    - execution_engine.py         — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py             — 統一的なログ設定
    - process_priority.py          — プロセス優先度 / CPU affinity
    - __init__.py

（注）一部のモジュールは README で全コードを網羅していない可能性があります。詳細は各モジュールの docstring を参照してください。

サンプル .env（最低限）
---------------------
例（.env に書くべき最低限のキー）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=（AI 機能を使う場合に設定）

ライセンス・貢献
----------------
- この README ではライセンス情報は記載していません。実際のリポジトリに LICENSE ファイルがある場合はそちらを参照してください。
- 貢献する場合は issue / PR を送ってください。大きな設計変更や本番投入前の改修は十分なレビューを推奨します。

最後に
------
本 README はコードベースの主要な使い方と構成を短くまとめたものです。各モジュールの docstring を参照すると詳細な設計意図・パラメータ説明が書かれています。運用前には必ず python -m kabusys.validate_config による検証を行ってください。