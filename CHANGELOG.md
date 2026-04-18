# Changelog

すべての重要な変更点を Keep a Changelog のガイドラインに従って日本語で記載します。

フォーマット:
- 変更はセマンティックに分類（Added / Changed / Fixed / Removed / Security / Deprecated / Known issues）しています。
- 各項目はコードベースから読み取れる設計・挙動・備考を元に要約しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値は警告してデフォルトにフォールバック。
    - 停止制御: プロジェクト内 `data/stop_requested.flag` の存在を検知してループを終了。
    - 監視データベースは環境に関係なく本番用 sqlite_path を使用（Settings で解決）。
    - duckdb 接続（分析用）も確立して SystemMonitor に渡す。
    - 例外発生時はログ出力して次のポーリングまで待機する堅牢化処理を追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite（`data/paper_trading.db` をデフォルト）に完全分離して記録。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 停止制御: `data/stop_requested.flag` を検知すると Engine.stop() を呼び出してセッションを停止。
    - PID ファイル管理（`data/execution.pid` など）に対応。

- 設定・環境管理
  - config.py
    - .env と環境変数の読み込みロジックを実装。自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を読み込む（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
    - .env のパース処理 `_parse_env_line` は次をサポート:
      - `export KEY=val` 形式
      - クォート付き値（シングル/ダブル）とバックスラッシュエスケープ処理
      - クォートなしの行におけるインラインコメントの取り扱い（直前がスペース/タブの場合はコメントと認識）
    - Settings クラスを提供し、各種設定値をプロパティ経由で取得可能:
      - J-Quants / kabu API / LINE / DB（duckdb/sqlite/paper_sqlite）/ログ / 監視閾値（CPU/MEM/DISK）など
      - PAPER_FILL_MODE のバリデーション（有効値: instant|partial|never|reject）
      - env 判定（development / paper_trading / live）とユーティリティプロパティ（is_live / is_paper / is_dev）
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 各設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を対話的に入力。
    - シークレット項目はマスク表示、選択肢やデフォルト値の提示、確認プロンプト付きで .env に書き出す `_write_env` を実装。
    - .env は生成時に注意書きヘッダを付与（Git にコミットしない旨の注意）。

- 設定検証ツール
  - validate_config.py
    - CLI による起動前検証ツールを実装（python -m kabusys.validate_config）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、値がプレースホルダのときは警告を出力。
    - KABUSYS_ENV / LOG_LEVEL / DB パスの検証。DB 親ディレクトリが無い場合は警告。
    - `config/*.yaml` の存在確認。PyYAML がインストールされていればパース検証も行う（未インストール時はスキップして警告）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。
    - ストリーム出力（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームのプロセス優先度設定を追加（Windows / POSIX に対応）。
    - set_process_priority(level: "high"|"normal"|"low") を実装。アクセス拒否等は警告してスキップ。
    - set_cpu_affinity(cpu_count) の実装。利用可能コア数より大きい数が指定された場合の挙動を扱う。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等額配分・スコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーが閾値（max_sector_pct）を超える銘柄の新規候補除外処理を実装。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング）を実装。未知のレジームは 1.0 でフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて銘柄ごとの発注株数を計算。
    - risk_based: 許容リスク率、stop_loss_pct 等からベース株数を計算し、単元株（lot_size）に丸める。
    - equal/score: ウェイトと max_utilization を用いて単元株丸め、per-stock 上限（max_position_pct）を考慮。
    - aggregate cap: 全銘柄のコストが available_cash を超える場合、スケーリングして lot_size 単位で再配分するアルゴリズムを実装。cost_buffer により手数料/スリッページを保守的に見積もる。
    - 設計上の注意: lot_size は現在は全銘柄共通。将来的に銘柄別 lot_map を導入する TODO を記載。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加（python -m kabusys.tools.paper_verification_report）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、平均/最大レイテンシ、リスク却下数、総ポーリング数など。
    - P95 計算関数、期間フィルタ (from/to)、DB パス解決（--db > 環境変数 > デフォルト）を実装。
    - 基準値（しきい値）を定義して PASS/FAIL 判定を行う（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms など）。
    - SQLite のテーブル欠如（OperationalError）時は適切にフォールバックしてレポートを生成。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム / MA200 / ATR / ボラティリティ等の計算方針を記載）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。calc_momentum 関数（モメンタム指標計算）の骨格を開始。注: ファイル末尾が途中で切れている（未完）。

- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （本リリースで特別なセキュリティ項目なし）
- 注意: .env は生成時に明確に Git にコミットしないようヘッダで注意喚起している。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされてしまい正しくブロックできない旨の TODO コメントあり。将来的に前日終値や取得原価でフォールバックすることを検討する必要あり。
- portfolio/position_sizing:
  - 現在 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る設計が望まれる（TODO コメントあり）。
- research/factor_research.py:
  - ファイルが途中で切れており、ファクター計算の一部実装が未完。追加実装・テストが必要。
- run_monitoring / run_execution:
  - 外部依存（psutil, duckdb, pyyaml 等）がインストールされていることが前提。欠如時の挙動は各モジュールで限定的に警告・フォールバックしているが、テストで確認推奨。
- 一部の機能（BrokerClientFactory, ExecutionEngine, SystemMonitor 等）は本 CHANGELOG の対象外の内部実装に依存するため、本稿では起動スクリプト周りの統合振る舞いのみを記載。

---

今後のリリースでは、未完の factor_research の完成、単体テストの追加、ドキュメント（API/設計ドキュメント）の整備、銘柄別 lot_size 対応、価格フォールバックロジックの実装などを予定してください。