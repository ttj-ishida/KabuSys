# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-04-19

初回リリース。

### Added
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用に分離された SQLite DB（data/paper_trading.db 既定）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（既定 60 秒）。監視は環境設定にかかわらず本番の sqlite_path を使用。
- 環境・設定管理
  - config.py: .env 自動ロード機能（.env/.env.local）、.env パースユーティリティ、Settings クラスによる環境変数アクセスの統一を追加。PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH などペーパートレード向け設定を含む。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加（シークレット項目のマスク表示、保存確認を実装）。
  - validate_config.py: 起動前に .env と config/*.yaml の基本的な妥当性チェックを行う CLI を追加（--strict オプションで警告をエラー扱いにできる）。
- 監視・運用
  - 監視データベース初期化（init_monitoring_db）呼び出しを run_execution/run_monitoring で保証。
  - PID / 停止フラグ（data/execution.pid, data/stop_requested.flag）を用いた安全な起動/停止制御を導入。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て0のときは等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。未知レジームは警告してフォールバック。
  - portfolio/position_sizing.py: 単元株丸め・リスクベース/等配分/スコア配分に対応した発注株数計算（calc_position_sizes）を追加。aggregate cap に基づくスケーリングと端数調整ロジックを実装。
  - portfolio パッケージ __init__ に主要 API をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー統一設定ユーティリティを追加。コンソール（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler）を設定、既存ハンドラをクリアすることで二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: Windows / POSIX に対応したプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足時は警告でスキップ。
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し PASS/FAIL 判定を行う。日付フィルタ（--from/--to）および DB パス指定（--db / 環境変数）に対応。
- パッケージ情報
  - __init__.py にバージョン (0.1.0) と主要パッケージを定義。

### Changed
- ロギングの挙動を統一
  - setup_logging() によって全起動スクリプトで同一のログ設定を適用するように変更。ログレベル解決順（引数 > 環境変数 > デフォルト）とログディレクトリ解決順（引数 > 環境変数 > デフォルト）を明確化。
- DB パスと環境依存分離
  - run_execution はペーパートレード時に専用 SQLite DB を使用するように分離。monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明記。
- .env 読み込みの優先度
  - OS 環境変数保護を導入し、.env.local は .env を上書きするが OS 環境変数は上書きしない動作に変更。

### Fixed
- 環境変数パースの堅牢化
  - _parse_env_line() でクォートされた値のバックスラッシュエスケープ処理やインラインコメント処理、export プレフィックス対応等を実装。不正行やプレースホルダ値を適切に扱うよう改善。
- MONITOR_POLL_INTERVAL の不正値対応
  - run_monitoring の _get_poll_interval() で 0 以下や整数変換失敗時にデフォルトへフォールバックし、警告ログを出すようにした（time.sleep に渡す不正値による例外防止）。
- プロセス優先度設定の安全化
  - set_process_priority / set_cpu_affinity は権限不足や未サポート環境で例外を投げず警告でスキップするようにして起動の堅牢性を向上。
- ポートフォリオ計算のフォールバック
  - calc_score_weights() で全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、警告ログを出力。
  - apply_sector_cap() は sector_map に存在しない銘柄を "unknown" 扱いとし、unknown セクターは上限チェックから除外する旨を明確化。
  - calc_position_sizes() の集約キャップ適用で単元株（lot_size）での丸めや残余キャッシュを用いた再配分を実装し、より合理的な数量決定を行うよう修正。
- YAML 検証の非必須化
  - validate_config.py は PyYAML 未導入時に YAML 検証をスキップし、警告を出すことで環境による起動障害を防止。
- ログ出力フォールバック
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合はファイル出力を無効化してコンソールのみで継続するように改善。

### Security
- config_setup.py にて .env ファイル生成時に「.env を絶対に Git にコミットしないこと」を明示。シークレット項目はウィザード表示時にマスクして表示。
- Settings._require() は必須環境変数未設定時に明確な ValueError を発生させることで起動時の不正構成を速やかに検出。

### Notes / Known limitations
- research/factor_research.py はモジュールが途中まで実装されており、いくつかの計算（Momentum 等）はまだ未完の状態（実装継続予定）。DuckDB 接続を前提としているため、テーブル構成とデータ準備が必要。
- run_monitoring / run_execution は外部モジュール（monitoring.system_monitor、execution.* 等）に依存しており、本リリースではそれらコンポーネントの実装が別途必要。
- calc_position_sizes の価格欠損時の扱い（price が 0.0 の場合の過少見積り）は TODO コメントとして注意喚起している。将来的に前日終値等のフォールバックを検討。

--- 

今後の予定
- factor_research の完全実装（ファクター計算の完成）
- execution / broker 周りのテストカバレッジ拡充と MockBrokerClient の整備
- ドキュメント（PortfolioConstruction.md 等）に基づく追加の検証ツール・CI 統合

