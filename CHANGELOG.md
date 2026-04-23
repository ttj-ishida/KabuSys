CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
このファイルはコードベースから推測して作成したもので、実装の意図や既知の制約も併記しています。

Unreleased
----------

- 現時点で未リリースの変更はありません。

0.1.0 - 初回リリース
--------------------

リリース日: (初回リリース)

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境・設定管理
  - Settings クラスを追加し、環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、実行環境など）を安全に参照できるように実装。
  - _find_project_root により .git または pyproject.toml を探索してプロジェクトルートを自動判定する自動 .env ロード機能を追加（.env / .env.local の読み込み、OS 環境変数保護機構あり）。
  - PAPER_FILL_MODE の入力検証（"instant" | "partial" | "never" | "reject"）を実装。
  - 各種しきい値・パスのデフォルト値を明確化（例: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db", PAPER_TRADING_SQLITE_PATH="data/paper_trading.db"）。

- .env 対話ウィザード CLI
  - config_setup.py により対話式で .env を作成/更新するウィザードを追加。
  - シークレット項目（J-Quants トークン、kabu API パスワード、LINE トークン等）はマスク表示。
  - デフォルト値・選択肢の提示、既存 .env の読み込み、保存確認機能を実装。

- 設定検証 CLI
  - validate_config.py を追加。必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース確認を行う。
  - --strict オプションで警告も失敗扱いにできる機能を追加。
  - 本番環境（KABUSYS_ENV=live）向けの追加チェック（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を実装。

- 実行系エントリポイント
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。
  - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離する設計。
  - ブローカークライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ監視を実装。
  - 起動時にプロセス優先度を "high" に設定する処理を実行。

- 監視系エントリポイント
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するスクリプト。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出す。
  - 監視用 DB 初期化処理を行い、duckdb 接続も確保。Monitoring は実行環境にかかわらず本番 sqlite_path を利用する設計（監視は本番データを参照する想定）。
  - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定する共通ユーティリティを実装。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベル解決の優先順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py を追加。Windows/Linux (およびサポートされる POSIX) の違いを吸収してプロセス優先度（high/normal/low）と CPU affinity の設定を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢性あり。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates：BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights：等金額配分（1/N）。
    - calc_score_weights：スコアに応じた重み付け。全スコアが 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：既存保有を踏まえてセクター集中が閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは制限の対象外。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。lot_size（単元）で丸め、最大ポジション比率や利用上限（max_utilization）を考慮。
    - aggregate cap（総投下額が利用可能現金を超える場合）のスケーリング、端数処理（lot 単位で残差順に追加）を実装。
    - cost_buffer による保守的な約定コスト見積もり対応。
    - 一部未実装の改善点を TODO コメントで明示（銘柄別 lot_size など）。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py を追加（モメンタム / ボラティリティ / Value / Liquidity の設計を明記）。
  - calc_momentum のインターフェースと設計方針を実装（DuckDB 接続を受け取り prices_daily を参照して計算する想定）。（注: ファイル末尾が途中で切れているため実装の続きや細部は保留）

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から検証レポートを生成する CLI を提供。
    - 指標: 稼働率、注文成功率(Filled/Created)、送信率(Sent/Created)、リスク却下数、API レイテンシ (avg, max, P95)。
    - デフォルト基準値を設定（稼働率 >= 99.0%, 成功率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms）。
    - 日付フィルタ (--from / --to) と --db オプションをサポート。DB が存在しない場合のエラーメッセージも実装。

Changed
- （初回リリースにつき変更履歴なし）

Fixed
- （初回リリースにつき修正履歴なし）

Deprecated
- なし

Removed
- なし

Security
- セキュリティに関する明示的な脆弱性対応は無し。ただし、.env ファイルの取り扱いに注意する旨を README/スクリプトにて強調（.env を Git にコミットしない）している。

Notes / Known limitations / TODO
- research/factor_research.py の一部（calc_momentum 以降）が途中で完結していない可能性があるため、完全な実装・テストが必要。
- position_sizing.calc_position_sizes の price が欠損（0.0）の場合の扱いについて注記あり（将来的に前日終値や取得原価などのフォールバックを検討）。
- apply_sector_cap は "unknown" セクターを制限対象外とする設計。必要に応じて扱いを変更する可能性あり。
- process_priority の実行には十分な権限（特に nice 値の設定など）が必要。許可がない場合は警告を出して安全にスキップする。
- logging_setup はログディレクトリ作成に失敗した場合ファイル出力を行わないが、その場合のログ永続化方法を運用ルールとして検討する必要あり。

以上。必要であれば、各ファイルごとの詳細な変更点（関数引数や戻り値の仕様、環境変数一覧、CLI 使い方例など）を追記します。どのレベルの詳細が必要か教えてください。