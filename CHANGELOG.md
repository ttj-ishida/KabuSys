CHANGELOG
=========

すべての変更は Keep a Changelog の形式 (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-21
------------------

Added
- 初期リリース。KabuSys 日本株自動売買システムの基本機能群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。プロセス優先度を "high" に設定し、環境に応じてペーパートレード用 DB を分離して利用（KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。BrokerClientFactory により本番/モックブローカーを切り替え。停止フラグ（data/stop_requested.flag）・PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。監視 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
- 設定管理
  - config.py: 環境変数／.env の読み込みと Settings クラスを追加。プロジェクトルート自動検出（.git / pyproject.toml）。自動ロードは OS 環境変数 > .env.local > .env の優先順で行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。.env パースは export 形式、クォート文字（エスケープ対応）、インラインコメントの扱いに対応。多くの設定プロパティ（J-Quants, kabu API, DB パス, ログ, Kill Switch 関連, 監視閾値 など）を提供。
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新する CLI を追加。必須項目のマスク表示や既存値の読み込み、保存確認を実装。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML 利用可時）や本番向けのガードチェック（LINE 通知・KILL_FLAG_CLEAR_ON_START）を実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純関数群、DB参照なし）
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順、同点のタイブレーク）、等金額配分・スコア加重配分の関数を追加。スコア全ゼロ時は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。セクターが "unknown" の場合は上限適用を行わない仕様。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装。allocation_method による "risk_based" / "equal" / "score" をサポート。単元株（lot_size）で丸め、1銘柄上限・全体の aggregate cap を考慮してスケールダウンし、残余キャッシュを用いた端数配分を行う。cost_buffer（スリッページ・手数料見積）対応。価格欠損時のスキップやログ出力あり。
- ユーティリティ
  - utils/logging_setup.py: 標準化されたロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR / app_name による設定、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック等を実装。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。Windows / POSIX の差分を吸収する実装で、"high" / "normal" / "low" のレベルをサポート。失敗時は警告でスキップ。
- 研究・分析
  - research/factor_research.py: ファクター計算モジュールの枠組み（モメンタム、Value、Volatility、Liquidity）を追加。DuckDB の prices_daily / raw_financials を利用して計算する設計（実装途中の箇所あり）。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または --db）を解析して検証レポートを出力する CLI を追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計し、閾値（稼働率 99% / 成功率 90% / 送信率 95% / P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。日付フィルタ（--from / --to）対応。
- パッケージメタ
  - __init__.py: パッケージのバージョンを 0.1.0 に設定。

Security
- 特になし。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Notes / 既知の注意点
- run_monitoring は Monitoring 用 SQLite（Settings.sqlite_path）を環境にかかわらず使用します。ペーパートレードと監視 DB を完全に分離したい場合は別途設定変更が必要です。
- .env の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml が存在するディレクトリ）。プロジェクトルートが検出できない場合、自動ロードはスキップされます。
- position_sizing の price 欠損時は簡易にスキップする挙動になっており、将来的にフォールバック価格（前日終値等）を導入することを想定しています（TODO コメントあり）。
- research/factor_research モジュールは設計方針と一部実装が含まれますが、計算の完全実装・最適化は継続が必要です。

作者・貢献
- 初期実装（コア CLI/ユーティリティ/ポートフォリオ/実行監視基盤）

---