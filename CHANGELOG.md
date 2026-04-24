CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
主にコードベースの現状（src/ 以下）から機能追加・設計意図・既知の TODO を推測してまとめています。

Unreleased
----------
- 改善予定（コード内の TODO コメントや拡張余地から推測）
  - position_sizing: 銘柄ごとの単元株（lot_size）を銘柄マスタから取得する仕組みへの拡張。
  - risk_adjustment: price の欠損時に前日終値や取得原価でフォールバックするロジックの追加。
  - research.factor_research: ファクター計算の実装完了（ファイル末尾が途中で切れているため未完了の関数が存在する可能性）。
  - 監視・実行の運用改善（ログ出力やエラーハンドリングの強化、監視項目の追加など）。
  - 自動テスト・CI の整備（明示的なテストコードは確認できないため想定）。

[0.1.0] - 2026-04-24
--------------------
Added
- 全体
  - 初期リリースとして、KabuSys コードベースを公開。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイントを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient を利用する想定）。
    - stop フラグ（data/stop_requested.flag）を監視し、存在時に安全に停止。起動時にフラグが既に存在すると起動せず終了。
    - エンジン用の PID ファイル管理（data/execution.pid を想定）。
    - duckdb 接続（分析用 DB）も初期化して利用。

  - run_monitoring.py
    - SystemMonitor 起動用エントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path（data/monitoring.db 等）を使用。
    - stop フラグでループ終了、check_once() 実行中の例外はログに出力して次サイクルへ継続。

- 設定管理 / CLI
  - config.py
    - Settings クラスを実装し、環境変数（.env/.env.local を含む自動ロード）から設定を取得する API を提供。
    - .env 自動ロードはプロジェクトルート（.git / pyproject.toml を起点）を検出して行う（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env パーサは export 形式、クォート文字・エスケープ、インラインコメントなどを扱える堅牢な実装。
    - 各種設定プロパティを提供（J-Quants, kabuステーション, LINE, DuckDB/SQLite パス, PID/KILL フラグパス, モニタ閾値, PAPER_FILL_MODE 検証など）。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実施。

  - config_setup.py
    - 対話式 .env 作成ウィザードを実装（既存 .env の読み込みと Enter による既存値の再利用、シークレット項目のマスク表示、書き込み時の注意喚起）。
    - 書き込みフォーマットは .env 内のセクション分けとコメント付きで出力。

  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV=live 固有の保護チェック（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実施。
    - --strict オプションで警告をエラー扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を実装。
    - stdout への StreamHandler と、logs/<app_name>.log への TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして標準出力のみで継続するフェールセーフを実装。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を明示。

  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定ユーティリティを提供（set_process_priority）。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応し、未対応 OS は警告を出してスキップ。
    - set_cpu_affinity によりプロセスを先頭 N コアにピン留めする機能も提供。アクセス権限がない場合は警告を出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定・重み計算: select_candidates（スコア降順、同点は signal_rank でタイブレーク）、calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター時価を計算し、上限超過セクターの候補を除外。unknown セクターは制限対象外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップと未知レジームでのフォールバック挙動）。
    - TODO コメントで price 欠損時のフォールバック拡張を想定。

  - portfolio/position_sizing.py
    - 発注株数算出 calc_position_sizes を実装。
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）と aggregate cap（available_cash）を考慮したスケーリングと残余分配アルゴリズムを実装。
    - cost_buffer を使った保守的なコスト見積りを反映。

  - portfolio/__init__.py により主要関数を公開。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受けて prices_daily / raw_financials を用いたモメンタム等のファクター計算を行うモジュールを追加（設計方針と定数・関数の雛形を実装）。一部関数はファイル末尾で途切れているため追加実装が想定される。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを実装。
    - system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し、閾値に基づいて PASS/FAIL を判定。
    - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。--from / --to / --db オプションをサポート。
    - P95 計算、N/A 表示などの堅牢な出力形式。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース。ただし設計上のフォールバック処理や例外ハンドリングが各所に実装されており、実運用での追加修正箇所が想定される）

Deprecated
- なし

Removed
- なし

Security
- なし（ただしシークレット情報の扱いに関する注意書きが .env 書き出し時に明記されている）

Notes / 実運用上の注意（コードから推測）
- .env ファイルは絶対に Git にコミットしないこと（config_setup の出力に明記）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることが推奨される（auto-clear は危険）。
- run_monitoring は監視 DB（SQLITE_PATH）を本番パスで参照するため、環境により監視対象 DB の分離に注意が必要。
- run_execution は paper_trading 時に DB を分離する設計になっているため、paper/live の DB 分離方針は適切に運用可能。
- ロギングは標準出力とファイル両対応だが、ログディレクトリの作成に失敗した場合はファイル出力が無効化されるため、起動環境の権限・パスに注意。

---

この CHANGELOG はソースコードの実装内容とコメント（docstring / TODO / メッセージ）から推測して作成しています。実際のコミット履歴がある場合は、コミット単位での差分に基づく詳細な CHANGELOG の作成を推奨します。必要であれば、想定されるリリースノート文言を英語で作成したり、各モジュールごとにより詳細な変更点（関数引数の仕様や返り値の例など）を追記できます。どのレベルの詳細が必要か教えてください。