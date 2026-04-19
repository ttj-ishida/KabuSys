CHANGELOG
=========

この変更履歴は「Keep a Changelog」形式に準拠しています。  
Semantic Versioning に従うことを意図しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回公開: KabuSys v0.1.0 を追加。
- 実行用エントリポイントを追加:
  - run_execution.py: ExecutionEngine の起動スクリプト（スレッドで実行、停止フラグ / PID 管理あり）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL による上書き対応）。
- 環境設定関連 CLI を追加:
  - config_setup.py: 対話式 .env 作成/更新ウィザード（.env のテンプレート生成、シークレットマスク表示）。
  - validate_config.py: .env や config/*.yaml の起動前検証ツール（--strict オプションあり）。
- Paper Trading 分離:
  - Execution 起動時に KABUSYS_ENV=paper_trading の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用する設計。BrokerClientFactory により MockBrokerClient を利用する想定で本番 DB と完全に分離。
- 監視 / モニタリング:
  - monitoring 用 DB 初期化（init_monitoring_db の呼び出し）により監視テーブルの存在を保証（冪等）。
  - 監視ループはプロジェクト直下の data/stop_requested.flag を監視して安全終了。
- 分析・レポート:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを出力し、閾値判定で PASS/FAIL を判定。
- ポートフォリオ構築モジュール（純粋関数）を追加:
  - portfolio_builder.py: 候補選定 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights。
  - risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier。
  - position_sizing.py: 株数決定ロジック calc_position_sizes（risk_based / equal / score に対応、単元株丸め、aggregate cap スケーリング、手数料/スリッページ用 cost_buffer）。
  - portfolio/__init__.py で上記関数群を公開。
- ユーティリティ:
  - utils/logging_setup.py: stdout ストリーム + 日次ローテート（TimedRotatingFileHandler）による統一ログ設定。LOG_DIR 未作成時のフォールバックとログレベル解決。
  - utils/process_priority.py: Windows/Linux/macOS の差を吸収するプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）と CPU affinity 設定。権限不足時に安全にスキップ。
- 設定読み込み・パース:
  - config.py: .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml 基準）、export KEY= 形式対応、シングル/ダブルクォート内のエスケープ処理、行コメント処理など堅牢な .env パーサ実装。環境変数アクセス用 Settings クラスを提供。
- 研究用ファクター計算（プロトタイプ）:
  - research/factor_research.py: DuckDB 接続を使った定量ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。calc_momentum の実装が着手されている（注: ファイル末尾で実装途中の可能性あり）。

Changed
- ロギング動作:
  - ログハンドラの二重登録を防止するため、既存ハンドラを一度 flush/close のうえ削除してから再設定する。
  - StreamHandler は stdout を使用（cron/スケジューラ利用時のリダイレクト互換のため）。
- 環境変数デフォルト/解決順:
  - .env 自動ロードは OS 環境変数を優先し、.env.local を .env の上から上書き（OS 環境変数は protected）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応（テスト向け）。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応して誤読を低減。
- ログディレクトリ作成失敗時のフォールバック:
  - ディレクトリ作成やファイルハンドラ作成に失敗しても stdout ログは継続されるように保護。
- ポーリング間隔の安全処理:
  - MONITOR_POLL_INTERVAL が不正（数値でない、0 以下等）の場合にデフォルト値へフォールバックし、警告出力するよう修正。
- DB 初期化の冪等性:
  - monitoring DB 初期化処理を呼び出すことで、監視テーブルが存在しない状態でも起動時に自動生成されるようにした（重複して呼んでも安全）。

Security
- 重要なシークレット（J-Quants トークン、kabu API パスワード）は Settings 経由で必須チェックを行い、未設定時に起動前に検出されるようにした（validate_config の検証で警告/エラー表示）。

Notes / Known issues
- research/factor_research.py の一部（calc_momentum の実装）は途中で終端している（ファイル末尾に不完全な行が存在）。追加実装・テストが必要。
- position_sizing.calc_position_sizes 内で価格が欠損（0.0 や None）の場合にエクスポージャが過少評価される可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバック処理を検討。
- run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」という設計になっているため、paper_trading と完全に分離したい場合は運用上の注意が必要。

Breaking Changes
- なし（初回リリースのため該当なし）。

Authors
- KabuSys 開発チーム（コードベースから推測して作成）

--- 

（補足）この CHANGELOG は渡されたコード内容から機能・設計意図を推測して記載しています。実際のリリースノートや運用ドキュメントは開発履歴（コミットログ）やリリースマネージャの記録に基づいて調整してください。