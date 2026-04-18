KEEP A CHANGELOGに準拠した形式で、コードベースの内容から推測した変更履歴を作成しました。なお日付は本日（2026-04-18）を使用しています。

CHANGELOG.md
=============

Unreleased
---------

- 特になし

[0.1.0] - 2026-04-18
-------------------

Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時に Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用する仕組み、PID ファイル管理、停止フラグ読み取り、バックグラウンドスレッドでのエンジン実行を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能、stop フラグ検知による安全な停止、監視用 DB の初期化を行う。
- 環境設定・検証 CLI を追加
  - config_setup.py: 対話式ウィザードで .env を生成・更新するユーティリティ。シークレット項目はマスクして表示。
  - validate_config.py: .env や config/*.yaml の起動前検証ツール。必須環境変数、KABUSYS_ENV の妥当性、DB パスや YAML パースのチェック、KABUSYS_ENV=live の追加ガードを実装。--strict オプションで警告を失敗扱いに可能。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用 SQLite から稼働率、注文成功率、レイテンシなどを集計し PASS/FAIL レポートを生成する CLI。期間指定および DB パス指定対応。
- ポートフォリオ構築モジュールを追加
  - portfolio/portfolio_builder.py: シグナルのソート（スコア降順＋タイブレーク）と候補選定、等重配分・スコア加重配分の計算を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと残差処理を実装。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（セクター別エクスポージャ計算による候補除外）と市場レジームに応じた乗数（regime multiplier）を実装。
- 研究用ファクター計算スケルトンを追加
  - research/factor_research.py: DuckDB の prices_daily 等を使ったモメンタム等ファクター計算の骨組み（モメンタム期間定義や calc_momentum 関数の雛形）を追加（実装途中のファイルあり）。
- 共通ユーティリティを追加/充実
  - utils/logging_setup.py: stdout ストリームハンドラ＋日次ローテーションのファイルハンドラをルートロガーに設定する共通ロギングセットアップ。ログディレクトリの解決・作成処理、既存ハンドラのクリーンアップ、LOG_LEVEL / LOG_DIR の優先順位を実装。
  - utils/process_priority.py: psutil を使ったプロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティ。プラットフォーム差分を吸収して安全に実行。
- 設定管理を導入
  - config.py: .env 自動読み込み（.env / .env.local、OS 環境変数保護）、.env パース機能（クォートやエスケープ、インラインコメント対応）、Settings クラス（各種環境変数のラップ）を実装。PAPER_FILL_MODE 等のバリデーションや paper_sqlite_path/duckdb_path/pid ファイルパスなどの取得を提供。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db の初期化呼び出し箇所を run_* スクリプトで利用（冪等に監視テーブルを保証）。

Changed
- ログ出力の標準化
  - ロガーのデフォルト構成を統一する setup_logging を全起動スクリプトで使用するようになり、コンソールは stdout、ファイルは日次ローテーション（30日保持）で出力されるようになった。
- .env 読み込みの挙動
  - 自動ロードの順序を OS 環境 > .env.local > .env とし、既存 OS 環境を保護するため protected キーを導入。プロジェクトルート探索は .git / pyproject.toml を基準に行うように変更（CWD に依存しない）。
- 実行環境分離
  - 実行エンジンは paper_trading と本番環境で DB を分離（paper_trading 用の paper_sqlite_path を使用）し、MockBrokerClient と本物のブローカークライアントを切り替えることを想定した BrokerClientFactory を利用。
- ポートフォリオ/ポジション計算の堅牢化
  - position_sizing で cost_buffer を考慮した保守的コスト見積り、lot_size 単位での切り捨てと残差配分ロジックを実装。価格未取得時のスキップや最大ポジション上限の適用など挙動を明確化。

Fixed
- 安全な起動・停止
  - run_execution/run_monitoring で停止フラグ（data/stop_requested.flag 等）を確認し、安全にプロセスを終了するフローを追加。run_execution は既に停止フラグが立っている場合に起動をキャンセルする。
- 入力バリデーション強化
  - MONITOR_POLL_INTERVAL の値が不正（0 以下や非整数）の場合にデフォルトにフォールバックして警告を出す処理を追加。
  - Settings.env や LOG_LEVEL、PAPER_FILL_MODE などの環境変数値の妥当性チェックを追加し、不正値で早期にエラーを出すようにした。
- ログハンドラ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合、ファイルハンドラをスキップしてコンソール出力のみで続行するように変更。これによりコンテナや権限制約下でも起動しやすくなった。
- ツールの堅牢化
  - paper_verification_report でテーブルが存在しない場合（OperationalError）でも例外で止まらず N/A 等で扱うフォールバックを実装。

Security
- config_setup においてシークレット項目は表示時にマスクされる（ユーザ操作中の露出を低減）。

Notes / Known limitations
- research/factor_research.py は実装途中の箇所（calc_momentum の途中）があります。実運用前に追加実装・テストが必要です。
- 一部のユーティリティ（process_priority の nice/priority/affinity 設定）は権限やプラットフォームによって失敗する可能性があり、その場合は警告ログを出してスキップする設計です。
- Paper Trading の挙動（MockBrokerClient の実装詳細や fill_mode の挙動）は BrokerClientFactory 側の実装に依存します。

--- 

この changelog はリポジトリ内のソースコードから機能追加・設計意図・例外処理の有無などを推測して作成しています。実際の変更履歴やリリースノートはコミット履歴や maintainer の運用方針に基づいて調整してください。