KEEP A CHANGELOG形式に準拠した CHANGELOG.md（日本語）を作成しました。初回リリース v0.1.0 として、コードベースから推測できる追加機能・挙動・既知の制限点を記載しています。

注意: 日付は本日（2026-04-19）を使用しています。必要に応じて修正してください。

----------------------------------------
CHANGELOG
=========
すべての重要な変更点をここに記録します。
このファイルは Keep a Changelog（https://keepachangelog.com/）に準拠しています。

[unreleased]
------------

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース。以下の主要機能・モジュールを追加。
  - 基本パッケージ
    - パッケージ定義 (src/kabusys/__init__.py) にバージョン "0.1.0" を設定。
  - 設定 / 起動支援
    - Settings クラスによる環境変数 / .env 管理 (src/kabusys/config.py)
      - プロジェクトルートの自動検出 (.git または pyproject.toml) に基づき .env を自動ロード（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
      - .env パース機能は export プレフィックス、引用符付き値、インラインコメント等に対応。
      - 多数の設定プロパティを提供（J-Quants / kabuステーション / DB パス / PID/kill flag /しきい値等）。
      - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL のバリデーションを実施。
    - 対話式 .env 作成ウィザード (src/kabusys/config_setup.py)
      - 初期 .env の生成・更新を支援。シークレット項目はマスク表示。
      - 出力は .env に書き込み（.env をコミットしないことを強調）。
    - 設定検証 CLI (src/kabusys/validate_config.py)
      - 必須環境変数、KABUSYS_ENV や LOG_LEVEL 値、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML があれば検証）等をチェック。
      - --strict オプションで警告を失敗扱いにできる。
  - 実行 / 監視プロセス起動スクリプト
    - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
      - プロセス優先度を高に設定して起動。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を用いてブローカークライアントを生成。Engine を別スレッドで実行し、data/stop_requested.flag を検知して停止。
      - execution.pid ファイルパスをサポート。
    - SystemMonitor ポーリングループ起動スクリプト (src/kabusys/run_monitoring.py)
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視は環境に関わらず本番 sqlite_path を使用する（監視データは本番監視 DB に記録）。
      - stop flag を検知して安全にループ終了。check_once() の例外を捕捉して継続。
  - 監視 DB 初期化
    - init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。
  - ロギング / プロセス制御ユーティリティ
    - 統一ロギング設定ユーティリティ (src/kabusys/utils/logging_setup.py)
      - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
      - LOG_DIR/LOG_LEVEL の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - プロセス優先度 / CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
      - Windows / POSIX の違いを吸収して nice 値や Windows priority を設定。
      - set_cpu_affinity によるプロセスのコア固定をサポート（オプション）。
      - 権限不足や未対応環境では警告を出してスキップ。
  - ポートフォリオ構築関連（純粋関数群）
    - 選定・重み付け (src/kabusys/portfolio/portfolio_builder.py)
      - select_candidates（スコアでソート、タイブレークは signal_rank）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等分にフォールバック）。
    - セクター・レジーム調整 (src/kabusys/portfolio/risk_adjustment.py)
      - apply_sector_cap（セクター集中上限を超える場合の候補除外。unknown セクターは適用除外）
      - calc_regime_multiplier（regime に応じて投下資金乗数を返す。未知レジームは 1.0 でフォールバック）
    - ポジションサイズ計算 (src/kabusys/portfolio/position_sizing.py)
      - allocation_method に応じた株数決定 ("risk_based", "equal", "score")、単元株（lot_size）丸め、per-stock 上限と aggregate cap のスケールダウン処理、cost_buffer による保守的見積り、残差配分ロジック等を実装。
    - ポートフォリオ API エクスポート（src/kabusys/portfolio/__init__.py）
  - 解析 / レポート
    - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
      - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL で判定。
      - 既定の閾値: 稼働率 99.0%, 成功率 90.0%, 送信率 95.0%, P95 レイテンシ 200 ms。
      - 日付フィルタ（--from / --to）をサポート。DB が存在しない場合はエラー表示。
    - 研究用ファクター計算モジュールの骨組み (src/kabusys/research/factor_research.py)
      - Momentum / Value / Volatility / Liquidity 等の方針と定数を定義。DuckDB 経由で prices_daily / raw_financials を参照して計算する設計。
  - その他
    - utils パッケージの準備（__init__ 等）。
    - tools パッケージの初期化ファイル追加。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- .env の取り扱いに関する注意を明記（config_setup にも .env を絶対に Git にコミットしない旨の警告を記載）。

Known Issues / Notes
- config._find_project_root() がプロジェクトルートを特定できない場合、自動 .env ロードはスキップされる（CI / コンテナでの取り扱いに注意）。
- position_sizing / apply_sector_cap の価格フォールバック
  - sector_exposure 計算で price_map に欠損（0.0）がある場合、エクスポージャーが過少見積りされる可能性がある。将来的に前日終値や取得原価をフォールバックする TODO が残されている。
- run_monitoring は監視データを本番 sqlite_path に記録する設計（意図的）。テスト環境と分離したい場合は設定の調整が必要。
- logging_setup はログディレクトリ作成やファイルハンドラ作成に失敗した場合にフォールバックするが、ファイル出力が失われる可能性がある点を留意。
- research/factor_research.py はファイル末尾が途中で切れている（コードベースの抜粋のため）。完全実装は別途。
- psutil を用いた優先度設定 / CPU affinity はプラットフォームや権限に依存し、失敗時は警告を出して処理を続行するよう設計されている。

Development / Usage Tips
- 設定検証: python -m kabusys.validate_config（--strict オプションあり）
- .env 作成: python -m kabusys.config_setup
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Reference
- デフォルトパス: DuckDB: data/kabusys.duckdb, SQLite (monitoring): data/monitoring.db, PaperTrading SQLite: data/paper_trading.db
- 環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。

----------------------------------------

必要があれば、
- 実際のコミット履歴に基づく差分形式（Unreleased / 既存バージョン間の差分）に変換、
- 日付の修正、
- さらに詳細なコンポーネント別の小項目分解
など対応します。どの形式がよいか指示してください。