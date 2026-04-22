CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。
ソースコードから推測できる追加・修正点を日本語でまとめています。

フォーマット:
- 各バージョンは Released 日付を付記しています（推定）。
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

Unreleased
----------
（なし）

[0.1.0] - 2026-04-22
-------------------

Added
- 初期リリース: KabuSys パッケージを追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
- 実行エントリスクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。プロセス優先度設定、DB接続、BrokerClientFactory を使ったブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、デーモンスレッドによるセッション実行、停止フラグ（data/stop_requested.flag）および PID ファイル管理を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。監視は環境に関係なく本番 sqlite_path を使用する設計。
- 設定管理
  - config.Settings クラスを追加し、環境変数経由の設定取得とバリデーション（KABUSYS_ENV、LOG_LEVEL 等）を提供。便利プロパティ（is_live / is_paper / is_dev）を実装。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの探索: .git または pyproject.toml 基準）。読み込み順: OS環境 > .env.local > .env。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメント処理等に対応。
- 設定ユーティリティ CLI
  - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を追加。重要項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、KABUSYS_ENV 等）を対話的に設定・保存。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。未設定の必須環境変数検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 設定や Kill Switch 設定の警告）を実装。--strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア正規化配分（全スコアが0なら等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクターのエクスポージャーに基づく候補除外ロジック（sell_codes を考慮）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバックで 1.0。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。単元株（lot_size）丸め、1銘柄上限・集合上限（available_cash）でのスケールダウン、cost_buffer による保守的見積り、端数配分ロジックを実装。
- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging: stdout ストリームハンドラ + 日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log）、ログディレクトリ自動作成、既存ハンドラのクリアを実装。ログレベル解決順・ログディレクトリ解決順をドキュメント化。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX 両対応でプロセス優先度設定を実装（psutil を利用）。権限不足や未対応環境では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定するユーティリティ。例外処理で権限不足や未対応環境をハンドリング。
- 監視・モニタリング関連
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring 両方で実行して冪等的に監視テーブル存在を保証。
  - SystemMonitor の単発チェック呼び出し（monitor.check_once）をポーリングループで実行し、例外をログに残してポーリング継続する耐障害性を実装。
- ペーパートレード分離設計
  - Settings.paper_sqlite_path / is_paper を実装。run_execution は KABUSYS_ENV=paper_trading 時に専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計を採用。
  - BrokerClientFactory を用いて環境に応じたブローカークライアント（MockBrokerClient 等）を生成する想定。
- 分析・検証ツール
  - tools.paper_verification_report: ペーパートレード DB から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値に基づく PASS/FAIL レポートを生成する CLI を追加。P95 計算や日付フィルタ、DB 存在チェックを実装。閾値（稼働率/成功率/送信率/P95）をソース内定数で定義。
- データ分析（研究）モジュール骨組み
  - research.factor_research: ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / liquidity 等の設計方針と定数を定義）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。モメンタム計算関数のインターフェースが定義されている（実装途中）。

Changed
- .env 読み込みの挙動を明確化
  - .env / .env.local の読み込み順と override の挙動を定義。OS 環境変数は保護され、.env.local は .env より優先的に上書き可能。
- ログ出力の既定動作
  - ログディレクトリの作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを導入。
- run_monitoring のデフォルトポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能に（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。

Fixed
- .env パーサーの堅牢化
  - export プレフィックス、引用符付き値内のバックスラッシュエスケープ、インラインコメントの取り扱いなど、実運用でよくある .env パターンに対応。
- validate_config における YAML 検証挙動
  - PyYAML がインストールされていない場合は YAML 検証をスキップして警告を出すように変更（依存性がなくても CLI が動作するように改善）。
- 複数の I/O リソースの確実なクローズ
  - run_execution/run_monitoring での sqlite3 / duckdb 接続を finally ブロックで確実に close するように実装。

Deprecated
- なし

Removed
- なし

Security
- .env ファイルを絶対にリポジトリにコミットしない旨を config_setup の出力ヘッダに明示（注意喚起）。
- Settings._require による必須環境変数未設定時の早期エラー検出を実装し、起動前に設定漏れを検出しやすくした。

Notes / Known limitations
- research.factor_research 内のモメンタム関数はソース末尾で途中になっており、完全実装は今後の作業を想定。DuckDB ベースの集計ロジックは設計済み。
- process_priority の設定は権限依存（一般ユーザーでは失敗する可能性あり）であり、その場合は警告を出してスキップする挙動。
- position_sizing の価格欠損（price が 0.0）の扱いに注記がある（将来的に前日終値等でフォールバックする可能性を示唆）。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」との設計コメントがあり、本番環境での監視データ扱いに注意が必要。

以上。コード内の docstring・コメント・関数名から推測してまとめています。追加でバージョン履歴の細分化や個別ファイルごとの変更点（差分ベース）を希望される場合は、さらに詳細に分けて作成できます。