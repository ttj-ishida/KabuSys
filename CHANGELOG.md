CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
-------------

- （現在のスナップショットでは未リリースの作業はありません）

[0.1.0] - 2026-04-24
-------------------

Added
- 初回公開: KabuSys 基本機能を実装・追加
  - 起動スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用可能にする。停止フラグ・PIDファイル管理・スレッド監視を実装。
    - run_monitoring.py: SystemMonitor ポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 設定・環境管理
    - config.py: .env 自動読み込み、OS環境変数保護、複雑な .env 行のパース（export対応、クォートとエスケープ、コメント処理）や各種設定値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。Settings クラスを提供。
    - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。必須・任意項目・既存値の再利用・書き込みをサポート。
    - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数・KABUSYS_ENV の妥当性・DBパス・config/*.yaml の存在とパース（PyYAML がある場合）・本番向けガード等を検査。--strict オプションで警告をエラー扱いに可能。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック対応などを実装。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）・CPU affinity を設定するユーティリティを追加。アクセス権限エラー時に安全にスキップ。
  - ポートフォリオ構築モジュール
    - portfolio/portfolio_builder.py: シグナル選定および等配分・スコア加重配分の関数を実装（select_candidates, calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等配分にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）と市場レジームに基づく乗数計算（calc_regime_multiplier）を実装。未知レジームのフォールバックやログ出力あり。
    - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の方式、単元株丸め、per-stock/aggregate 上限、cost_buffer による保守的見積、スケーリング時の残差処理）。
  - 分析・研究
    - research/factor_research.py: ファクター計算モジュールを実装（モメンタム / MA200乖離 / ATR / 出来高等の設計方針と定数を含む）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し PASS/FAIL を判定。--from/--to/--db オプションをサポート。
  - その他
    - monitoring.monitoring_db モジュール呼び出し（DB 初期化）や SystemMonitor/ExecutionEngine 等の起動連携を追加（run_* スクリプト側での統合）。
    - パッケージバージョン定義: __version__ = "0.1.0"

Changed
- （初回リリースのため履歴的変更なし）

Fixed
- 初回実装時に下記の堅牢性対応を実施
  - .env 読み込み失敗時に警告を出して処理を継続（config._load_env_file）。
  - logging_setup: 既存ハンドラを安全に flush/close してから削除し、ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続。
  - process_priority: サポート外 OS や権限不足時に警告を出してスキップ。
  - run_monitoring: monitor.check_once() 内の例外をキャッチしてループを継続（監視の堅牢化）。
  - run_execution: 停止フラグ検出時の安全な停止処理とスレッド join のタイムアウト処理を導入。

Security
- シークレット値（J-Quants トークン・kabu パスワード・LINE トークン）の取り扱いについて注意書きを追加（config_setup にて .env を Git にコミットしない旨を明示）。

Notes / Migration
- デフォルトの SQLite / DuckDB ファイルパス等は .env または環境変数で上書き可能（例: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH）。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading.db を用いて本番データと完全に分離する設計。
- 起動前に python -m kabusys.validate_config で環境を検証することを推奨。
- run_monitoring 実行時に停止させたい場合はプロジェクトの data/stop_requested.flag を作成することで安全に停止可能。

Acknowledgements
- 本 CHANGELOG は現在のコードベースからの機能・挙動を推測して作成しています。実際の履歴（コミット履歴等）と差異がある可能性があります。必要であれば、コミットログやリリースノートとの突合せで更に正確な履歴に更新してください。