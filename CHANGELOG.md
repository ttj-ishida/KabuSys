# Changelog

すべての重要な変更点を Keep a Changelog 準拠の形式で記載します。  
バージョン管理は Semantic Versioning を想定しています。

マイグレーションやリリースに伴う注意点は各項目の説明を参照してください。

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-04-21

### Added
- 全体
  - KabuSys の初期機能群を追加（ライブラリ・実行スクリプト・ユーティリティ等の初期実装）。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定関連
  - 環境変数読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env の行パースは `export KEY=val`、クォート、バックスラッシュエスケープ、インラインコメントなど複数ケースに対応。
    - Settings クラスを提供し、各種設定をプロパティから取得できる（J-Quants トークン、kabu API、DB パス、監視閾値、実行環境判定など）。
    - `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` などの値検証（許容値チェック）を実装。
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の作成／更新を対話的に支援。シークレットはマスクして表示。
    - 出力ファイルテンプレートおよびデフォルト値を用意。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の未設定検出、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）を実施。
    - `--strict` オプションで警告を失敗扱い（exit code 1）にできる。

- ロギング / プロセス制御
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル・出力先の解決順（引数 > 環境変数 > デフォルト）を実装。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収する実装。優先度設定で失敗しても警告を出してスキップ。
    - CPU affinity 固定機能（最初の N コアに固定）を提供。

- 実行スクリプト / 実行基盤
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ループ（スレッド管理）を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。停止フラグ検知で安全に停止。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装し、初期ポートフォリオ値に broker.get_available_cash() を利用。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用（監視 DB を環境分離しない設計）。
    - stop フラグ検知でループを抜ける仕組み、KeyboardInterrupt による終了をハンドリング。
  - 監視 DB 初期化ユーティリティ（monitoring_db の初期化呼び出し）を実行時に呼ぶことで冪等にテーブルの存在を保証。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio モジュールを追加（src/kabusys/portfolio/*）。
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）にソートして上位 N を選択。
      - calc_equal_weights: 等ウェイト配分（1/N）。
      - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバックして警告。
    - risk_adjustment:
      - apply_sector_cap: 既存保有のセクター別エクスポージャーが max_sector_pct を超える場合、同セクターの新規候補を除外。unknown セクターは上限の適用対象外。
      - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す。未知レジームは警告して 1.0 にフォールバック。
    - position_sizing:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
        - risk_based: 許容リスク率、ストップロス率に基づくポジションサイズ計算。
        - equal/score: ウェイトに基づく配分。
        - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、手数料・スリッページ用 cost_buffer を考慮した aggregate cap のスケールダウンと余剰の lot_size 単位での追加配分ロジックを実装。
        - 価格がない銘柄をスキップする挙動とログ出力。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py を追加（DuckDB を用いたファクター計算のベース実装）。
    - モメンタム、MA200、ATR、出来高などの計算方針と定数を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - （ファイル末尾で関数の実装が途中まで存在しているため、今後の拡張が想定される）

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計してレポートを出力（稼働率、注文成功率、送信率、リスク却下数、レイテンシ P95 等）。
    - デフォルトの合格基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - P95 計算、期間フィルタリング、DB 存在チェック、テーブルが無い場合のフォールバック（OperationalError ハンドリング）を実装。

### Changed
- ロギング
  - ログ出力は stderr ではなく stdout に StreamHandler を設定（cron/スケジューラからのリダイレクト想定）。
  - 既存ハンドラがある場合は flush/close してから削除することで二重設定を防止。

- 設定自動ロードの挙動
  - .env 自動読み込みの順序を明確化：OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない。
  - 自動読み込みの解除用に KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。

- 実行スクリプトの DB 取り扱い
  - monitoring は環境に依らず Settings.sqlite_path（本番相当）を使用する仕様に明文化。
  - execution は paper_trading の場合に paper_sqlite_path を使用して本番 DB から分離する仕様に明文化。

### Fixed / Robustness
- 環境変数パースの堅牢化
  - .env パーサはクォート内のバックスラッシュエスケープ、インラインコメント、export プレフィックス等に対応し、不正行を無視するよう改善。
- MONITOR_POLL_INTERVAL の扱い
  - 環境変数が不正（数値変換失敗、0以下 等）の場合は警告を出してデフォルト（60 秒）にフォールバックするように修正。time.sleep に渡して ValueError が発生しないよう対処。
- process_priority / cpu_affinity のフォールトトレランス
  - 権限不足や未対応 OS の場合は警告を出して処理をスキップするようにしてクラッシュを防止。
- DB 接続の確実なクローズ
  - run_execution / run_monitoring で finally により sqlite3 / duckdb の接続を確実に閉じるように実装。
- validate_config の堅牢化
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出す（ImportError ハンドリング）。
  - config/*.yaml のパースエラーを個別に検出してエラーとして報告。
- position_sizing のスケールダウンロジック
  - 合計コストが available_cash を超えた際の縮小処理で、小数部による分配（remainder）を考慮した追加配分の実装により極端な不整合を低減。

### Notes / TODOs
- portfolio.position_sizing: price が欠損（0.0）の場合に現在は単純にスキップしているため、将来的に前日終値や取得原価などのフォールバック価格を導入することが想定されている（コードに TODO コメントあり）。
- research.factor_research.py は設計・定数が整備されているが、関数の一部が未完（実装途中で終了）となっているため、完全なファクター計算の追加実装が必要。
- 一部 API クライアント（BrokerClient 等）、ExecutionEngine の内部実装は本変更ログの範囲外のため詳細は該当モジュールを参照のこと。

---

Semver に基づき今後の変更では以下を参考にしてください:
- 破壊的変更（API 変更、設定名変更等）は MAJOR を上げる
- 新機能追加は MINOR を上げる
- バグ修正・内部改善は PATCH を上げる

取り急ぎの操作や運用上の注意点:
- 本番運用時は KABUSYS_ENV を `live` に設定し、validate_config で警告や未設定項目を必ず確認してください。
- .env は決して Git にコミットしないでください（config_setup でも注意書きを表示します）。