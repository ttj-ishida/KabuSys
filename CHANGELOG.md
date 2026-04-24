CHANGELOG
=========

すべての重要な変更点はここに記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。
タグ付けはセマンティックバージョニングを想定しています。

Unreleased
----------

- （現時点の開発中の変更はここに記載します）

0.1.0 - 2026-04-24
------------------

Added
- 初回リリース。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時は専用の Paper Trading 用 DB を使用し、MockBrokerClient 経由で発注のシミュレーションを実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する処理を組み込んでいる。
  - 停止制御: プロジェクト直下の data/stop_requested.flag による停止フラグ検知と PID ファイルの利用をサポート。

- 設定・環境管理
  - config.py: 環境変数の取得・検証を集約する Settings クラスを導入。.env 自動読み込み機能（.env / .env.local）を備え、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - config_setup.py: .env を対話的に作成・更新するウィザードを追加（デフォルト値、シークレット入力、保存機能）。
  - validate_config.py: 起動前に .env と config/*.yaml の不備を検出する CLI を追加（--strict オプションで警告も fail 扱い）。

- 監視・検証関連
  - monitoring モジュール初期化処理を実装。run_execution と run_monitoring の起動時に監視用テーブルの存在を冪等的に保証する init_monitoring_db 呼び出しを追加。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計し PASS/FAIL を判定する。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler (stdout) と TimedRotatingFileHandler（日次・30 日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収したプロセス優先度設定・CPU affinity 設定ユーティリティを追加。アクセス権限不足等で失敗した場合は警告を出してフォールバックする。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と、マーケットレジームに応じた資金乗数を返す calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: リスクベース／等配分／スコア配分に基づく株数決定ロジックを実装。単元（lot_size）丸め、aggregate cap によるスケールダウン、残差分を考慮した追加配分アルゴリズムを含む。

- リサーチ（部分実装）
  - research/factor_research.py: Momentum を含むファクター計算モジュールの骨組みを追加（DuckDB 接続を受け取り prices_daily 等を参照して計算する方針）。モジュール内に計算対象・期間等の定数と設計方針を明記。

Changed
- デフォルトのファイルパスや環境変数名を明確化（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID ファイル等）。
- .env 読み込みの優先順位を OS 環境変数 > .env.local > .env に明確化。既存の OS 環境変数は保護される（protected）。

Fixed
- 環境変数パーサーの堅牢化:
  - export プレフィックス対応、引用符つき値のバックスラッシュエスケープ処理、コメント記法の取り扱いを強化。
  - 必須環境変数未設定時に明示的なエラーを出す _require を導入。

Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する前にウィザード上でマスク表示されるよう配慮。
- .env ファイルの Git コミット禁止を README に明記するよう生成ヘッダを出力（config_setup の書き込みテンプレート）。

Known issues / Notes
- research/factor_research.py はファクター計算の骨組みと定数を備えるが、一部関数実装（ファイル終端での計算ロジック）が未完または切り出し途中の箇所が見られる。今後の実装・レビューが必要。
- position_sizing と risk_adjustment の実装上で、価格データが欠損した場合のフォールバック（前日終値や取得原価を使う等）は TODO コメントで指摘されており、将来の改良が想定されている。
- logging_setup: ログディレクトリ作成に失敗した際はファイルログが無効化されコンソールのみになる（意図的）。
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番向けの監視 DB）を使用する旨の振る舞いに注意。
- validate_config は PyYAML 未インストール時に config/*.yaml の構文検査をスキップする。CI 等では PyYAML をインストールすることを推奨。
- KILL_FLAG_CLEAR_ON_START は production で 1 にすると危険（validate_config で警告）。デフォルトは 0。

Migration / Deployment notes
- 環境変数の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Paper Trading を有効にする場合は KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH を適切に構成することで本番 DB と完全に分離可能。
- PAPER_FILL_MODE の有効値は instant / partial / never / reject の 4 種。その他は起動エラーとなる。
- ログ出力先ディレクトリ（LOG_DIR）やログレベル（LOG_LEVEL）を環境変数で調整可能。ファイル出力が必須の場合は実行ユーザーにディレクトリ作成権限があることを確認すること。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

以上。開発中の変更は Unreleased セクションに随時追加してください。