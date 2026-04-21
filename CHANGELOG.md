# Changelog

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお本CHANGELOGは、提供されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

（今後のリリースに向けた変更点の記録領域）

---

## [0.1.0] - 2026-04-21

最初の公開リリース相当。システム全体の起動スクリプト、設定管理、環境整備ツール、運用向けユーティリティ、ポートフォリオ構築/サイズ計算ロジック、ペーパートレード検証レポート等を収録。

### Added
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。環境（KABUSYS_ENV）に応じて paper_trading 用 DB を分離して使用。停止フラグの検出・処理、デーモンスレッドでエンジン実行、PID ファイル指定などをサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止用フラグファイルによる終了処理を実装。
- 設定・環境管理
  - config.py: 環境変数・.env の自動ロード機能を追加（プロジェクトルートの検出に .git / pyproject.toml を使用）。.env と .env.local の読み込み順を実装（OS 環境を保護して上書き回避）。Settings クラスを通じて各種設定をプロパティで取得可能に。
  - config_setup: 対話形式の .env 作成/更新ウィザードを追加。シークレット値のマスク表示、デフォルト値、説明文、保存処理をサポート。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数やパス、config/*.yaml の存在・パース検証（PyYAML がない場合はパース検証をスキップ）、--strict オプションを実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。コンソール(stdout) と日次ローテーション（TimedRotatingFileHandler）でのファイル出力を一元化。ログディレクトリ自動作成・失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows / POSIX を透過するプロセス優先度設定（および CPU affinity 設定）ユーティリティを追加。アクセス権限エラー等は警告でスキップする堅牢設計。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分・スコア加重（calc_equal_weights, calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 各銘柄の発注株数を計算する calc_position_sizes を実装（risk_based / equal / score の割当方式、単元株丸め、aggregate cap スケーリング、cost_buffer を用いた保守的見積り、残差を考慮した追加配分ロジック等）。
  - portfolio.__init__: 上記機能を公開 API としてエクスポート。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を参照し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等の指標を算出してレポートを出力するスクリプトを追加。しきい値による PASS/FAIL 判定を実装。
- その他ユーティリティ・モジュール
  - monitoring 側 DB 初期化ヘルパー経由で監視テーブルの冪等な初期化処理を呼び出すインテグレーションを追加（起動スクリプトから利用）。
  - package version 定義: kabusys.__init__ に __version__ = "0.1.0" を追加。

### Changed
- 環境変数読み込みの挙動
  - プロジェクトルート検出（.git / pyproject.toml）に基づいて .env 自動ロードを行うように変更。読み込み順は OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト等で利用）。
- run_monitoring/run_execution の DB 接続方針
  - run_monitoring は監視用 DB に対して環境に依存せず production 用 sqlite_path を使用する方針を明示。
  - run_execution は paper_trading 環境時に専用の paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離するように変更。
- ログ設定の既定値と挙動
  - ログ出力はデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）を併用するよう統一。
  - 既にハンドラが設定されている場合は一旦すべてクリアしてから再設定することで二重出力を防止。
- .env パーシングの堅牢化
  - クォートあり/なしの値取り扱い、バックスラッシュエスケープ、コメントの扱い（クォート内の # は無視、非クォートの # は前が空白の場合にコメント扱い）に対応。
  - export KEY=val 形式に対応。
  - .env 読み込み時に OS 環境変数を保護する（既存変数は override しない / override=True でも protected set は上書きしない）。

### Fixed
- .env 読み込みでの既存 OS 環境変数上書き問題を回避する保護機能を追加。
- process_priority / set_cpu_affinity で権限不足や未対応 OS の場合に例外で止めず警告に置き換える改善。
- position_sizing の aggregate スケーリング時に残差処理で順序を安定化し、端数処理のバグを軽減（remainders を用いた追加配分ロジックを実装）。
- validate_config が PyYAML 非インストール環境で落ちる問題を回避（警告出力して YAML パース検証をスキップ）。

### Security
- .env ファイル生成ウィザードで生成されるファイルに対して「.env は絶対に Git にコミットしないこと」の警告を明記。

### Known issues / Notes
- research/factor_research.py（ファクター計算モジュール）は採用設計を記載した上で実装が途中（ファイル末尾が途中で切れている）になっている可能性があるため、実運用前に実装完了とテストが必要。
- position_sizing の price 欠損時の扱いや、apply_sector_cap の price フォールバック（前日終値等）については TODO コメントが残っており、将来の改善余地あり。
- 一部モジュールは外部ライブラリ（psutil, duckdb, PyYAML 等）に依存するため、実行環境でのインストールと権限設定（プロセス優先度変更など）に注意が必要。

---

（以降のリリースでは、各機能の追加／修正ごとにセクションを追記してください）