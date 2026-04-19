CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初回リリース。
- 実行用スクリプトを追加:
  - run_execution.py: ExecutionEngine の起動スクリプトを提供。起動時にプロセス優先度を「high」に設定し、別スレッドでセッションを実行。停止は data/stop_requested.flag によるフラグで制御。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する。
  - run_monitoring.py: SystemMonitor のポーリングループ開始スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定管理機能:
  - config.py: .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）、環境変数パーサ（クォート・エスケープ・インラインコメント対応）、Settings クラス（多数のプロパティ、値検証）を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - config_setup.py: インタラクティブな .env ウィザードを追加。.env の読み書き（デフォルト値やシークレット扱い、保存前の確認）をサポート。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML があれば中身も検証）、本番環境向けの追加ガード、--strict オプションで警告を FAIL 扱いにする機能。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout 出力用 StreamHandler と 日次ローテーション (TimedRotatingFileHandler) をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで継続。ログ保持日数は 30 日。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加。アクセス権限や未対応 OS の場合は警告を出して安全にスキップする実装。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限適用 (apply_sector_cap) と市場レジームに応じた乗数 (calc_regime_multiplier) を実装。セクター未定義は "unknown" 扱いなどの挙動を定義。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）および cost_buffer を考慮した保守的見積もり、残差処理による再配分ロジックを実装。
  - portfolio/__init__.py: 上記機能をパッケージとして公開。
- 研究・分析ユーティリティ（骨格）:
  - research/factor_research.py: DuckDB 接続を用いたモメンタム等のファクター計算モジュールの骨格を追加（モメンタム期間や ATR など定数の定義を含む）。（関数実装の続きはコードベースに継続あり）
- ツール:
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定する。閾値や P95 計算ロジック、日付フィルタ、DB 存在チェックを備える。
- パッケージ定義:
  - kabusys/__init__.py: パッケージ名とバージョン (0.1.0) を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 備考
- .env のパースは実用的なケース（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント）に対応しており、意図しない値の読み込みを防止するための保護機構を含む。
- validate_config と config_setup により初期設定の導線を整備しており、起動前に設定不備を早期検出できる。
- ロギングとプロセス優先度の設定は、運用環境での安定稼働を意識したフォールバック（失敗時は警告を出してスキップ）を行う設計。
- ペーパートレード用 DB を本番 DB と完全に分離することで、テスト時の誤発注リスクを低減する設計方針を採用。

今後の改善案（TODO）
- research/factor_research.py の実装完了（ファクター計算ロジックの詳細実装）。
- portfolio/position_sizing.py の lot_size を銘柄別に対応（将来的な拡張案として記載あり）。
- apply_sector_cap の価格欠損（price が 0.0）の取り扱い改善（前日終値等のフォールバック導入）。
- validate_config の YAML 検証で PyYAML 非依存時の代替フロー改善。