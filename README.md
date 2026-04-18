KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なフレームワーク群です。本リポジトリは以下の機能を提供します。

- 発注エンジン（ExecutionEngine）とブローカークライアント（本番 / ペーパートレード分離）
- 監視サブシステム（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築（候補選定、ウエイト算出、ポジション計算、セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC算出）
- AI 支援機能（ニュースの NLP によるセンチメント評価、市場レジーム判定）
- 運用支援ツール（対話式 .env 作成、設定検証、ペーパートレード検証レポート等）

主な設計方針:
- 本番 DB とペーパートレード DB を分離している（KABUSYS_ENV により切替）
- 時刻参照でのルックアヘッドバイアスを避ける実装（関数に target_date を渡す設計）
- フェイルセーフ（API失敗時はフォールバックして継続）
- ロギング・プロセス優先度設定など運用を意識したユーティリティ

機能一覧
--------
- 実行（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  - プロセス優先度設定、PID 管理、停止フラグ（data/stop_requested.flag / data/kill.flag）対応
- 監視（run_monitoring.py / MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行
  - 監視結果は SQLite（monitoring.db）に永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 環境設定支援
  - config_setup.py : 対話式ウィザードで .env を生成/更新
  - validate_config.py : .env と config/*.yaml の検証（--strict オプションあり）
- データベース／監視永続化
  - monitoring_db.py: 必要なテーブル作成・マイグレーションと CRUD ユーティリティ
- ポートフォリオ構築
  - 銘柄選定（select_candidates）、重み計算（equal/score）、ポジションサイズ計算（risk_based 等）
  - セクターキャップ、レジーム乗数適用
- リサーチ
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - feature_exploration: forward returns / IC / 統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM に送信し銘柄別センチメントを ai_scores に書き込み
  - regime_detector.score_regime: 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に記録
- ツール
  - tools.paper_verification_report: ペーパートレード DB から期間レポートを生成（PASS/FAIL 判定）

前提 / 必要環境
--------------
- Python 3.10+
- 基本的な外部ライブラリ（プロダクション用途では requirements.txt を用意してください）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML の構文チェックを行う場合）
- ファイルおよびディレクトリ: data/（DB・フラグ）、logs/（ログ出力）
  - これらは自動生成されますが、権限等に注意してください。

セットアップ手順
---------------
1. リポジトリをクローンし作業ディレクトリへ移動
   - (例) git clone ... ; cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt を作成して管理してください

4. 初期ディレクトリ（必要に応じて）
   - mkdir -p data logs

5. 対話式 .env の作成
   - python -m kabusys.config_setup
   - 指示に従い J-Quants トークン、kabu API パスワード等を設定してください
   - 出力される .env は絶対に Git にコミットしないでください

6. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

7. DB 初期化
   - 実行スクリプト（run_monitoring / run_execution）を起動すると monitoring DB（SQLite）や DuckDB は必要に応じて初期化されます
   - 監視用 DB を手動で初期化したい場合は、Python で init_monitoring_db() を呼ぶこともできます

環境変数（主なもの）
-------------------
重要な環境変数（.env で設定）:
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABUSYS_ENV : 実行環境（development | paper_trading | live）（デフォルト: development）
  - paper_trading: MockBrokerClient を使用、ペーパートレード用 DB に記録
  - live: 本番（実際に発注）

データベース / ファイルパス:
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH : ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH : Kill Switch 用フラグファイル（デフォルト data/kill.flag）

運用関連:
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリア（1: 有効 / 0: 無効、production では 0 推奨）
- PAPER_FILL_MODE : ペーパートレードの約定挙動（instant|partial|never|reject）

AI 関連:
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で必要）

自動 .env ロード:
- プロジェクトルートに .env / .env.local がある場合、自動で環境変数に読み込まれます
- テスト等で自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要コマンド）
--------------------

1. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB を使用（settings.paper_sqlite_path）
   - 起動前に data/stop_requested.flag が存在するとエンジンは起動しません
   - 実行中は data/execution.pid に PID が書き込まれます。停止は stop フラグの作成（data/stop_requested.flag）で行います

2. 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒）
   - 監視は常に本番 sqlite_path を使用してログを記録します（KABUSYS_ENV にかかわらず）

3. 設定ウィザード
   - python -m kabusys.config_setup
   - .env を対話的に作成 / 更新します

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

6. AI 機能（プログラムから呼び出す）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡して呼び出します。api_key が None の場合 OPENAI_API_KEY を使用
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - 同様に DuckDB を渡して日次の market_regime を更新します

監視と停止フラグ
----------------
- 停止フラグ: data/stop_requested.flag — run_execution / run_monitoring はこれを検知して優雅に終了します
- Kill Switch: data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に強制停止を促します
- PID ファイル: data/execution.pid — 実行中の PID を記録（プロセス管理や stale PID 判定に利用）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み / Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（AI + MA200）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ・永続化 API
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py        —（未記載の実装ファイル）取引監視ロジック
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch 制御
    - alert_manager.py        —（未記載の実装ファイル）通知管理
  - execution/
    - execution_engine.py     — ExecutionEngine（メインロジック）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py        — 注文管理
    - order_repository.py     — DB への注文永続化
    - reconciler.py           — 注文状態の突合せ
    - risk_manager.py         — 発注リスク制御
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数計算・aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等
    - feature_exploration.py  — forward returns / IC / summary
  - data/
    - pipeline.py             — （参照されるデータパイプライン; 実装に依存）
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - その他ユーティリティ

注意事項 / 運用上のポイント
--------------------------
- .env は絶対にリポジトリにコミットしないでください（秘密情報を含む）
- 本番環境（KABUSYS_ENV=live）での KILL_FLAG_CLEAR_ON_START=1 は危険です（自動的に kill.flag をクリアしてしまう）
- OpenAI を使う機能は API キーとコスト管理に注意してください（バッチ処理・レート制限に配慮）
- DuckDB / SQLite のファイルパスは設定で変更できます。バックアップや配置場所に注意してください
- 監視間隔やリスク閾値は Settings / config/*.yaml（プロジェクトの設定ファイル）で調整してください

開発者向けヒント
-----------------
- 単体関数群（portfolio/*.py、research/*.py）は副作用を持たずテストしやすく設計されています
- AI 呼び出しはモジュール内で _call_openai_api を分離しているため unittest.mock で差し替えてテスト可能です
- validate_config は起動前の簡易チェックとして有用です。CI に組み込むことを推奨します

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）
- ライセンス情報がリポジトリに含まれている場合はそちらに従ってください

最後に
------
まずは .env を作成し validate_config で問題がないことを確認してください。ローカルでの動作確認時は KABUSYS_ENV=development / paper_trading を使い、本番切替は慎重に行ってください。

README に含めたい追加情報（例: 実際の設定例、CI 手順、デプロイ手順、詳細な監視閾値など）があれば教えてください。必要に応じて README を拡張します。