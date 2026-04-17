# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

次のバージョンでは後方互換性のない変更や重大な追加がある場合は Unreleased セクションに追記してください。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-17
-------------------

Added
-----
- 基本パッケージ初期リリース: KabuSys v0.1.0 を追加。
  - パッケージバージョンは src/kabusys/__init__.py に定義（__version__ = "0.1.0"）。

- 環境設定 / ロード関連
  - .env 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理、空行/コメント行無視。
    - .env を読み込む際、OS 環境変数を保護するため protected キーを扱い .env.local は上書き（override=True）される。
  - Settings クラスを追加（src/kabusys/config.py）。主なプロパティ:
    - J-Quants / kabu API の必須トークン取得（未設定時は ValueError）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や各種監視閾値、KABUSYS_ENV / LOG_LEVEL の検証ロジック。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新する機能を追加。
    - シークレット項目はマスク表示、既存値の再利用、ファイル書き込みテンプレートを提供。

- 設定検証 CLI
  - src/kabusys/validate_config.py:
    - .env と config/*.yaml の存在・基本妥当性検証を行う CLI を追加。
    - --strict オプションで警告も FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリチェック、PyYAML がない場合のスキップ動作、本番ガード（LINE 設定や Kill フラグ自動クリアの警告）を実装。

- 実行/監視用起動スクリプト
  - src/kabusys/run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH。デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と停止フラグ（data/stop_requested.flag）監視を実装。
    - デフォルト RiskManager 設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を用意し、初期 available_cash は broker.get_available_cash() を使用。
    - プロセス優先度を起動直後に high に設定。
  - src/kabusys/run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告ログ。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループ終了。例外発生時はログを残して次ポーリングへ継続。

- 監視 DB 初期化共通化
  - init_monitoring_db(sqlite_conn) を提供し、起動時に監視テーブルが存在することを冪等的に保証。

- Process / CPU ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - set_process_priority(level: "high"|"normal"|"low") を追加。Windows（psutil の priority class）と POSIX（nice 値）を吸収して設定。
    - set_cpu_affinity(cpu_count: Optional[int]) による CPU affinity 固定機能を追加。エラー時は警告ログでフォールバック。
    - アクセス権限不足や未対応 OS の場合は警告を出してスキップする堅牢な実装。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/*
    - portfolio_builder.py:
      - select_candidates: BUY シグナルを score 降順、同点時は signal_rank 昇順でソートして上位 N 件を返す。
      - calc_equal_weights: 等金額配分（1/N）。
      - calc_score_weights: スコア加重配分（score / sum(scores)）。全スコアが 0 の場合は等金額にフォールバックして警告ログ。
    - risk_adjustment.py:
      - apply_sector_cap: 既存保有のセクター比率が閾値を超えるセクターの新規候補を除外する。unknown セクターは制限対象外。
      - calc_regime_multiplier: レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
      - Note: price 欠損時のフォールバックや将来的な銘柄別 lot_size の拡張は TODO としてコメントあり。
    - position_sizing.py:
      - calc_position_sizes: allocation_method ("risk_based" | "equal" | "score") に基づき発注株数を計算。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
      - aggregate cap により総投資額が available_cash を超える場合はスケーリングし、残余キャッシュを用いた lot 単位での追加配分（小数端数の再配分）ロジックを実装。
      - cost_buffer によりスリッページ等を保守的に見積もる。
  - 上記は純粋関数群として設計され、DBアクセスは行わない（メモリ内計算）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - calc_momentum: DuckDB の prices_daily テーブルを用いて 1M/3M/6M リターンおよび MA200 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility (途中まで実装として存在): ATR / 相対 ATR / 20 日平均売買代金 / 出来高比などの算出ロジックを実装（prices_daily に依存）。
    - 全関数は DuckDB 接続を受け取り SQL + Python で計算。raw_financials テーブルを用いた Value ファクター等の設計方針を明記。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを計算。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms。閾値違反をまとめて PASS/FAIL を判定。
    - --from / --to 日付フィルタ（YYYY-MM-DD）、--db で DB パス指定。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能。
    - DB が存在しない場合のエラーメッセージを備える。
    - レポートは標準出力に印字。

Changed
-------
- （初版のため該当なし）

Fixed
-----
- （初版のため該当なし）

Security
--------
- （初版のため該当なし）

Notes / Known issues / TODO
---------------------------
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。前日終値や取得原価でのフォールバックを将来的に検討予定。
- position_sizing:
  - 銘柄ごとの lot_size を将来的にサポートするための拡張がコメントで示されている（現状は全銘柄同一単元を想定）。
- research.calc_volatility はファイル末尾で実装途中の SQL ブロックが存在（現在のスナップショットは主要アルゴリズムを含むが、細部は継続実装の可能性あり）。
- 実行時のプロセス優先度設定や CPU affinity の適用は権限に依存するため、アクセス権限不足時はログを出して処理をスキップする設計。

---

以上が v0.1.0 の主要な追加点と設計ノートです。必要であれば各項目をより詳細に分割したり、実装差分（ファイル別変更箇所）を追記します。