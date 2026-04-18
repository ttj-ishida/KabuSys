# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
フォーマット: https://keepachangelog.com/（日本語要約）

全般
- バージョン番号はパッケージ `kabusys.__version__ = "0.1.0"` にて管理。

## [0.1.0] - 2026-04-18

### Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
    - 停止フラグファイル（project/data/stop_requested.flag）を監視して安全停止。
    - Monitoring は実行環境にかかわらず本番用 SQLite パスを使用して起動。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（paper/live 切り替え対応）。
    - エンジンは別スレッドで run_session を実行し、停止フラグ（data/stop_requested.flag）で停止処理を行う。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイルを生成（data/execution.pid）。

- 設定・環境管理
  - config.py: 環境変数／.env 自動ロード機能を追加。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を読み込む（OS 環境変数が優先、.env.local は上書き）。
    - .env パースは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントを適切に処理。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、KABUSYS_ENV など）をプロパティ経由で取得。
    - 一部値はバリデーション（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
  - config_setup.py: 対話式の .env 設定ウィザードを追加。
    - 初期 .env 作成・更新を支援。シークレット項目はマスク表示。最終的に .env を書き出す機能。
    - デフォルト値や選択肢の提示、保存前の確認を含む。

- 設定検証 CLI
  - validate_config.py: 起動前チェックツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML が無い場合はスキップして警告）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギングセットアップを提供。
    - ルートロガーに StreamHandler(STDOUT) と TimedRotatingFileHandler（日次、30日分保持）を設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順序（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX(Linux/macOS/FreeBSD) の差分を吸収して nice / priority を設定。
    - set_cpu_affinity による CPU affinity 固定機能を追加（例外発生時は警告でスキップ）。

- Portfolio ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が0の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有比率が閾値を超える場合、そのセクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未知レジームは警告後 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に対応した発注株数算出。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケール調整、cost_buffer を用いた保守的見積りなどを実装。
    - スケールダウン時は残差を lot 単位で再配分するロジックを持つ。

- 解析・研究ツール
  - research/factor_research.py（ファクター計算モジュール）を追加（モメンタム、ボラティリティ、バリュー等の計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いてファクターを算出する設計（純粋関数）。
    - （注）ファイル末尾で関数の実装が続く設計になっているため、必要に応じてさらなる関数実装が想定される。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - デフォルト DB path は 環境変数 `PAPER_TRADING_SQLITE_PATH` または data/paper_trading.db。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計してレポート出力。
    - Pass/Fail 判定を行う閾値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）を定義。
    - 日付フィルタ（--from / --to）に対応。

### Changed
- なし（初回リリース）

### Fixed
- _get_poll_interval() の挙動: 環境変数値が不正（非数値や 0 以下）の場合にデフォルト値へフォールバックし、警告を出す実装を導入（run_monitoring.py）。

### Security
- .env の自動読み込みはデフォルトで有効。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できる旨を明記。
- config_setup.py は .env を生成するが、生成された .env は決して Git にコミットしないことを README/ファイルヘッダに明記。

### Notes / Migration
- 起動スクリプトを利用する際は必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を .env または OS 環境に設定してください。`python -m kabusys.validate_config` で事前検証を推奨します。
- Paper Trading を利用する場合は KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に分離されます（本番 DB と完全に切り離される構成）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみとなります。

---

（今後のリリースでは各モジュールの単体テスト追加、factor_research の完成、さらに CLI/ドキュメントの充実を予定しています。）