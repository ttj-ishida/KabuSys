CHANGELOG
=========

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

※ この CHANGELOG は提供されたコードベースの内容から推測して作成しています。

Unreleased
----------

- いくつかの TODO / 未実装箇所を残しています（factor_research の実装途中、position_sizing の lot_size 拡張、価格フォールバックなど）。詳細は既知の問題セクションを参照してください。

0.1.0 - 2026-04-18
-----------------

Added
- 初回リリース。
- 基本アーキテクチャと起動スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用することを想定。停止フラグ（data/stop_requested.flag）と実行 PID 管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイント。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理:
  - config.py: .env の自動読み込み（.env, .env.local）・堅牢な行パーサ実装（クォート、エスケープ、コメント処理対応）、Settings クラスによる環境変数アクセスラッパーを追加。KABUSYS_ENV / LOG_LEVEL 等の値検証を実装。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
  - validate_config.py: 起動前に .env / config/*.yaml の妥当性をチェックする CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
- データベース / 分析:
  - DuckDB と SQLite の統合を想定したパス設定を追加（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。
  - 監視 DB 初期化関数（init_monitoring_db）を利用してテーブル存在を保証する呼び出しを追加（冪等性を想定）。
- ロギング / 運用ユーティリティ:
  - utils/logging_setup.py: ルートロガーの初期化ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。ログディレクトリ作成失敗時にフォールバックする処理あり。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度設定と CPU affinity を設定するユーティリティを追加（Windows / POSIX を吸収）。アクセス権限や未対応 OS の場合は警告でスキップ。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）と等金額・スコア加重配分ロジックを追加。スコアが全て 0 の場合のフォールバックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を追加。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）を追加。単元株（lot_size）丸め、aggregate cap によるスケールダウンと余剰キャッシュの再配分ロジックを実装。
  - portfolio/__init__.py: 上記関数を公開。
- ツール:
  - tools/paper_verification_report.py: ペーパートレード DB（デフォルト: data/paper_trading.db）から検証レポートを生成するスクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し PASS/FAIL を判定する。閾値はスクリプト内の定数で管理。
- 研究用:
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / MA200 / ATR / Volume 等の設計方針と定数を定義）。DuckDB を使った計算を想定。実装途中の箇所あり（ファイル末尾が途中で切れている旨の痕跡）。

Fixed / Resiliency improvements
- .env パーサの堅牢化: export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い、クォートなし時のコメント判定を実装。
- ログ出力可用性: ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールログのみで継続するように処理（運用環境での起動失敗を低減）。
- DB 初期化処理は冪等に実行する（init_monitoring_db を複数コンポーネントから呼べるようにしている）。
- 実行スクリプトは停止フラグ（data/stop_requested.flag）検知により安全に終了・停止できるようになっている。

Security
- .env を生成する際の注意書きを盛り込み、.env を絶対に Git にコミットしない旨をドキュメント（config_setup.py の出力）に明記。
- SECRET な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャンネルトークン等）は Settings 経由で直接取得する設計。

Documentation / Usage notes
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を上書き可能（不正値・0/負値はデフォルト 60 秒にフォールバックし警告を出す）。
- PAPER_FILL_MODE の有効値とバリデーションを実装（instant / partial / never / reject）。不正値は例外を送出。
- KABUSYS_ENV の有効値は development / paper_trading / live。live は追加の安全チェック（LINE 通知設定未設定や Kill Switch の設定）で警告を出す。
- validate_config CLI は PyYAML 未インストール時に YAML 検証をスキップして警告を出す。

Known issues / Limitations
- research/factor_research.py が途中で切れている（calc_momentum 実装の先頭部分が不完全）。ファクター計算の完全実装は未完了。
- position_sizing.py の将来的拡張点:
  - 銘柄ごとの lot_size マップを受け取る想定だが、現時点では全銘柄共通の lot_size を使用（TODO コメントあり）。
  - 価格が欠損（0.0）だった場合のフォールバック（前日終値や取得原価の採用）が未実装で、現在はスキップしてしまう旨の警告コメントあり。
- apply_sector_cap: "unknown" セクターは上限算定の対象外としているが、価格欠損によりエクスポージャーが過少評価されるリスクがある旨の注記あり。
- process_priority / set_cpu_affinity: 権限不足や未対応プラットフォームでは設定がスキップされログに警告が出る。運用時に適切な権限が必要。
- run_monitoring は監視 DB に対して環境にかかわらず本番 sqlite_path を使う仕様。意図しない DB に書き込まれる可能性を避けるため運用手順に注意が必要。
- tools/paper_verification_report の P95 算出はメモリ上で全値をソートして求める単純実装（大規模データでは性能面に注意）。

Migration / Upgrade notes
- 初回リリースのため互換性に関する変更点はありませんが、.env のキー名や期待される値（PAPER_FILL_MODE, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH 等）に注意してください。
- ペーパートレードと本番 DB は明確に分離されるように設計されています（settings.paper_sqlite_path を利用）。既存の DB レイアウトやファイルパスを変更する場合は validate_config で事前検証してください。

Contributing
- バグ報告・プルリクエストの際は、.env に秘密情報を含めずに minimal reproducible example を提供してください。
- factor_research の続きをはじめ、position_sizing の lot_size 拡張や価格フォールバック実装が貢献しやすい箇所です。