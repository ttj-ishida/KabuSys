# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースから推測される主要な変更・追加点を記載しています。

全体方針:
- 初期公開リリースとして 0.1.0 を作成（コードベースの現状に基づくまとめ）
- 各項目はソースコードの機能説明・実装から推測しています

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買フレームワーク「KabuSys」の基本コンポーネントを実装。

### Added
- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、MockBrokerClient を切り替えられる（BrokerClientFactory により生成）。
    - エンジンは別スレッドで run_session を実行し、data/stop_requested.flag による停止指示を監視。
    - 起動時にプロセス優先度を "high" に設定する仕組みを呼び出す。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に依存せず本番 sqlite_path を使用する実装。
    - data/stop_requested.flag による優雅な停止、KeyboardInterrupt による終了処理を実装。

- 設定管理（.env / 環境変数）
  - config.py: Settings クラスを実装し、アプリケーション設定を環境変数から提供。
    - .env/.env.local の自動ロード機能（プロジェクトルート検出による）。OS 環境変数の保護（上書き防止）をサポート。
    - .env 解析の強化: export プレフィックス、クォート文字内のエスケープ、インラインコメントの取り扱いなどをサポート。
    - 各種設定プロパティを定義（J-Quants トークン、kabu API、DB パス、paper_trading の DB・fill_mode、監視閾値、環境判定ヘルパ等）。
    - 入力値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実装。

- 設定補助 CLI / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレット項目はマスク表示、既存 .env の読み込みと再利用、保存前確認などを提供。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の有無と YAML パース検査（PyYAML が無ければ警告）を行う。
    - --strict により警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ初期化ユーティリティを追加。
    - stdout 出力用 StreamHandler（STDOUT）と、日次ローテートする TimedRotatingFileHandler（logs/<app>.log）をルートロガーに設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラの二重設定を防ぐ（既存ハンドラをクリアして再設定）。
  - utils/process_priority.py: クロスプラットフォーム（Windows/Linux/macOS 等）のプロセス優先度設定と CPU affinity ユーティリティを追加。
    - Windows の優先度定数と POSIX の nice 値を抽象化して set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留めできる（権限や未実装 API は警告でスキップ）。

- ポートフォリオ構築関連モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates(): シグナルスコアの降順選別（タイブレーク: signal_rank）。
    - calc_equal_weights(), calc_score_weights(): 等金額配分、スコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中上限(max_sector_pct)を越える場合に新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier(): 市場レジームに応じたレバレッジ/投下率乗数を返す ("bull"/"neutral"/"bear")。未知値は警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に基づき各銘柄の発注株数を算出。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積りおよび余剰配分ロジックを搭載。

- 実務支援ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs などから稼働率、注文成功率、送信率、レイテンシ（avg, max, P95）を算出。
    - 各指標に対する閾値を定義し PASS/FAIL を判定（デフォルト閾値: uptime>=99%、fill_rate>=90%、send_rate>=95%、P95<=200ms）。
    - コマンドライン引数で期間(from/to) や DB パスを指定可能。DB が無ければエラーメッセージを出力。

- 研究用ファクターモジュール（部分実装）
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計で実装を開始（関数 calc_momentum 等の骨組み、定数を定義）。※ファイル末尾で実装が途中（トランケート）している点に注意。

- パッケージメタ
  - パッケージ初期化: __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- monitor と execution のプロセス停止／終了処理を明示的に実装（stop flag / KeyboardInterrupt ハンドリング）。
- .env ローダーの安全性: OS 環境変数を保護して .env.local の上書きを制御。

### Security
- .env の取り扱いに関する注意書きを config_setup.py の出力に明記（.env を Git にコミットしない旨）。

### Notes / Implementation details（実装上の注記・想定動作）
- DB 分離:
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB とデータを分離する設計。
  - 監視系（run_monitoring）は環境にかかわらず settings.sqlite_path（本番想定）を参照する実装になっている点は意図的と思われる（監視は本番データを監視する想定）。
- ログ:
  - ファイル出力に失敗した場合はコンソール出力にフォールバックする堅牢性を持つ。
- エラーハンドリング:
  - ループ内の予期しない例外を監視スクリプトが捕捉してログ出力し、次のポーリングまで待機する設計。
- 将来の拡張ポイント（コード内コメントより推測）:
  - position_sizing: 将来的に銘柄ごとの lot_size 情報を stocks マスタに持たせる拡張を想定。
  - risk_adjustment: apply_sector_cap の価格欠損時の扱い（フォールバック価格導入）を改善予定。
  - research/factor_research の未完実装部分の続行。

---

上記は現行ソースコードから推測して作成した CHANGELOG です。実際の変更履歴やリリースノートとして使用する場合は、コミット履歴・リリース方針に合わせて適宜編集してください。