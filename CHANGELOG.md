Keep a Changelog
=================

すべての変更は "Keep a Changelog" の形式に従って記録しています。  
以下の内容は提示されたソースコードから推測して作成した変更履歴です（コミット履歴ではありません）。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 実行用エントリポイントを追加/整備
  - run_execution.py: ExecutionEngine を起動するランナーを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）が使われ、MockBrokerClient 経由で発注を分離できる。停止フラグ（data/stop_requested.flag）検出および execution.pid の管理を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理・支援ツール
  - config.py: .env の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。多くの設定（DB パス、ログレベル、環境判定、paper_trading 関連等）をプロパティで提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。必須/任意/シークレット項目を扱い、.env 書き出しをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV/LOG_LEVEL の妥当性・DB パスや config/*.yaml の存在／YAML パース検証（PyYAML があれば）等をチェック。--strict モードをサポート。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計し Pass/Fail 判定を出力。PAPER_TRADING_SQLITE_PATH を参照可能。
- ポートフォリオ構築関連（純関数ライブラリ）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）と重み計算（等金額・スコア重み）を追加。スコア全体がゼロの場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装。risk_based、equal、score の各 allocation_method に対応。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、手数料/スリッページ想定の cost_buffer を考慮。
- ユーティリティ
  - utils/logging_setup.py: 統一的ロギング設定ユーティリティを追加。コンソール出力（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR 解決、ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定を追加（Windows / POSIX を吸収）。set_process_priority/set_cpu_affinity を提供。
- リサーチ（途中実装）
  - research/factor_research.py: モメンタム等のファクター計算モジュールの骨組みを追加（DuckDB 経由で prices_daily / raw_financials を参照する想定）。（ソースは途中で切れているが設計方針と定数が整備済み）

Changed
- .env パーサーを強化（config._parse_env_line）
  - export キーワード対応（export KEY=val）。
  - シングル/ダブルクォート値のエスケープ解釈対応（バックスラッシュ）。
  - クォートなし値のインラインコメント扱いルールを改善（'#' の扱いを前後の空白で判定）。
  - _load_env_file にて override/protected 機能を導入し、OS 環境変数を保護しつつ .env.local で上書きできる仕組みに。
- Settings のバリデーションを明確化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の有効値チェックを追加。無効値は ValueError を送出するように変更（誤設定の早期検出）。
- ログ出力における標準出力の利用
  - ログのコンソールハンドラは stderr ではなく stdout を使用（cron/task scheduler でのリダイレクト配慮）。
- run_monitoring / run_execution のプロセス優先度設定
  - 起動直後に set_process_priority("high") を呼び出し、重要プロセスの優先度を上げるように変更。

Fixed
- 安全な DB 初期化呼び出し
  - init_monitoring_db() を実行して監視テーブルの存在を保証（冪等的に呼び出し可能）。
- 実行停止ロジックの整理
  - ストップフラグ（data/stop_requested.flag またはプロジェクト内 data ディレクトリの同等ファイル）検出により、monitoring と execution の両方で外部から安全に停止できるように実装。

Security
- シークレット値の取り扱い改善
  - config_setup の表示や保存においてシークレット項目はマスク表示（コンソール上）。ただし .env 自体は平文で保存する点は明示。

Potential Breaking Changes / Notes
- Settings のプロパティは不正な環境変数値に対して ValueError を送出するため、従来どおり曖昧な設定を許容していたコードでは起動時に例外となる可能性があります（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）。
- run_monitoring は「監視用 DB」を環境にかかわらず settings.sqlite_path（本番想定のパス）で開く設計のため、paper_trading と本番 DB の分離を期待する運用では注意が必要です（run_execution は paper_trading 時に別 DB を使用するよう配慮済み）。
- research/factor_research.py は途中で実装が切れているため、関数群をそのまま利用するには追加実装が必要。

その他
- パッケージバージョンを __version__ = "0.1.0" として設定。

--- 
（この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴・作者コメントに基づくものではありません。必要であればコミット単位での詳細な差分を反映した CHANGELOG を作成します。）