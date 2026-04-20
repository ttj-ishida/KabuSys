# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog 準拠の形式で記載しています。

## [Unreleased]

### Added
- factor_research モジュールにモメンタム等のファクター計算の実装を追加（作業中）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
  - 注: 現在のスナップショットでは calc_momentum の実装が途中で中断されています（ファイル末尾が未完）。

### Notes / TODO
- research/factor_research の未実装箇所を完了する必要があります。
- portfolio/position_sizing: 将来的に銘柄ごとの単元（lot_size）をマスタ化する予定（現状は全銘柄共通の単元を前提）。
- portfolio/risk_adjustment: price 欠損時のフォールバック（前日終値や取得原価など）を導入することを検討中。

---

## [0.1.0] - 2026-04-20

初回リリース。主要機能・CLI・ユーティリティ類をまとめて追加。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応（不正値はログ警告後にデフォルト 60 秒にフォールバック）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視データを書き込む挙動。
    - 起動時にプロセス優先度を "high" に設定し、stop フラグファイルを監視してループを終了。

- 設定関連
  - config.py
    - Settings クラスを実装。環境変数・.env の自動ロード（プロジェクトルート検出）機能を追加。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース機能の強化（export プレフィックス対応、クォート内エスケープ処理、インラインコメント処理など）。
    - 各種プロパティを定義（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 検証、PAPER_TRADING_SQLITE_PATH、各種監視閾値、KABUSYS_ENV 検証など）。
    - settings = Settings() のシングルトンを公開。
  - config_setup.py
    - 対話式の .env 作成／更新ウィザードを追加。秘密項目はマスク表示、既存値の読み込み、デフォルト値の提示、保存の確認を実装。
    - .env 書き込み時にファイルヘッダや注意書きを付与（.env を Git にコミットしない旨の注意）。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を実施。
    - --strict オプションで警告を失敗（exit 1）扱いにできる。

- ポートフォリオ構築（Portfolio Construction）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・signal_rank タイブレークでソート。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は警告を出して等金額配分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャーに基づく候補除外ロジックを追加。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer によりスリッページや手数料を保守的に推定して合計コストを算出。
    - aggregate スケールダウン時に残差を考慮して lot 単位で再配分を試みる（再現性のためソート順を安定化）。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging を提供。root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定。
    - ログレベル・ログディレクトリの解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢化。
    - stdout を使用（stderr ではなく）: タスクスケジューラや cron からの起動時に stdout/stderr を一本化して扱いやすくする目的。
  - utils/process_priority.py
    - set_process_priority (high/normal/low) をプラットフォーム差分を吸収して実装（Windows の priority class / POSIX の nice 値を使用）。失敗時は警告ログでスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めするユーティリティを実装（アクセス拒否等は警告でスキップ）。

- 監視 / モニタリング
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを各起動スクリプトで行い、監視テーブルが存在することを保証（冪等）。
  - SystemMonitor（別モジュール）を用いた1回分チェックのループ化（run_monitoring）。

- 実行補助ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。閾値判定（PASS/FAIL）を実装。
    - CLI オプションで期間（--from/--to）や DB パス（--db）を指定可能。

- パッケージ管理
  - pkg root: __version__ を "0.1.0" に設定。

### Changed
- ログ関連動作
  - StreamHandler を stdout に統一し、ファイル出力の失敗時にコンソール出力のみで継続するフォールバックを実装。
- DB 接続
  - run_monitoring は監視用 DB 初期化前に Settings を参照し、環境に関係なく監視 DB パスを使用する仕様に明示。
  - run_execution は paper_trading 環境で専用 DB を使用するよう明確化（本番 DB との分離）。
- .env 自動ロード
  - プロジェクトルート (.git または pyproject.toml を基準) を起点に .env / .env.local を読み込み。OS 環境変数は保護（protected）して上書きしない。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してログ警告し、デフォルト値にフォールバックするようにした（run_monitoring）。
- プロセス優先度設定や CPU affinity 設定でアクセス許可がない場合に例外で落ちないよう例外を捕捉して警告ログでスキップするようにした。

### Security
- config_setup に .env を絶対に Git にコミットしない旨の注意を明記。
- 必須シークレットは Settings で取得し、未設定時は明確なエラーを出す実装（_require 関数）。

### Known issues / Notes
- research/factor_research の calc_momentum が途中で切れている（未完成）。本リリースではモジュールの骨格が追加されているが、完全動作には追加実装が必要。
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的なフォールバック価格の導入を検討中（ソースに TODO コメントあり）。
- position_sizing は現状グローバルな lot_size を想定しているため、銘柄別単元対応が必要な場合は拡張が必要。

---

開発者向け注意:
- 自動 .env ロードを一時的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（validate_config で警告を出します）。

(この CHANGELOG はコードの現状から推察して記載しています。実際のコミット履歴と差異がある可能性があります。)