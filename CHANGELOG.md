CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーション骨格を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0。
- 起動スクリプト / 実行単位を追加。
  - run_execution: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading 時は専用のペーパートレード DB を使用し MockBrokerClient を利用する設計を組み込み。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイルで安全に終了可能。
- 設定管理を実装。
  - config.Settings: 環境変数ベースの設定取得ラッパーを提供（パスや閾値、API トークン等のプロパティを含む）。
  - 自動 .env ロード機能: プロジェクトルート（.git / pyproject.toml を探索）を検出して .env / .env.local を適切な優先度で読み込む（OS 環境変数の保護機能付き）。
  - 強力な .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い等に対応）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の検証ロジックを実装（不正値は例外）。
- 対話式設定ウィザードを追加（config_setup）。
  - .env の初期作成／更新を支援する CLI ウィザードを実装。秘密値のマスク表示・選択肢サポート・確認保存機能あり。
- 設定検証コマンドを追加（validate_config）。
  - 必須環境変数やパス、config/*.yaml の存在とパース（PyYAML 利用時）を検証。--strict オプションで警告をエラー扱いにできる。
- ロギング整備ユーティリティを追加（utils.logging_setup）。
  - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション：30日保持）をルートロガーに設定する共通ユーティリティを導入。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度 / CPU affinity ユーティリティを追加（utils.process_priority）。
  - Windows / POSIX を吸収する set_process_priority と set_cpu_affinity を提供。権限不足等は警告を出して安全にフォールバック。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights)。
  - risk_adjustment: セクター上限適用(apply_sector_cap)、市場レジーム乗数(calc_regime_multiplier)。
  - position_sizing: 発注株数計算(calc_position_sizes)。risk_based / equal / score の割り当て方式、lot_size 単位丸め、aggregate cap（スケールダウン）と残差処理を実装。
- Execution 系依存コンポーネントのスケルトンを追加。
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の組み立てと起動フロー（スレッドでの実行、PID ファイル管理、停止フラグ監視）。
- 監視 DB 初期化ユーティリティを追加（monitoring.monitoring_db の init_monitoring_db を呼び出す利用）。
- Paper Trading 検証ツールを追加（tools.paper_verification_report）。
  - ペーパートレード SQLite DB から稼働率、注文成功率、送信率、P95 レイテンシなどを集計してレポート出力。デフォルト基準値（稼働率 99%、成立率 90% 等）による PASS/FAIL 判定を実装。CLI 引数で期間指定・DB 指定可能。
- 研究用ファクタ計算モジュールを追加（research.factor_research の骨格）。
  - モメンタム、MA200 乖離、ATR、流動性等の計算方針と定数を定義。DuckDB を使用して prices_daily/ raw_financials を参照する設計（実装は継続）。

Changed
- ログ関連の挙動:
  - stdout を使用する StreamHandler をルートロガーに追加（stderr ではなく stdout を採用）。これにより cron 等で stdout/stderr を一元管理しやすく。
  - 既存ハンドラがある場合は一旦 flush/close してから置き換えることで二重ハンドラ設定を防止。
- DB 接続の扱い:
  - run_monitoring は KABUSYS_ENV に関わらず「監視用の本番 sqlite_path」を使用する設計とした旨をログ注記（監視は一貫した DB を参照するため）。
  - run_execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離。
- .env 読み込み優先順位を明確化:
  - OS 環境変数 > .env.local > .env の順で読み込む。既存の OS 環境変数は保護される（protected set）。

Fixed / Robustness
- 環境変数パーシング改善:
  - export プレフィックス、引用符付き文字列内のバックスラッシュエスケープ、インラインコメントの処理などに対応して .env のパース耐性を向上。
- ログディレクトリ作成失敗時のフォールバックを追加:
  - ディレクトリ作成やファイルハンドラ生成に失敗しても、StreamHandler（コンソール出力）で継続動作するようにして起動失敗を防止。
- process_priority / cpu_affinity の例外ハンドリングを強化:
  - psutil の AccessDenied 等に対して警告ログを出し安全にスキップするようにした（権限のない環境でも動作継続）。
- ExecutionEngine 起動時の停止フラグ処理:
  - 起動直前に停止フラグが存在する場合は起動せずに安全終了するようにし、実行中は定期的にフラグを監視してエンジンを停止可能に。

Documentation / UX
- config_setup の対話 UI を整備:
  - 秘密値はマスク表示、選択肢チェック、途中キャンセル時の挙動（変更を保存しない）などを実装。生成される .env にヘッダコメントを付与して Git へのコミット禁止を明示。
- validate_config の出力を整理:
  - INFO / WARNING / ERROR を分類して出力。--strict フラグで警告を失敗扱いにできる。
- tools.paper_verification_report のレポート形式を整備:
  - 指標表示、閾値比較、FAIL 理由の一覧出力を実装。

Notes / Known issues
- research.factor_research はファイル末尾で実装途中（コメントでの設計方針は含む）。完全実装は今後のリリースで追加予定。
- 一部の TODO コメント（例: position_sizing の価格フォールバック、lot_size の銘柄別対応）が残っているため将来的な改善余地あり。
- PAPER_FILL_MODE の不正値は Settings で ValueError を投げるため起動前に validate_config でチェックすることを推奨。
- .env ファイルは機密情報を含むため絶対にリポジトリへコミットしないこと（config_setup にも同旨の注意コメントあり）。

Security
- .env ファイルの扱いについて再度注意喚起:
  - config_setup に .env を絶対に Git にコミットしない旨のヘッダを追加。
  - 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや CI 向け）。

今後の予定（未実装 / 予定）
- research.factor_research の完全実装（各ファクター算出 SQL / DuckDB 統合）。
- ExecutionEngine 周りの詳細な単体テストと BrokerClient の実装強化（実ブローカ連携のテスト等）。
- ログのメトリクス収集やより高度な監視アラート連携（LINE 通知の活用自動化）。
- 単元テスト、CI 設定、型の強化（mypy 等）の追加。

----- 

注: この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際の変更履歴やコミットログに基づくものではありません。