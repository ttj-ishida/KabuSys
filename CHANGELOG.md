CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠します。

フォーマット
- 変更は "Added", "Changed", "Fixed", "Deprecated", "Removed", "Security" セクションで分類します。
- バージョンごとに日付を付与します。

Unreleased
----------

- なし

0.1.0 - 2026-04-18
------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と完全分離。停止フラグ・PID 管理・デーモンスレッド管理に対応。
  - run_monitoring.py: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定管理・ウィザード・検証
  - config.py: Settings クラスによる環境変数/設定管理を追加。プロジェクトルート自動検出に基づく .env 自動読み込み（無効化フラグあり）。PAPER_FILL_MODE 等の入力検証を実装。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。シークレット項目のマスク表示、既存 .env 読み込み対応。
  - validate_config.py: 起動前設定検証 CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在とパース検証を実施（PyYAML 未インストール時は警告）。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額／スコア重み算出（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中抑制（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的な見積りをサポート。
  - portfolio.__init__: 上記関数群をエクスポート。
- ツール類
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計し PASS/FAIL 判定を出力。--from/--to/--db オプション対応。
- 研究用モジュール
  - research.factor_research: モメンタム等のファクター計算モジュール（DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計）。（初期実装）
- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定ユーティリティを追加。stdout 出力と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラの二重設定を防止するためハンドラをクリア。ログディレクトリ作成失敗時のフォールバック処理あり。
  - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度設定（Windows / POSIX 対応）および CPU affinity 設定ユーティリティを追加。psutil を利用し、権限不足や未対応 OS を安全にスキップする。
- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

Fixed
- .env 読み込みの堅牢化
  - .env パーサで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。無効行やコメント行をスキップ。
- ロギング初期化の二重登録対策
  - setup_logging() で既存ハンドラを flush/close のうえ削除してから新規ハンドラを設定するようにし、複数回初期化した際のハンドラ重複を回避。
- run_monitoring の堅牢化
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合に警告を出しデフォルト値にフォールバックする処理を追加。time.sleep に渡す値の安全性を確保。
- DB 分離の明示化
  - run_execution で paper_trading 環境用に専用 SQLite を利用するように実装（settings.is_paper 判定）。
- プロセス優先度／CPU affinity の安全ハンドリング
  - 権限不足や未実装メソッドに対して警告ログを出し処理継続するようにした（AccessDenied / NotImplementedError 等をキャッチ）。

Changed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues / TODO
- research.factor_research は初期実装であり、部分的に未完成（ファイル末尾付近で関数が途中のままになっている可能性あり）。本格運用前にレビュー・テスト推奨。
- portfolio.risk_adjustment.apply_sector_cap は price_map に 0.0 が含まれる場合にエクスポージャーが過少見積りされる旨の注記と TODO が残っている。前日終値や取得原価によるフォールバックの実装を検討中。
- position_sizing.calc_position_sizes は現状単元株数 lot_size を全銘柄共通とする想定。将来的に株ごとの lot_size マスタ導入を想定した拡張予定あり（TODO コメントあり）。
- run_monitoring/run_execution はファイルベースの停止フラグ (data/stop_requested.flag) に依存する設計。コンテナやマネージド環境では別途運用手段の検討が必要。
- validate_config の config/*.yaml 検証は PyYAML に依存。環境に PyYAML がない場合はパースチェックがスキップされ、警告を出す実装。

作者からのメモ
- 本リポジトリはローカル開発・ペーパートレード・本番運用を想定した設計を志向しています。デフォルトでの安全ガード（paper_trading 用 DB 分離、Kill Switch 等）を組み込んでいますが、本番運用前に .env 設定・LINE 通知設定等の整備を必ず行ってください。