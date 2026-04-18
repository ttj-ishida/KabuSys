# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  

バージョン番号はパッケージの __version__ を基にしています。

## [Unreleased]
- なし（今後の変更をここに記載してください）

## [0.1.0] - 2026-04-18
初回リリース。自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築、検証ツールおよび設定周りのCLIを実装しました。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。環境変数 KABUSYS_ENV に応じて paper_trading モードでは専用の paper DB（data/paper_trading.db）を使用する挙動をサポート。停止フラグ（data/stop_requested.flag）と PID ファイル管理を備える。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py: 環境変数/`.env` の読み込み・解釈機能を実装。自動ロード（.env / .env.local）ロジック、.env の行パース（クォートやエスケープ・コメント対応）、必須キー検査ユーティリティ、Settings クラス（各種プロパティ：DB パス、KABUSYS_ENV 判定、paper_trading 用設定、しきい値 等）を追加。
  - config_setup.py: 対話式ウィザードで `.env` を生成/更新する CLI を実装（secret 値マスク表示・確認・保存機能）。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを実装。--strict オプションで警告を FAIL 扱いにできる。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在チェック、YAML パース検証（PyYAML の有無に応じてスキップ）や本番向け安全ガードを提供。
- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）を用いた統一ログ設定ユーティリティを実装。ログディレクトリ作成失敗時はファイル出力をスキップするフォールバック実装。
  - utils/process_priority.py: Windows/Linux/macOS を抽象化したプロセス優先度設定と CPU affinity 設定を実装。許容レベル "high"/"normal"/"low"、および cpu_count によるコア固定機能を提供。権限不足時は警告ログでフォールバック。
- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py: 銘柄候補選定（スコア・ランクに基づくソート）、等金額配分・スコア加重配分関数を実装（スコアがゼロ時は等配分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバック処理あり）。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数計算を実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、per-stock 上限・aggregate 上限（available_cash）基づくスケーリング、cost_buffer（取引コスト見積り）考慮などを含む。
  - portfolio/__init__.py: 上記関数群をエクスポート。
- Paper Trading 向けツール
  - tools/paper_verification_report.py: Paper Trading データベースから期間指定レポートを生成するスクリプトを実装。稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、平均/最大/P95 レイテンシ等を集計して PASS/FAIL を判定する閾値（稼働率 >=99% 等）を内包。--from / --to / --db オプションをサポート。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）。
- DuckDB 統合
  - DuckDB 接続を ExecutionEngine / モニタリング / リサーチ処理から使用するための接続コードを実装（Settings.duckdb_path で指定）。
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- ロギングの挙動
  - StreamHandler を stdout に出力するように統一（cron/タスクランナーで stdout/stderr を一本化しやすくするため）。ログディレクトリ作成に失敗した場合はファイルハンドラ作成をスキップしてコンソールのみで継続するフォールバックを導入。
- 環境変数ロードの優先順位
  - OS 環境変数 ＞ .env.local ＞ .env の順で読み込む仕様を明確化し、OS 環境変数を protected として .env.local による上書きを制御。
- 設定検証のメッセージ性向上
  - validate_config で INFO/WARNING/ERROR を整備し、環境が live の場合の追加チェック（LINE 設定、KILL_FLAG_CLEAR_ON_START）を導入。

### Fixed / Robustness
- .env パーサーの耐久性向上
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、不正行の無視などを実装して .env のパースを堅牢化。
- 実行時のフェイルセーフ
  - 各種起動スクリプトで DB 接続後の finally ブロックにより接続を確実にクローズするようにし、ポーリングループ内の例外は catch してログ出力後に次ポーリングへ継続するよう変更（監視ループの安定化）。
- 環境変数値検証
  - MONITOR_POLL_INTERVAL の不正値（非整数、0 以下）を検出して警告を出しデフォルト値にフォールバックする処理を追加。
  - Settings.paper_fill_mode のバリデーションを実装（有効値: instant/partial/never/reject）。無効な値で ValueError を投げる。

### Documentation / CLI UX
- config_setup.py に対話式の説明・デフォルト・現在値表示・シークレットマスク・保存確認フローを実装。生成される .env テンプレートヘッダに注意書き（Git にコミットしない）を付与。
- validate_config.py と config_setup.py に CLI 用のヘルプ・引数説明を追加。

### Internal / Tests / TODO notes
- research/factor_research.py にてファクター計算の設計と一部実装（モメンタム等）を追加。実装中の関数や TODO コメントが残されています（今後の拡張点: データ不足ハンドリング、SQL の最適化など）。
- position_sizing.calc_position_sizes にて将来的な拡張のための注記を追加（銘柄別 lot_size を導入する設計など）。

### Security
- 秘密情報の取り扱いに関する注意を README/テンプレート（.env ファイルヘッダ）で明示（.env を Git にコミットしないこと）。

---

注:
- 上記はコードベースから推測可能な変更点・実装内容に基づく CHANGELOG です。実際のリリースノートやコミット履歴に応じて適宜調整してください。