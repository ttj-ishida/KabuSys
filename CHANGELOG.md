# Changelog

すべての重要な変更はここに記録します。フォーマットは「Keep a Changelog」に準拠します。

最新リリース
------------

### [0.1.0] - 2026-04-17

Added
- 基本アプリケーション初期実装を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
- 起動スクリプトを追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルートの data/stop_requested.flag により検知。監視は環境にかかわらず本番用の sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite DB を使用して本番 DB と分離する。停止フラグと PID 管理を実装。エンジンはデーモンスレッドで実行され、停止フラグ検知時に安全に停止する。
- 設定管理を実装（kabusys.config）。
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。優先順位は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パース機能強化: `export KEY=val` 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、コメント処理などに対応。
  - Settings クラスを実装し各種設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、監視閾値、環境判定等）。環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証）を含む。
- 対話式設定ウィザード（kabusys.config_setup）を追加。
  - .env の初期作成・更新を支援。対話入力、既存値の再利用、書き込みテンプレート生成機能を提供。
- 設定検証 CLI（kabusys.validate_config）を追加。
  - 必須環境変数・DB パス・config/*.yaml の存在・YAML パース（PyYAML が存在する場合）・本番環境特有チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）などを検証。--strict モードで警告を FAIL 扱いにできる。
- Process 優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。
  - set_process_priority(level) で Windows / POSIX（Linux, macOS, FreeBSD）を抽象化して優先度設定を試行。権限がない場合は警告してスキップ。
  - set_cpu_affinity(cpu_count) によりプロセスを先頭 N コアにピンニング可能。失敗時は警告してスキップ。
- Portfolio 構築モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。全銘柄スコアがゼロの場合は等配分にフォールバックして警告を出力。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）。未知のセクターやレジーム時のフォールバック動作を実装。
  - position_sizing: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）丸め、1銘柄上限、aggregate cap（投下合計が利用可能現金を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装。
- 研究用ファクター計算モジュールを追加（kabusys.research.factor_research）。
  - momentum, volatility などのファクターを DuckDB 接続（prices_daily テーブル）を使って計算。1M/3M/6M リターン、MA200 乖離、ATR20、平均売買代金、出来高関連などを実装。データ不足時は None を返す設計。
- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）を追加。
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から期間フィルタで各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計（avg/max/P95））を集計してレポートと PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 99% など）。
- DuckDB を分析用 DB として利用する実装を追加（Settings.duckdb_path デフォルト: data/kabusys.duckdb）。監視テーブルの初期化ユーティリティ init_monitoring_db を利用。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数の値が不正（非整数や 0 以下）の場合にデフォルト（60 秒）へフォールバックし、警告を出力する。
- run_execution は paper_trading モード時に MockBroker（BrokerClientFactory により生成される）を利用して本番 DB と完全分離する設計。RiskManager の初期値に broker.get_available_cash() を使用して初期ポートフォリオ値を算出する。
- .env パースはシェル互換の完全実装ではなく、一般的なケース（export プレフィックス、クォートとエスケープ、行末コメント）に対応するための実装になっている。
- position_sizing のスケーリングロジックおよび apply_sector_cap のセクター露出計算は、価格データ欠落時に過小評価を招く可能性がある旨の TODO コメントがある（将来的なフォールバック価格導入を想定）。
- psutil による優先度 / affinity 設定は環境によって権限や API の違いで失敗することがあるため、失敗時は警告ログにとどめて処理を継続する。

今後の改善点（示唆）
- 銘柄ごとの lot_size を持たせる等の拡張（position_sizing の TODO）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価）実装。
- factor_research における追加ファクターや並列化、長期運用向けのパフォーマンス改善。
- validate_config におけるさらに厳密な YAML スキーマ検証導入。

--- 

（初回リリースのため過去の変更履歴はありません。）