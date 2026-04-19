CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 追加予定 / 注意点（コード中の TODO 等から推測）
  - 銘柄別の単元（lot_size）を stocks マスタ等から取得する設計への拡張予定（現状は全銘柄共通の単元数を想定）。
  - apply_sector_cap の price が欠損した場合のフォールバック価格（前日終値や取得原価など）を導入予定。
  - research.factor_research の実装継続（ファクター計算ロジックの完成・テスト・最適化）。
  - その他ログ・ファイルハンドラの堅牢化、運用向けの監視/アラート改善。

0.1.0 - 2026-04-19
------------------

Added
- 基本パッケージ初期実装
  - kabusys パッケージ（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用の専用 SQLite を使う（本番 DB と分離）。停止フラグ/ PID ファイル連携、スレッド実行管理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きに対応（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite_path を使用する仕様。
- 設定関連ツール
  - config.py: 環境変数読み込み・ラッパー実装（.env 自動ロード、保護付き上書き、各種設定プロパティ）。値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - config_setup.py: 対話式 .env ウィザードを実装（.env の作成・更新、シークレットマスク表示、保存確認）。
  - validate_config.py: 起動前検証 CLI を実装（必須環境変数、パス、config/*.yaml の存在および YAML パースチェック、KABUSYS_ENV=live 時のガード等）。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティ。コンソール(stdout) と 日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
  - utils/process_priority.py: Windows / POSIX の差を吸収するプロセス優先度設定および CPU affinity 設定ユーティリティ（psutil ベース）。権限不足時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコアが全て 0 の場合のフォールバック動作を含む。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ）を実装。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py: position size の計算（risk_based / equal / score）を実装。単元丸め、per-stock 上限、aggregate cap によるスケールダウンと端数処理ロジックを含む。cost_buffer による保守的コスト見積りを考慮。
- Paper Trading 向けツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。uptime, fill rate, send rate, latency(P95) 等を算出して PASS/FAIL 判定（閾値設定あり）。--from/--to/--db オプション対応。
- 研究用モジュール（途中実装）
  - research/factor_research.py: DuckDB を用いたファクター計算基盤（Momentum, Value, Volatility, Liquidity）を設計・実装開始。calc_momentum 等の関数骨格を含む（実装継続予定）。
- DB 初期化・監視関連
  - monitoring.monitoring_db.init_monitoring_db の利用により、起動時に監視用テーブルが存在することを保証（冪等）。

Changed
- 環境変数自動ロードの優先順を確立
  - OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートは .git または pyproject.toml を基準に探索。
- ログ出力ポリシー
  - StreamHandler は stdout を使用（stderr ではない）。ファイルハンドラは日次ローテーション・30日保持。
- run_execution の DB 接続
  - paper_trading 環境時は paper_sqlite_path を使用し、本番 DB と分離する実装。

Fixed
- 環境変数パースの堅牢化
  - .env パーサが export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 負値や非数値が指定された場合にデフォルト値へフォールバックして警告を出力するように修正（run_monitoring）。
- process_priority と CPU affinity のエラー耐性
  - 権限不足や未対応 OS の場合に例外を投げず、警告ログを出す実装に改善。

Security
- 機密情報の取り扱い
  - config_setup と .env の運用ドキュメント内で「.env を絶対に Git にコミットしない」旨を明示。

Notes / Known issues
- apply_sector_cap は price_map に 0.0 が渡された場合にエクスポージャーが過少見積りされる可能性がある旨を TODO コメントで明示。将来的にフォールバック価格を導入する予定。
- research.factor_research の実装はまだ完成していないファイルの箇所があり、追加の実装・テストが必要。
- position_sizing の将来的拡張点: 銘柄別の lot_size をサポートする設計に変更予定。

Acknowledgments
- 初期実装において、ロギング・プロセス制御・環境設定まわりに特に配慮し、運用時の安全性と可観測性を重視した構成になっています。

-----