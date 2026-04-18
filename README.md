README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／リサーチ基盤を想定した Python パッケージです。本リポジトリは以下の主要機能を含みます:

- 発注実行エンジン（ExecutionEngine）: 本番 / ペーパートレード対応
- 監視（Monitoring）: システム状態・データ鮮度・注文ログ・リスク監視
- ポートフォリオ構築ユーティリティ: 候補選定、重み算出、ポジション決定等
- リサーチモジュール: ファクター計算、将来リターン、IC 等
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI API 利用）
- 運用ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成 など

主な設計方針:
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアスを避ける設計
- API 呼び出しの失敗はフェイルセーフで扱う（可能な限り継続）

機能一覧
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、別 DB (data/paper_trading.db) に記録
  - 停止フラグ（data/stop_requested.flag）で安全停止
  - 実行時に execution.pid を生成
- 監視ループ起動スクリプト: run_monitoring.py
  - システムリソース、プロセス生存、データ鮮度を定期チェック（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
  - 監視は常に本番 sqlite_path を使用（環境に依らず）
- 監視永続化: monitoring_db.py（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル
  - 必要に応じてマイグレーションを自動実行
- リスク監視 / Kill Switch: risk_monitor.py, kill_switch.py
  - ドローダウン・ポジション上限等で kill.flag を書き込み、Execution を停止
- ポートフォリオ構築: portfolio/*.py
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ: research/*.py
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、IC、統計サマリ等
- AI: ai/news_nlp.py, ai/regime_detector.py
  - OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ツール:
  - config_setup.py: .env 対話式ウィザード（初期設定）
  - validate_config.py: 設定検証 CLI（--strict オプションあり）
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

要件（主な依存）
----------------
- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml を検証する場合）
- SQLite（標準ライブラリに含まれる）

インストール例（仮）
- 仮想環境を作成して依存をインストールしてください:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  - pip install -r requirements.txt  （requirements.txt があれば）
  - または個別に: pip install duckdb psutil openai pyyaml

環境設定 (.env)
---------------
プロジェクトルートに .env / .env.local を置くことで環境変数を設定します。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主な環境変数とデフォルト:

- 必須:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
- 推奨 / 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — デフォルト: logs/
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
  - OPENAI_API_KEY — AI モジュール利用時に必要
  - PAPER_FILL_MODE — instant | partial | never | reject (デフォルト: instant)
  - KILL_FLAG_CLEAR_ON_START — 0 or 1（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL — 監視ポーリング秒数（run_monitoring 用、デフォルト 60）

.env を対話的に作成する:
- python -m kabusys.config_setup
  - ウィザード形式で .env を生成できます
  - 生成後は python -m kabusys.validate_config で検証してください

設定検証
-------
- python -m kabusys.validate_config
  - 必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在や config/*.yaml の存在・パースを確認します
  - --strict を付けると警告も失敗扱い（exit code=1）

起動・使い方
-----------

ログ設定
- すべてのスクリプトは kabusys.utils.logging_setup.setup_logging を使います。
- ログは stdout に出力され、LOG_DIR（デフォルト logs/） に日次ローテーションでファイル出力されます。

ExecutionEngine 起動（発注実行）
- コマンド:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV が paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して発注を記録し、本番 DB と分離
  - 停止フラグ file: data/stop_requested.flag を検知して安全停止
  - 実行時に data/execution.pid を作成

Monitoring 起動（監視ループ）
- コマンド:
  - python -m kabusys.run_monitoring
- 動作:
  - Settings に従い sqlite_path（data/monitoring.db デフォルト）へ接続して監視ログを書き込む
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
  - 停止フラグ file: data/stop_requested.flag を検知してループを抜ける
  - 注意: 監視側は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します

Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 簡易用途: PAPER_TRADING_SQLITE_PATH 環境変数を指定して DB を参照可能

AI（OpenAI）機能
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（引数または環境変数）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API を用いるため同様に API キーが必要
- 注意: API エラーはリトライ + フェイルセーフ（失敗時はデフォルト値で継続）で扱います

停止 / Kill Switch
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアされる設定がありますが、本番では 0 を推奨

デフォルト DB / ログパス
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- SQLite (paper trading): data/paper_trading.db
- ログ: logs/<app_name>.log

ディレクトリ構成（主要ファイル）
-------------------------------
src/
  kabusys/
    __init__.py
    config.py                  — 環境変数 / Settings 管理（.env 自動ロード）
    config_setup.py            — .env 対話ウィザード
    validate_config.py         — 設定検証 CLI
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
    utils/
      logging_setup.py         — ログ設定ユーティリティ
      process_priority.py      — プロセス優先度 / CPU affinity 設定
    monitoring/
      monitoring_db.py         — SQLite の永続化層
      system_monitor.py        — リソース・データ鮮度監視
      trade_monitor.py         — 注文ログ監視（省略された箇所あり）
      risk_monitor.py          — ドローダウン等の監視
      kill_switch.py           — kill flag 書き込みユーティリティ
      monitoring_engine.py     — 各モニターの統括（ポーリング）
      alert_manager.py         —（アラート送信: 実装参照）
    execution/                  — 発注関連コンポーネント（OrderManager 等）
    portfolio/                  — ポートフォリオ構築ロジック
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/                   — ファクター計算・特徴量解析
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py               — ニュース NLP スコアリング（OpenAI）
      regime_detector.py        — レジーム判定（OpenAI）
    tools/
      paper_verification_report.py

開発メモ / 注意点
----------------
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダに警告あり）。
- monitoring.run uses the production sqlite_path regardless of KABUSYS_ENV — 監視は常に本番監視 DB を参照します。
- OpenAI API 呼び出しはネットワーク/レート制限・5xx 等に対して指数バックオフでリトライしますが、API キー不足は即エラーになります。
- プロセス優先度設定は psutil を使用し、OS により動作が異なります（権限が必要な場合があります）。
- DuckDB への書き込み（ai_scores 等）は executemany の空リスト渡しに注意（互換性確保のため空リストチェックあり）。

よく使うコマンド例
-----------------
- .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動（フォアグラウンド）:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 貢献
----------------
- バグ報告・機能提案は Issue にお願いします。
- 開発に参加する場合はフォークして Pull Request を送ってください。

ライセンス
---------
- 本リポジトリにライセンス表記がない場合は保守者に問い合わせてください。

以上。README の内容で不明点があれば、特定のコマンドやモジュールの使い方（例: ExecutionEngine の設定項目、AI モジュールのテスト方法、DB スキーマ詳細）についてさらに詳しく説明します。