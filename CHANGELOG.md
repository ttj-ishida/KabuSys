CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-25
------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行用スクリプトを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて本番／ペーパートレードを切り替え、専用の SQLite（ペーパートレード時は data/paper_trading.db）と DuckDB を利用してエンジンを起動する。プロセス優先度設定、PID ファイル、停止フラグ監視、スレッド実行をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検出でループを終了。監視用 DB 初期化と DuckDB 接続を行う（監視は環境に関わらず本番 sqlite_path を使用）。
- 設定関連 CLI を追加:
  - config_setup.py: 対話式 .env ウィザード（.env の初期生成／更新）。シークレット項目はマスク表示。生成された .env のテンプレートを出力。
  - validate_config.py: 起動前検証 CLI。.env と config/*.yaml、DB パス、必須環境変数や本番環境ガードをチェック。--strict オプションで警告を FAIL 扱いにできる。
- ツールを追加:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成。稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計して PASS/FAIL 判定を行う。
- ポートフォリオ構築ライブラリを追加（純粋関数群、DB 参照なし）:
  - portfolio_builder: 候補抽出・等重み／スコア重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用とレジーム乗数計算（apply_sector_cap, calc_regime_multiplier）。
  - position_sizing: 株数算出ロジック（risk_based / equal / score をサポート）、単元株丸め、集計キャップによるスケールダウン、コストバッファ考慮。
- 研究用モジュール（骨格）を追加:
  - research/factor_research.py: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、流動性、バリュー等）用の設計と実装開始（calc_momentum など）。
- 共通ユーティリティを追加:
  - utils/logging_setup.py: stdout ストリームと日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定。ログレベル・ログディレクトリの解決順を実装し、ディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - utils/process_priority.py: Windows / POSIX の差を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティ。アクセス権や未対応環境時に警告を出す。
- 環境設定読み込み／管理:
  - config.py: プロジェクトルートの自動検出（.git / pyproject.toml を基準）および .env 自動読み込み（.env → .env.local、OS 環境変数保護）。.env のパーサを改良（export 形式、クォート／エスケープ、インラインコメント処理をサポート）。Settings クラスに各種プロパティと妥当性チェック（PAPER_FILL_MODE 等）を追加。

Changed
- 設計方針:
  - ポートフォリオ／ポジションサイズ／リスク調整は副作用なくメモリ内で完結する純粋関数として実装。外部 DB や API への依存を排除しユニットテストを容易に。
  - ロギングは各起動スクリプトから統一された setup_logging() を呼ぶことで一貫したログ出力に統合。
- Execution/Monitoring 起動ロジック:
  - 起動時にプロセス優先度を最初に高にセットする処理を追加（set_process_priority("high")）。
  - run_monitoring は監視用テーブルの初期化（init_monitoring_db）を必ず行うようにして監視テーブルの存在を保証（冪等）。
- validate_config:
  - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出すようにして、依存関係がなくても最低限の検証ができるように変更。
  - KABUSYS_ENV=live 時に本番向けの安全ガイド（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START 設定など）を警告するチェックを追加。

Fixed
- .env パーサの堅牢化:
  - export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメント扱いなどを正しく処理するよう改善。不正行は無視。
- MONITOR_POLL_INTERVAL の扱い:
  - ポーリング間隔が無効（0 以下や非整数）の場合に警告を出してデフォルト（60 秒）にフォールバックするように実装し、time.sleep の ValueError を回避。
- Paper Trading 分離:
  - ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を明示的に分離し、テスト／検証用の操作が本番 DB に影響しないようにした。

Security
- config_setup の出力ではシークレット項目をマスクして表示（保存前の確認でもマスク表示）。
- .env ファイル生成ドキュメントに「.env を絶対に Git にコミットしないこと」を明示。

Notes / Known issues
- research/factor_research.py は一部実装が続いており（ファイル最終部で cut-off）、関数群は今後拡張予定。現状は設計と一部実装が含まれている。
- position_sizing の価格欠損（price が 0.0）の場合に過少見積りが生じる可能性がある旨の TODO コメントあり。将来的にフォールバック価格の導入を検討。
- process_priority や set_cpu_affinity は権限不足やプラットフォーム非対応時に設定がスキップされる可能性がある（警告ログにて通知）。

Breaking Changes
- なし（初回リリース）。

Acknowledgements
- 本 CHANGELOG はソースコードの現状から推測して作成しています。実際の運用上の注意点・履歴管理はプロジェクトの運用ポリシーに従ってください。