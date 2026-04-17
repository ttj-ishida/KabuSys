CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

記法:
- 変更はセクション（Added, Changed, Fixed, Removed, Security）に分類しています。
- 各エントリは実装および動作から推測して記載しています。

[Unreleased]
------------

（未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定と読み込み
  - kabusys.config:
    - プロジェクトルートを .git または pyproject.toml から自動探索して .env/.env.local を順に読み込む自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパース実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 設定キーの取得用 Settings クラスを実装（DB パス、API トークン、KABUSYS_ENV、各種しきい値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - is_live/is_paper/is_dev 等のユーティリティプロパティを提供。
- 設定関連 CLI
  - kabusys.config_setup:
    - 対話式ウィザードで .env を作成・更新する CLI を実装。秘匿項目はマスク表示。
    - デフォルト値、選択肢、説明文を含む複数の設定項目をサポートし、.env を安全に書き出す機能を追加。
  - kabusys.validate_config:
    - 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV 検証、DB パスや config/*.yaml の存在と（可能なら）YAML パース検証を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 本番環境向けガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START 設定等）のチェックを追加。
- 実行 / 監視エントリポイント
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を利用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。Engine はスレッドで実行され、stop フラグで安全に停止。
    - RiskManager のデフォルト RiskConfig を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() で動的取得。
    - 実行 PID ファイルを管理（data/execution.pid）。
    - 起動時に停止フラグが立っていれば起動をスキップする安全機能を追加。
  - run_monitoring:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（monitoring DB の分離ポリシー）。
    - duckdb, sqlite 接続初期化と監視 DB テーブルの初期化（init_monitoring_db）。
    - 停止フラグファイル（data/stop_requested.flag）検出によるループ終了、KeyboardInterrupt のハンドリング、例外時のログ保持とポーリング継続を実装。
- モニタリング / DB 初期化
  - monitoring 側の DB 初期化フック（init_monitoring_db）を呼び出して監視用テーブルの存在を保証（冪等）。
- ユーティリティ
  - kabusys.utils.process_priority:
    - クロスプラットフォームでプロセス優先度（Windows の priority class、POSIX の nice 値）を設定する機能を追加。アクセス権限がない場合は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
- ポートフォリオ構築ライブラリ
  - kabusys.portfolio.portfolio_builder:
    - 銘柄選定 select_candidates（スコア降順・同点時信号ランクでのタイブレーク）を実装。
    - 重み計算: calc_equal_weights（等分配）および calc_score_weights（スコア正規化。全スコアが 0 の場合は等分配にフォールバックして警告）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有比率が上限を超えるセクターの新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（既定: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告の上フォールバック 1.0。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes を実装。allocation_method（"risk_based"/"equal"/"score"）に応じた株数計算、単元株（lot_size）での丸め、per-stock 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積り）考慮、残余キャッシュを用いる端数分配アルゴリズムを備える。
- 研究用 / 分析モジュール
  - kabusys.research.factor_research:
    - DuckDB を用いた定量ファクター計算モジュール（モメンタム、ボラティリティ、流動性等）を実装。calc_momentum（1M/3M/6M リターン、MA200 乖離率）、calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比率）を提供。データ不足時の None 返却やウィンドウサイズの扱いに留意。
- ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード結果検証レポート生成スクリプトを追加。P95 計算、稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL 判定を出力。
    - デフォルトの DB は data/paper_trading.db。期間指定 (--from/--to) と DB 指定 (--db) をサポート。
    - レポートの閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）を定義。
- パッケージ初期化
  - kabusys.portfolio/__init__.py で主要関数をエクスポート。

Changed
- 無し（初回リリースのため）

Fixed
- 無し（初回リリースのため）

Removed
- 無し（初回リリースのため）

Security
- 機密情報の取り扱いに配慮:
  - config_setup の出力では秘匿項目をマスク表示。
  - .env ファイルに関する注意書きを自動生成ファイルヘッダに含め、Git へのコミット禁止を明示。

Notes / 実装上の注意（今後の改善候補）
- calc_position_sizes の max_per_stock 計算で price が 0.0 の場合にエクスポージャーが過小評価されうるため、価格フォールバック（前日終値等）を導入する余地がある旨を TODO コメントで記載。
- apply_sector_cap は "unknown" セクターを制限対象外にしている点は設計上の選択。マスタ不備時の挙動を注意すること。
- process_priority や set_cpu_affinity は権限不足で失敗する可能性があり、その場合は警告ログを出してスキップする実装になっている。
- validate_config は PyYAML 未インストール時に YAML 内容検証をスキップする（警告を出力）。

--- 
この CHANGELOG は、提供されたコードベースの内容から実装意図を推測して作成しています。実際のリリースノートとは差異がある可能性があります。必要であれば、リリース日付や各項目の詳細（コミットハッシュ、著者など）を追記します。