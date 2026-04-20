CHANGELOG
=========

すべての重大な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- なし（初期リリースに相当する変更は 0.1.0 に含まれます）

[0.1.0] - 2026-04-20
-------------------

Added
- 基本機能の初期実装を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイント。環境に応じて paper_trading 用の専用 SQLite を使う（data/paper_trading.db デフォルト）。プロセス優先度を高く設定し、停止フラグ検出・PID 管理・デーモンスレッドでのセッション実行を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 設定/起動支援
    - config.py: 環境変数/.env の自動読み込み機構と Settings クラスを追加。.env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。PAPER_FILL_MODE 検証、各種パス・閾値・フラグの取得メソッドを提供。
    - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。秘密値のマスク表示、選択肢サポート、保存プレビューを実装。
    - validate_config.py: 起動前設定検証 CLI。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml 存在および YAML パース検証、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等配分・スコア加重配分を実装。スコアが全て 0 の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
    - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元（lot_size）丸め、aggregate キャップ調整（スケーリング・残差処理）を実装。コストバッファ考慮あり。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティ。stdout 出力用 StreamHandler と 日次ローテートされたファイルハンドラ（デフォルト logs/、30 日保持）をルートロガーに設定。既存ハンドラのクリーンアップロジックを実装。
    - utils/process_priority.py: Windows / POSIX の差異を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを実装。アクセス権限や未対応 OS 時のフェールバックを考慮。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツール。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL を判定。期間フィルタ（--from/--to）と DB パス指定（--db）をサポート。P95 計算・NULL ハンドリングを実装。
  - リサーチ（計算）モジュール
    - research/factor_research.py: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を開始。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計（関数単位の計算ロジックを実装、残り実装は継続予定）。

Changed
- 初期設計上の注意点・運用方針を明記。
  - .env 自動ロードルールを定義（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を導入。
  - .env パーサ: export プレフィックスとクォート・バックスラッシュエスケープ、インラインコメントの取り扱いを実装し柔軟な .env 設定をサポート。
  - ログハンドラ: ファイル出力に失敗した場合は stdout のみで継続する堅牢性を確保。
  - 実行系と監視系で使用する SQLite パスの分離（paper_trading 用 DB を分ける）を明確化。

Fixed
- 環境値の検証・フォールバックを強化。
  - MONITOR_POLL_INTERVAL が不正（0 や負値、非数）の場合にデフォルトへフォールバックし、警告を出す処理を追加（run_monitoring）。
  - PAPER_FILL_MODE 等の列挙値検証を行い、不正値で明示的な例外を投げる（config.Settings）。
  - validate_config: PyYAML が未インストール時に YAML 検証をスキップし警告するようにして起動失敗を回避。
  - process_priority / set_cpu_affinity: 欠如したプラットフォーム定数や権限不足による例外をキャッチして運用継続するよう改善。

Security
- .env のハンドリングに関する注意を README 相当コメントへ追加（config_setup の出力ヘッダ内で .env を絶対にコミットしない旨を明記）。
- 設定検証で J-Quants / kabu API の必須環境変数が未設定の場合はエラーとして検出（validate_config）。

Notes / Known issues
- research/factor_research.py は継続実装中（ファイル末尾で未完の箇所あり）。今後のリリースでファクター計算関数を完成予定。
- position_sizing の価格欠損時（price が 0.0）のフォールバック価格戦略は未実装（TODO コメントあり）。欠損価格があるとエクスポージャーが過少見積もられる可能性があるため、運用時は入力データの完全性に注意してください。
- apply_sector_cap は "unknown" セクターをセクター制限の対象外とする設計。マスタにセクター情報が不十分な場合の挙動に注意。

貢献・開発
- 初期実装のため、ユニットテスト・ドキュメント・CI の整備は今後の優先課題です。README や運用ドキュメントの整備を継続してください。