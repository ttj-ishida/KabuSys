# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠しています。  

なお、本 CHANGELOG はリポジトリ内のソースコードを参照して推測・作成したもので、実際のコミット履歴に基づくものではありません。

## [0.1.0] - 2026-04-21

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」のコアユーティリティ・起動スクリプト・ポートフォリオ構築ロジック・検証ツール群を追加。
  - バージョン番号を `__version__ = "0.1.0"` として設定（`src/kabusys/__init__.py`）。

- 起動スクリプト / 実行制御
  - 実行エンジン起動スクリプトを追加（`src/kabusys/run_execution.py`）。
    - プロセス優先度を起動時に "high" に設定（`set_process_priority("high")`）。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、MockBrokerClient を選択する設計を導入。
    - ExecutionEngine の起動・停止に PID ファイル（`data/execution.pid` を想定）と停止フラグファイル（`data/stop_requested.flag`）を利用。
    - 依存コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組立て処理を実装。RiskManager に対する既定値（最大ポジション比率、利用率、レートリミット、サーキットブレーカ閾値、最大ドローダウン等）を設定。
  - 監視（モニタリング）ループ起動スクリプトを追加（`src/kabusys/run_monitoring.py`）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（`data/stop_requested.flag`）を監視し検知時にループを終了。
    - 監視は環境に関わらず本番用の sqlite_path を使用して監視テーブルを初期化（`init_monitoring_db`）し、DuckDB と併用する。

- 設定管理
  - 環境変数 / .env 自動読み込み機構を導入（`src/kabusys/config.py`）。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索し、自動的に `.env` / `.env.local` を読み込む（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパースは export 表記・クォート・コメント・エスケープに対応。
    - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API、LINE、SQLite/DuckDB パス、paper trading パス、監視閾値、環境種別等）にアクセス可能。
    - PAPER_FILL_MODE（paper trading の約定モード）に対する入力検証を実装（有効値: "instant", "partial", "never", "reject"）。
    - 環境種別（KABUSYS_ENV）は `development` / `paper_trading` / `live` のいずれかのみ許容する検証を行う。
  - 環境設定ウィザード CLI を追加（`src/kabusys/config_setup.py`）。
    - 対話形式で .env を作成・更新する機能を提供。
    - 秘匿値（トークン等）のマスク表示・デフォルト値・選択肢提示に対応。出力する .env テンプレートで `.env` を Git に絶対にコミットしない旨の注意を記載。
  - 設定検証 CLI を追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在・パースチェック（PyYAML がインストールされている場合）を実行。
    - `--strict` オプションで警告も FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - ログ設定ユーティリティを追加（`src/kabusys/utils/logging_setup.py`）。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の環境変数と引数による解決順を実装。既存ハンドラを安全にクリアして再設定する。
  - プロセス優先度・CPU Affinity 設定ユーティリティを追加（`src/kabusys/utils/process_priority.py`）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。優先度レベル: `high` / `normal` / `low`。
    - CPU affinity を最初の N コアに固定する機能も提供。権限不足等の例外は警告によりスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み計算（`src/kabusys/portfolio/portfolio_builder.py`）
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク、上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は警告を出して等金額にフォールバック。
  - セクター集中制限・レジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）
    - apply_sector_cap: 既存保有のセクター別比率が max_sector_pct を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム (`bull`/`neutral`/`bear`) に基づき資金乗数を返す（未定義レジームは 1.0 でフォールバックし警告）。
  - 株数決定・リスク制限・単元丸め（`src/kabusys/portfolio/position_sizing.py`）
    - allocation_method: `risk_based` / `equal` / `score` をサポート。
    - risk_based: 損切り幅・risk_pct による理論株数を計算し単元（lot_size）で丸める。
    - equal/score: 重みに基づく割当を計算。1銘柄上限（max_position_pct）や aggregate 上限（available_cash / max_utilization）を考慮。
    - aggregate cap を超えた場合はスケールダウンし、残余キャッシュに基づく lot_size 単位での再配分（端数処理）を行う。
    - lot_size や cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積りに対応。
  - 上記 API をパッケージレベルでエクスポート（`src/kabusys/portfolio/__init__.py`）。

- Research / 分析
  - ファクター計算モジュールを追加（`src/kabusys/research/factor_research.py`）。
    - Momentum / Value / Volatility / Liquidity に関する設計コメントと計算用定数を定義。
    - DuckDB 接続を受け取って prices_daily / raw_financials テーブルから計算する想定。
    - モメンタム計算（calc_momentum）の実装を開始（ファイル末尾で途中まで実装が見られるが、完全実装は今後予定）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（`src/kabusys/tools/paper_verification_report.py`）。
    - PAPER_TRADING_SQLITE_PATH（または `--db` 引数）で指定した SQLite DB から集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算、欠損データに対する N/A 表示、閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）に基づく PASS/FAIL 判定を実装。

### Changed
- （初期リリースのため無し）

### Fixed
- （初期リリースのため無し）

### Notes / Implementation details / 確認事項
- .env の自動読み込みはプロジェクトルート探索に依存するため、配布後のインストール環境では自動検出が失敗する場合がある。明示的に環境変数をセットするか KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して動作を制御すること。
- logging_setup はログディレクトリの作成に失敗した場合、ファイル出力をスキップしてコンソール出力のみにフォールバックする設計。
- process_priority や CPU affinity の設定は権限に依存し、失敗時は警告を出して処理を続行する。
- portfolio の一部関数は price が欠損（0.0 等）の場合にスキップする実装となっており、将来的に価格フォールバック（前日終値など）の追加が検討されている旨の TODO コメントが存在する。
- research モジュールは設計が明確に記載されているが、calc_momentum 等の完全実装は引き続き実装・テストが必要。

---

今後の変更ログ（機能追加・バグ修正・ドキュメント整備等）は本ファイルに追記してください。