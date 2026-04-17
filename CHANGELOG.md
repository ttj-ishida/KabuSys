Keep a Changelog準拠の CHANGELOG.md（日本語）
（推測に基づきコードベースの変更点・機能を記載しています）

All notable changes to this project will be documented in this file.

フォーマットの規約については https://keepachangelog.com/ja/ を参照してください。

Unreleased
----------

（なし）

0.1.0 - 2026-04-17
-----------------

Added
- 初回リリース: KabuSys 自動売買システムのコアユーティリティ群を追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - エンジンは別スレッドで実行され、停止フラグ検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py: Settings クラスを実装。環境変数・.env ファイル（.env.local の上書き含む）から設定を読み込む自動ロード機能を提供（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースは export プレフィックス・クォート・エスケープ・インラインコメント等に対応。
    - 各種設定プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等）を提供し、バリデーションを実行。
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - セクション毎のテンプレート出力と保存、.env を Git にコミットしない旨の注意文を含む。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml ファイル存在・パース検査（PyYAML 利用、未導入時はスキップ）、本番用ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険値警告）などを実装。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコア 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有を基に上限超過セクターの候補除外）。"unknown" セクターは制限対象外にする挙動。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算、単元株丸め（lot_size）、1銘柄上限・合計上限（available_cash）・cost_buffer（手数料・スリッページ見積）を考慮したスケーリング・再配分ロジックを実装。
    - risk_based では stop_loss_pct / risk_pct を利用した目標株数計算。
    - aggregate cap 超過時の縮小・残差配慮ロジックを実装（再現性のあるソートで残余配分）。
- utils
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収し、呼び出し側はプラットフォーム依存を意識せず使用可能。
    - 権限不足や未対応 API の場合は警告を出してスキップする安全設計。
- 研究用ファクター計算
  - research/factor_research.py: DuckDB を利用したファクター計算モジュール（Momentum / Volatility / Liquidity / Value の設計方針）。
    - calc_momentum: 約1/3/6か月リターン、MA200 乖離率を SQL ウィンドウ関数で計算。
    - calc_volatility: ATR (20日) / 20日平均売買代金 / 出来高比率 を計算する設計（詳細な NULL/データ不足ハンドリングを考慮した実装）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算して PASS/FAIL 判定を表示。
    - デフォルト DB は data/paper_trading.db、PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで上書き可能。
    - レポートの閾値（稼働率 99% 等）はスクリプト内定義で判定。
- DB / 接続
  - DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用する設計を採用。run_* スクリプトはそれぞれの用途に応じて適切な DB パスを選択。
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を参照して、監視テーブルが起動時に存在することを保証（冪等処理）。
- パッケージ情報
  - __init__.py によるバージョン定義 __version__ = "0.1.0"。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の注意（推測）
- .env パーサはクォート中のバックスラッシュエスケープや export プレフィックス、インラインコメントの取り扱いに対応しており、現場でよくある .env のバリエーションを扱えるよう設計されています。
- run_monitoring は監視用 DB を本番パスで固定して参照するため、監視ログの混同を避ける設計になっています（paper_trading 環境でも本番監視 DB を使う仕様になっている点に注意）。
- Paper Trading は発注関連を完全に分離（専用 SQLite）しており、本番資金とデータを混同しない安全設計です。
- process_priority / cpu_affinity の設定は権限やプラットフォームによって失敗する可能性があるため、失敗時はログ警告でスキップする挙動となっています。
- portfolio/position_sizing のスケーリングロジックは lot_size 単位で丸めるため、端数扱いに注意が必要です。

開発者向け補足（推測）
- config_setup.py と validate_config.py により、新規導入時のセットアップと事前検査を CLI で実行可能。初期導入フローとして .env を生成 → validate_config でチェック → 起動スクリプト（run_execution/run_monitoring）を実行する想定。
- DuckDB を分析用に使用するため、大量の履歴データ集計やファクター計算は DuckDB 側で高速に処理される想定。

ライセンスや貢献
- この CHANGELOG はコードから推測して作成しています。実際のリリースノート作成時は、PR 単位の変更点や既知の問題一覧を追加してください。