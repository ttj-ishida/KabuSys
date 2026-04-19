# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付や記述はコード内の実装内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期リリース相当の主要機能を追加。
- 実行エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて実行挙動を切り替え（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 用 SQLite に記録）。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知機構を実装。
- 設定・環境変数管理:
  - config.py: Settings クラスを導入し、環境変数やデフォルト値を統一的に読み取り（J-Quants、kabu API、DB パス、ログ設定等）。.env 自動ロード機能を実装（優先順: OS 環境 > .env.local > .env、無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加（シークレット項目のマスク表示、デフォルト値、保存確認を実装）。
  - validate_config.py: .env や config/*.yaml の起動前チェックツールを追加（--strict オプションで警告を FAIL 扱いにできる）。
- ロギング・プロセスチューニング:
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。コンソール出力は stdout、日次ローテートのファイル出力（TimedRotatingFileHandler）をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティを追加。アクセス不可時は警告でスキップ。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py: シグナル選択（スコア降順）と等分・スコア加重の重み算出を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数決定ロジックを実装（risk_based / equal / score 両対応、lot_size 単位丸め、aggregate cap スケーリング、手数料・スリッページのバッファ計算）。
  - portfolio/risk_adjustment.py: セクター集中上限の除外ロジックと市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio/__init__.py: 上記関数をパッケージ公開。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。期間フィルタ・稼働率/成功率/送信率/レイテンシ（平均/最大/P95）などを算出し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能。
- モニタリング DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を呼び出して必要な監視テーブルの存在を保証（冪等）。
- パッケージ情報:
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- DB 分離ルールを明文化（実装）:
  - run_execution: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、発注/ログを本番 DB から分離。
  - run_monitoring: 監視データは実装上は本番の sqlite_path を使用（環境に依存せず監視用 DB のパスを利用）。
- .env パーサの強化:
  - config._parse_env_line にて export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理等の実装により .env の柔軟な解析を実現。
  - OS 環境変数を protected として .env からの上書きを制御。
- ロギング設定の挙動改善:
  - 既存ハンドラを flush/close の上で削除してから再設定することで二重ハンドラ設定を防止。
  - 標準出力に stdout を使用し、cron 等でのリダイレクト運用を考慮。
- エラー耐性の向上:
  - run_monitoring / run_execution のメインループで例外を捕捉しログ出力後にループ継続（監視の堅牢化）。
  - DB/duckdb 接続の確実なクローズを finally 節で実施。

### Fixed
- 環境変数の妥当性チェック:
  - Settings の各種プロパティで不正値（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）を検出して ValueError を発生させるようにし、不正設定での誤動作を防止。
- CLI ツールの使い勝手改善:
  - validate_config による各種チェック（必須環境変数、パスの親ディレクトリ存在確認、YAML パースの有無チェック）を追加。PyYAML 未インストール時は YAML 検証をスキップし警告を出す。

### Security
- config_setup にて .env の自動コミット防止を明記（.env を絶対に Git にコミットしないことをドキュメント化）。
- .env 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、テストや CI での副作用を抑制可能。

### Other / Notes
- research/factor_research.py はファクター計算（モメンタム等）実装を開始。DuckDB 接続を利用して prices_daily / raw_financials を参照し各種ファクターを返す設計だが、ファイルは途中で切れている（未完の箇所あり）。将来的にファクター計算群の追加が予定される。
- いくつかの TODO コメントや将来拡張（銘柄別 lot_size、価格フォールバック処理など）をコード内に残している。

## Deprecated
- なし

## Removed
- なし

## Security
- なし

（注）上記はリポジトリに含まれるコードからの挙動・意図を推測してまとめた CHANGELOG です。実際のリリースノートや公開日付は運用ポリシーに合わせて調整してください。