README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ/監視フレームワークです。  
DuckDB／SQLite をデータレイヤに、kabuステーション API（実口座）や MockBroker（ペーパートレード）を通じて発注・検証を行います。AI（OpenAI）を利用したニュースセンチメント評価や、市場レジーム判定、ポートフォリオ構築・位置決め・リスク制御、監視（モニタリング）機能を含みます。

主な特徴
--------
- 発注エンジン（ExecutionEngine）
  - KABUSYS_ENV に応じて実口座 / ペーパートレード（Mock）を切替
  - 発注管理／リスク管理／オーダー再照合（Reconciler）などを実装
- 監視コンポーネント（Monitoring）
  - システム状態（CPU / メモリ / ディスク）、プロセス生存チェック、データ鮮度監視
  - 注文ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch によるフラグファイル停止、アラート通知機構（LINE 等）
- リサーチ機能
  - DuckDB 上でのファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI 機能（OpenAI）
  - ニュースを LLM で解析して銘柄ごとのセンチメントスコア生成（ai_scores テーブルに書き込み）
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定
- ポートフォリオ構築
  - シグナル選定、等金額／スコア加重によるウェイト計算、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数などの調整ロジック
- 運用支援ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成スクリプト

セットアップ
----------
前提:
- Python 3.10+（型アノテーションに Union | を使用）
- Git リポジトリのクローン

1) 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 必要パッケージ（代表例）
   - duckdb
   - psutil
   - openai
   - PyYAML（任意：config YAML 検証用）
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを使用してください）

3) 初期設定 (.env)
   - 対話式ウィザードを実行して .env を生成できます:
       python -m kabusys.config_setup
   - 生成される主な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|...)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、通知用）
     - KILL_FLAG_CLEAR_ON_START (0|1)

4) 設定検証
   - .env 作成後、設定整合性をチェック:
       python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
       python -m kabusys.validate_config --strict

使い方（スクリプト・運用）
-----------------------

起動スクリプト
- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作ポイント:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録して本番 DB と分離
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID ファイルを書きます
    - 停止は stop フラグ（stop_requested.flag）または外部から engine.stop() を呼ぶことで行います

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 動作ポイント:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
    - monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込む
    - data/stop_requested.flag が存在するとループを抜けて終了

ログ
- 共通ログ設定ユーティリティが用意されています:
    from kabusys.utils.logging_setup import setup_logging
- ログは標準出力（stdout）と日次ローテートされるファイル（logs/<app_name>.log）に出力されます
- LOG_DIR 環境変数や setup_logging の引数で出力先を変更可能

監視 / Kill Switch
- kill_switch（data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送れます
- KillSwitch はリスク（ドローダウンやポジション上限）に応じて自動でフラグを作成します
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でフラグをクリアします（本番では 0 推奨）

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
  - 稼働率、注文成功率、送信率、レイテンシ等を集計し PASS/FAIL を報告

AI 機能（OpenAI）
- ニュース NLP（センチメント）:
    from kabusys.ai import score_news（内部で OpenAI を使用）
- 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
- OpenAI を使う機能は OPENAI_API_KEY の設定が必要です（もしくは各関数へ api_key を渡す）
- API エラー時のフェイルセーフ（多くのケースでスコア 0 やスキップ）を組み込んでいます

データベース（デフォルトパス）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数／設定読み込みロジック（自動 .env ロード含む）
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルがある想定)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルがある想定)
    - monitoring_engine.py
  - execution/
    - execution_engine.py (実装ファイルがある想定)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

注意事項 / 運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では設定ミスに注意してください。validate_config は本番向け追加チェック（LINE 通知設定など）を行います。
- .env は絶対に Git へコミットしないでください（config_setup でも注意喚起あり）。
- OpenAI の利用は API コストが発生します。news_nlp や regime_detector は呼び出し回数を考慮して運用してください。
- ログディレクトリ作成やファイル書き込み権限に注意。logs/ ディレクトリ作成に失敗した場合、ファイル出力は無効になりコンソールのみに出力されます。
- プロセス優先度の設定（set_process_priority）は OS 権限に依存します。AccessDenied が発生する場合は警告を出してスキップされます。

よく使うコマンドまとめ
---------------------
- .env を対話的に作成:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
- 実行エンジン起動:
    python -m kabusys.run_execution
- 監視ループ起動:
    python -m kabusys.run_monitoring
- Paper Trading レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（本リポジトリ固有のライセンス・貢献ルールをここに追記してください）

以上。必要であれば README に含める環境変数のサンプル .env テンプレートや、requirements.txt の具体例、各モジュールの API 使用例（簡単なコードスニペット）を追加できます。どの情報を優先して追記しますか？