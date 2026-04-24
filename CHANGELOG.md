CHANGELOG
=========

すべての注目すべき変更履歴を記録します。フォーマットは "Keep a Changelog" に準拠しています。

注: 以下の内容は提示されたコードベースから推測して作成した変更点の要約です。

Unreleased
----------

### Added
- 環境設定・起動用スクリプト群を追加
  - run_monitoring.py: SystemMonitor ポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず production の sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db 想定）に記録することで本番 DB と分離。
- 設定管理とヘルパーを追加
  - config.py: .env 自動ロード（.env → .env.local、OS 環境変数の保護）、環境変数のパース（クォート・エスケープ対応、行末コメント処理）、Settings クラス（各種設定値取得と検証）を実装。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加（シークレットマスク、選択肢・デフォルト表示、.env 出力）。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パスの確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live の追加ガードなどを実行。--strict オプションで警告を FAIL 扱いにできる。
- 監視・実行周りの DB 初期化ユーティリティを統合
  - run_monitoring/run_execution 内で monitoring 用テーブルが存在することを保証する init_monitoring_db 呼び出しを行う（冪等）。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。stdout ストリーム出力 + 日次ローテートのファイルハンドラ（デフォルト logs/、30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定、CPU affinity 設定ユーティリティを追加。権限不足等の失敗は警告でスキップ。
- ポートフォリオ構築・リスク調整・ポジションサイジング機能を追加（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルをスコア順で選定する select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中上限適用 apply_sector_cap（既存保有のセクター比率を評価し、上限超過セクターの新規候補を除外）、市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知のレジームはフォールバックと警告）。
  - portfolio/position_sizing.py: allocation_method("risk_based"/"equal"/"score") に基づく発注株数算出、単元株丸め、1 銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した保守的見積り、余剰キャッシュによる端数調整ロジックなどを実装。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用 SQLite から各種指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシの P95 等）を算出しレポート出力する CLI を追加。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 latency <= 200 ms）に基づく PASS/FAIL 判定を行う。--from/--to/--db オプションをサポート。
- research/factor_research.py（ファクター計算基盤）を追加（モメンタム等の仕様、DuckDB 接続を受ける設計）。一部実装を含む（未完部分あり）。

### Changed
- パッケージのバージョン初期設定を追加: __version__ = "0.1.0"
- ログ出力の統一: すべての起動スクリプトで setup_logging を呼び出し、ログ管理を統一。

### Fixed / Hardened
- .env パースの堅牢化（config.py）
  - シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの無視、export プレフィックス対応などにより .env の柔軟な記述をサポート。
- run_monitoring のポーリング間隔取得で不正値を扱う際にフォールバックして ValueError を回避する処理を実装（警告ログを出力してデフォルト 60 秒を使用）。
- ログディレクトリ作成失敗時にファイルハンドラ作成をスキップするなど、運用環境差異に対するフォールバックを追加（logging_setup.py）。
- プロセス優先度・CPU affinity 設定で権限やプラットフォーム差により失敗した場合に例外を握りつぶして警告ログを出すようにして安定性を向上（process_priority.py）。

### Security / Operational notes
- config_setup により生成される .env ファイルは決して Git にコミットしない旨を明記（.env ヘッダコメント）。
- validate_config により本番環境（KABUSYS_ENV=live）での注意喚起（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）を追加。

0.1.0 - 2026-04-11
------------------

初回リリース想定（提示コードからの推測）

### Added
- 上記 Unreleased の主要機能群を初回リリースとしてまとめて公開:
  - 起動用スクリプト（run_monitoring, run_execution）
  - 設定管理（config, config_setup, validate_config）
  - ロギング / プロセス制御ユーティリティ（utils/logging_setup, utils/process_priority）
  - ポートフォリオ構築・リスク・サイジング（portfolio/*）
  - Paper Trading 検証ツール（tools/paper_verification_report）
  - research/factor_research の基盤
  - パッケージ __version__ = "0.1.0"

### Notes
- 監視（monitoring）は設計上「常に本番用の sqlite_path を参照する」点に注意。paper_trading 用データは run_execution 側で専用 SQLite を使用している（settings.is_paper 判定により分離）。
- .env 自動読み込み機構はプロジェクトルート（.git または pyproject.toml を基準）を探索して行うため、配布後の動作を想定した堅牢な実装になっている（プロジェクトルートが特定できない場合は自動ロードをスキップ）。
- 一部モジュール（research/factor_research）の実装は継続的に拡張される想定。

Deprecated
----------

- なし（初回リリース相当のため該当なし）。

Removed
-------

- なし。

Security
--------

- .env に機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を含める設計のため、config_setup の出力ヘッダで .env を絶対に Git にコミットしないよう明示。
- process_priority やログ設定での失敗は警告して処理を継続する設計。権限不足で期待どおり動作しない可能性があるので運用時は適切な実行ユーザー・権限を確認すること。

参考: 主要 CLI / 起動コマンド
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

この CHANGELOG は提示されたソースコードの内容から推測して作成したものであり、実際のコミット履歴とは異なる可能性があります。必要であれば、特定ファイル・変更点ごとにより詳細な追記を行います。