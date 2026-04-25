# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日・内容はソースコードから推測したものを記載しています。

リンク: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 監視・実行系の起動スクリプトを追加／整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止用フラグファイルを監視して安全に終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading 時はペーパートレード用の専用 DB を使用して本番 DB と分離。停止フラグ / PID 管理を実装。
- 環境設定管理とウィザード
  - config.py: .env 自動ロード（.env, .env.local）機能、堅牢な .env 解析、Settings クラスでアプリ設定をプロパティとして公開（デフォルト値・検証含む）。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
  - validate_config.py: .env や config/*.yaml を起動前に検証する CLI を追加。--strict オプションによる厳密モードをサポート。PyYAML の未インストールを許容して警告を出す設計。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py: stdout 出力 + 日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ロギング設定を実装。LOG_DIR / LOG_LEVEL による調整、ハンドラ二重設定防止、ファイル作成失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。権限不足等は警告でスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）・等金額 / スコア加重の重み計算を実装。スコア全0時のフォールバックログあり。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクター扱いやフォールバック挙動を明記。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）を実装。単元（lot_size）丸め、最大保有比率・aggregate キャップ、コストバッファを考慮したスケーリングロジックを実装。
  - portfolio/__init__.py で上記 API を公開。
- ペーパートレード用検証ツール
  - tools/paper_verification_report.py: ペーパートレード SQLite DB を読み取り、稼働率・注文成功率・送信率・レイテンシ（平均／最大／P95）等を集計してレポート出力。閾値を基に PASS/FAIL 判定を行う。コマンドライン引数で期間・DB を指定可能。
- 研究用ファクター計算の初期実装
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールを追加（モメンタム・MA200・ATR などの計算設計を含む）。（実装途中の箇所あり）

### Changed
- 実行環境分離の明確化
  - run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照する設計であり、監視は本番 DB を対象にする挙動を明示。
  - run_execution は設定に応じて paper_trading 用 DB に切り替え、本番 DB と完全分離する挙動を実装。
- 環境変数読み込みの順序・保護
  - config.py の自動ロードは OS 環境変数を保護しつつ .env/.env.local を読み込む（.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて自動ロードを無効化可能に。
- ロギング設定の出力先
  - 標準出力 (stdout) を主要なコンソールハンドラに使用（stderr ではない）。ログファイルは日次ローテーション、30 日保持をデフォルトとする。
- 例外／エラー処理の強化
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループを継続するように例外捕捉とログ出力を追加。
  - run_execution のスレッド実行で停止フラグを検知した際に engine.stop() を呼ぶ安全停止処理を追加。

### Fixed
- .env パーサの改善
  - config._parse_env_line() で export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなどを堅牢化。
  - config._load_env_file() でファイル読み込み失敗時に警告（warnings.warn）を出して継続するように変更。
- ログディレクトリ作成失敗時のフォールバック処理強化
  - logging_setup.setup_logging() でディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続するように改善。

### Notes / Known issues
- research/factor_research.py は一部実装が途中（ソースが途中で切れている箇所あり）。今後モメンタム等の詳細実装が必要。
- position_sizing の price が欠損（0.0）の場合の扱いについて TODO コメントあり（フォールバック価格の導入を検討）。
- process_priority.set_cpu_affinity() は権限やプラットフォームに依存するため、失敗時は警告を出してスキップする設計。運用環境により期待通り動作しない場合がある。
- run_monitoring が「本番 sqlite_path を使用」する点は意図的だが、開発中の誤使用を避けるためドキュメントや起動スクリプトで明示することを推奨。

---

## [0.1.0] - 2026-04-25

初回公開リリース — コードベース初期版として以下を含む:

### Added
- 基本ライブラリ構成
  - アプリケーションメタ情報（kabusys.__version__ = 0.1.0）
  - パッケージ構造: execution / monitoring / portfolio / research / tools / utils 等のモジュール群
- 実行用スクリプト群
  - run_execution.py, run_monitoring.py を含む起動エントリ
- 設定管理・検証ツール
  - config.py（Settings クラス、.env 自動ロード）
  - config_setup.py（対話ウィザードによる .env 作成）
  - validate_config.py（起動前チェック CLI）
- ロギング・プロセス制御
  - utils/logging_setup.py（統一ロギング設定）
  - utils/process_priority.py（優先度・CPU affinity）
- ポートフォリオ構築ライブラリ
  - portfolio_builder, risk_adjustment, position_sizing の実装と公開 API
- ペーパートレード検証ツール
  - tools/paper_verification_report.py（期間指定レポート出力）
- 研究用ファクター計算（初期）
  - research/factor_research.py（設計と開始実装）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- デフォルトで .env を Git 管理に含めないよう README 等で注意喚起（.env ファイルを絶対にコミットしない旨を config_setup のヘッダに記載）。

---

脚注:
- 上記はソースコードの内容・コメント・ドキュメント文字列から推測して作成した変更履歴です。実際のコミット履歴に基づくものではありません。必要であれば各変更点をコミット単位で分割した詳細な CHANGELOG を生成できます。