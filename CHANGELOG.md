# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般的な方針:
- バージョン番号はパッケージの __version__（現行: 0.1.0）に合わせています。
- 日付はリポジトリ解析時点（この CHANGELOG 作成日）を使用しています。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム「KabuSys」の基盤機能一式を追加。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite / DuckDB 接続、BrokerClient の生成、OrderManager / RiskManager / Reconciler の組立て、スレッドでの実行監視、停止フラグ・PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔設定、停止フラグ検出、例外安全なループ実行を実装。
- 設定管理
  - config.py: .env 自動読み込み（.env / .env.local、OS 環境変数保護）、環境変数の取得ユーティリティ Settings クラスを追加（DB パス・API トークン・システム閾値等をプロパティ化）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。シークレットのマスク表示、既存値の再利用、.env テンプレート書き出し機能を提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
- ポートフォリオ構築ライブラリ（純粋関数群・DB 参照なし）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア全ゼロ時のフォールバック挙動を含む。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。regime による投下資金調整ロジックを提供（未定義レジームはフォールバック）。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、per-stock / aggregate 上限、コストバッファ考慮によるスケーリングと端数処理を実装。
  - portfolio/__init__.py: 上記関数群のエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。stdout 出力ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして安全に続行。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加。権限不足や未対応 OS 時に警告を出してスキップする安全措置あり。
- ツール類
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを集計し、閾値に基づく PASS/FAIL 判定を出力。コマンドラインで期間指定可能（--from / --to / --db）。
- リサーチ（開発途中）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨子を追加（モメンタム等の指標計算を想定）。（ファイルは実装途中で truncation の可能性あり）
- パッケージ情報
  - __init__.py: パッケージバージョンを "0.1.0" に設定。主要サブパッケージを __all__ に列挙。

### Changed
- なし（初回リリースのため該当なし）

### Fixed
- .env パーサー（config.py）での堅牢性向上
  - クォート付き値のバックスラッシュエスケープ対応、インラインコメント処理、export キーワード対応、コメント扱いの厳密化などを実装。
  - .env ファイル読み込みは OS 環境変数を保護する protected 機能を導入。
- ロギング初期化の堅牢化
  - 既存ハンドラを確実に flush/close してから再設定することで二重登録を防止。
  - ログディレクトリ作成に失敗した場合はファイルハンドラ作成をスキップしてコンソール出力のみで継続する。
- DB 初期化の冪等性
  - init_monitoring_db を各起動スクリプト（実行／監視）で呼ぶことで監視テーブルの存在を保証（既存 DB に対しても安全）。

### Security
- config_setup.py のウィザードではシークレット項目（API トークン等）をマスク表示。生成された .env ファイルは Git にコミットしないよう README 風のヘッダ注記を挿入。

### Notes / Design decisions
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず「本番」用 sqlite_path（Settings.sqlite_path）を使用する設計。対して実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合に専用 paper_sqlite_path を使用し本番 DB と分離する。
- run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能。0 以下の値は無効としてデフォルトにフォールバックする（time.sleep の ValueError 回避）。
- process_priority と CPU affinity の設定は権限や OS により失敗する可能性があるため、安全に失敗を握りつぶして警告を出力する方針。
- paper_verification_report の判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）はデフォルトの基準値として実装。必要に応じて調整可能。

### Known issues / TODO
- research/factor_research.py はファイル末尾が切れている（実装途中の可能性あり）。完全なファクター計算ロジックの追加が必要。
- position_sizing の lot_size 固定（現状: 共通の単元株 100 を想定）。将来的に銘柄別 lot_map を受け取る拡張を検討。
- apply_sector_cap の価格欠損時（price == 0.0）にエクスポージャーが過少見積りされる注意点あり（TODO コメントあり）。前日終値や取得原価によるフォールバック実装が望まれる。
- run_execution/run_monitoring の shutdown/cleanup ロジックは基本的なケースをカバーしているが、長時間停止や I/O エラー時の追加ハンドリング検討の余地あり。

---

履歴の追加や修正は次回リリース時に [Unreleased] セクションに追記してください。