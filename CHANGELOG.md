# Changelog

すべての注目すべき変更を記載します。本ファイルは "Keep a Changelog" の形式に準拠しています。

全般:
- 日付はリリース日を示します。
- 各項目はコードから推測できる機能追加・仕様・注意点を記述しています。

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒）。
    - 停止制御はプロジェクト内 data/stop_requested.flag ファイルを利用。
    - 監視用 DB は実行環境に関係なく本番 sqlite_path を参照して初期化。
    - duckdb 接続を利用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）で本番 DB と完全分離。
    - 起動前に停止フラグをチェックし、thread を用いてエンジン実行・停止を管理。
    - 実行中は data/execution.pid に PID ファイルを使用する想定。

- 設定関連 CLI / ユーティリティ
  - config.py
    - .env の自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env と .env.local の読み込みルール（OS 環境変数 > .env.local > .env）、および KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を実装。
    - .env 行パーサは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの考慮をサポート。
    - Settings クラスを通じた型付きプロパティを提供（DB パス、LINE トークン、KABUSYS_ENV, LOG_LEVEL 等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の検証（development/paper_trading/live）を実装。
    - 各種しきい値（CPU/MEM/DISK 等）や PID/kill flag のパスを Settings 経由で取得可能。

  - config_setup.py
    - .env を対話的に作成・更新するウィザードを実装。
    - シークレット項目はマスク表示、選択肢・デフォルトサポート、既存 .env の読み込み・Enter で再利用可能。
    - 最終確認後に .env を書き出す機能を提供。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML があればパースも実施）を実装。
    - KABUSYS_ENV=live 時の追加ガードチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モードで警告を失敗扱いにできる。

- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定するユーティリティを追加。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢な実装。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（set_process_priority）。
    - Windows と POSIX(Linux/Mac/FreeBSD) に対応。アクセス権限不足等は警告ログを出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity も提供。

- Execution 系基盤（起動スクリプトで組み合わせて使用）
  - BrokerClientFactory（ブローカークライアントの生成）、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）などを組み合わせ、実行エンジンを起動するワークフローを実装（run_execution.py にて初期化 & 起動）。

- 監視系
  - monitoring_db 初期化ヘルパーを利用して監視テーブルの冪等なセットアップを実施。
  - SystemMonitor の単発チェック check_once() をポーリングループで実行し、例外はログに記録して次のポーリングへ継続。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank 小さい方優先）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックし WARNING）。

  - portfolio/risk_adjustment.py
    - セクター集中上限適用 apply_sector_cap（既存保有のセクター時価を計算し上限を超えるセクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップし未知は 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - リスクベース: risk_pct, stop_loss_pct を基に個別目標株数を算出し単元（lot_size）で丸め。
    - 等配分/スコア配分: ウェイトに基づく配分と per-position / aggregate 上限の適用。
    - aggregate cap 超過時のスケーリング処理（スケールダウン）と、残余キャッシュに対する fractional remainder を基に単元単位で再配分するアルゴリズムを実装。
    - cost_buffer を考慮した保守的見積りをサポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを読み取り、稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを集計するレポートを追加。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義し PASS/FAIL 判定を出力。
    - 日付フィルタ（--from, --to）と DB パス指定（--db）をサポート。
    - DB テーブルが存在しない場合の失敗耐性（OperationalError を捕捉して N/A を返す）。

- 研究用モジュール（雛形）
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算を行う設計を追加。DuckDB の prices_daily / raw_financials を使用する想定。
    - モメンタム計算のパラメータ定義（1M/3M/6M、MA200、ATR など）を含む。実装はモジュール内に計算ロジックの骨組みあり（一部実装途中の箇所あり）。

### Changed
- （初版のため該当なし）既存コードの大規模追加が主。

### Fixed
- （初版のため該当なし）

### Notes / Implementation details / Safety
- .env の自動読み込みはプロジェクトルートが発見できない場合スキップするため、パッケージ配布後や特殊な配置でも安全。
- .env の読み込み時、OS 環境変数は保護され（上書き保護）、.env.local は .env より優先して上書きされる。
- logging_setup はログディレクトリ作成失敗時にファイル出力を自動で無効化し、サービスの起動を阻害しない設計。
- process_priority の設定は権限不足や未対応 OS の場合は警告ログを出し続行する。
- run_monitoring と run_execution は停止フラグ（data/stop_requested.flag）をチェックし、外部からの停止要求に対応。run_execution は paper_trading モードで本番 DB から分離して動作する。
- position sizing の aggregate スケーリングは単元（lot_size）を尊重するため、丸め処理により期待通りに現金利用されない場合がある（設計上の注意点としてログにコメントあり）。
- risk_adjustment の apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いとし、unknown は上限適用の対象外となる。
- validate_config は PyYAML 未導入環境でもエラーにならず YAML 検証をスキップして警告を出す。

### Known issues / TODO
- research/factor_research.py はファクター計算の骨格があるが、ファイル末尾に断片的な行があり（実装途中）、完全実装が必要。
- position_sizing の価格欠損時のハンドリングについて注記あり（将来的に前日終値や取得原価をフォールバックする等の改善を検討）。
- 一部の TODO コメントは将来的な拡張（銘柄別 lot_size、価格フォールバック、より堅牢な DB スキーマ検証など）を示す。

---

（初版リリース: 機能追加と初期実装を含むリリース）