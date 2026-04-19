Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ のガイドラインに従って記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

[Unreleased]
------------

（現状なし）

[0.1.0] - Initial release
-------------------------

Added
- 基本パッケージと CLI を追加
  - 実行用エントリポイント:
    - run_execution.py: ExecutionEngine 起動用スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用し、Broker クライアントをファクトリ経由で生成してエンジンをバックグラウンドスレッドで実行する。停止フラグの検出と PID ファイル管理に対応。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番用 sqlite_path を使用。
  - 設定関連:
    - config.py: 環境変数/ .env 読み込みのユーティリティと Settings クラスを追加。プロジェクトルートの自動検出、.env/.env.local の自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）、各種検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加（デフォルト値、秘密値マスク、保存確認付き）。
    - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML 未導入時のフォールバックや DB パスの親ディレクトリ存在チェック、live 環境用の追加注意喚起などを実装。
  - ロギング/プロセス管理:
    - utils/logging_setup.py: ルートロガーの初期化ユーティリティを追加（コンソール stdout と 日次ローテーションのファイルハンドラ）。ログディレクトリ自動作成失敗時のフォールバック対応、既存ハンドラのクリーンアップ処理、ログレベル解決順を実装。
    - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）、および CPU アフィニティ設定ユーティリティを追加。権限不足等は警告ログでスキップする安全策を実装。
  - ポートフォリオ構築関連（純粋関数群）:
    - portfolio/portfolio_builder.py: シグナルから候補選定と等金額・スコア加重重み計算を実装。スコアが全て 0 の場合等金額にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック処理を行う。
    - portfolio/position_sizing.py: 各銘柄の発注株数算出ロジックを実装（risk_based / equal / score）。単元株（lot）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer を使った保守的見積り、残差処理による追加配分ロジックを備える。
    - portfolio/__init__.py: 上記関数群をエクスポート。
  - ツール:
    - tools/paper_verification_report.py: ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、閾値に基づき PASS/FAIL を出力する CLI。--from/--to/--db オプションを提供。
  - 研究用モジュール（骨組み）:
    - research/factor_research.py: DuckDB を用いたファクター計算の骨組みを追加（モメンタム、MA200乖離、ATR、流動性等の指標算出を意図）。（実装途中の関数あり）

Changed
- 初期リリースに伴う各種設計決定を文書化（コード内 docstring と注記）
  - ログは stdout を主要にし、ファイルハンドラは補助（ログディレクトリ作成に失敗した場合はコンソールのみで継続）。
  - .env 読み込みは OS 環境変数を保護する仕組みを導入（.env.local で上書き可、override と protected の概念）。
  - run_monitoring は環境にかかわらず「監視用 DB」は本番 sqlite_path を使用する仕様を明示。
  - run_execution は paper_trading 環境時に専用 DB（PAPER_TRADING_SQLITE_PATH）を使用することで本番 DB と完全分離。

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- 環境変数の対話式入力でシークレット値はマスク表示（config_setup の出力/確認時）。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能（安全策）。

Notes / Known limitations
- research/factor_research.py は一部実装途中（ファイル末尾で切れている箇所あり）。完全なファクター算出は今後追加予定。
- portfolio/risk_adjustment.apply_sector_cap は価格データが欠損（0.0 等）の場合、エクスポージャーが過少見積りされる可能性があり、コメントにて将来的なフォールバック価格対応を示唆している。
- process_priority や cpu_affinity は権限不足や未対応 OS の場合に警告でスキップする実装。期待する動作を得るには適切な権限が必要。
- validate_config の YAML 検証は PyYAML がインストールされていない場合スキップされる（その際は警告を出力）。

作者注
- このリリースは機能の骨格を揃えた初版です。今後、研究モジュールの完成、テストカバレッジの拡充、エラーハンドリング・ロギングの強化、そして実運用向けの監視アラート・通知（LINE 連携）の追加実装を予定しています。