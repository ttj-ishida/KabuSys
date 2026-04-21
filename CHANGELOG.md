# CHANGELOG

すべての変更は「Keep a Changelog」形式に従っています。  
このファイルでは、ソースコードから推測できる新機能・改善点・重要な挙動を日本語で記載しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21
Added
- 全体
  - 初期リリース相当の機能群を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 起動スクリプト / デーモン
  - run_monitoring.py を追加: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 停止制御はプロジェクトの data/stop_requested.flag ファイルで行う。  
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して初期化する。
  - run_execution.py を追加: ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。  
    - 実行中は PID ファイル（data/execution.pid 等）を使用。停止フラグにより安全に停止可能。

- 設定管理 / CLI
  - config.py を追加: 環境変数/.env の読み込み・管理ロジックを実装。  
    - プロジェクトルートの自動判定（.git または pyproject.toml を基準）。CWD に依存しない読み込み。  
    - .env/.env.local の読み込みルール（OS 環境 > .env.local > .env）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。  
    - 複雑な .env の行パーサを実装（export プレフィックス、クォート文字・エスケープ、インラインコメントの扱いなど）。  
    - Settings クラスを提供（各種環境変数の取得とバリデーション: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV 等）。  
    - PAPER_FILL_MODE に対する検証（有効値: instant/partial/never/reject）や paper_trading 用 sqlite パス指定をサポート。
  - config_setup.py を追加: 対話式の .env 作成ウィザード CLI を実装。  
    - デフォルト値の提示、シークレット値のマスク表示、保存の確認、.env ファイルの書き込みロジックを提供。
  - validate_config.py を追加: 起動前設定検証 CLI を実装。  
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在/パース検証（PyYAML の有無に応じて挙動を変化）。  
    - 本番（live）環境向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。`--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py を追加: 全起動スクリプトで共通利用可能なログ設定ユーティリティ。  
    - stdout（StreamHandler）への出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。  
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続する保守的な動作。  
    - LOG_LEVEL / LOG_DIR / app_name を利用した柔軟な解決順を提供。
  - utils/process_priority.py を追加: プロセス優先度（および CPU affinity）設定ユーティリティを実装。  
    - Windows / POSIX （Linux, macOS 等）差分を吸収して優先度を設定（psutil を利用）。  
    - set_process_priority("high" | "normal" | "low")、set_cpu_affinity(N) を提供。許可されていない OS や権限不足時は警告を出して安全にスキップする実装。

- Execution / Monitoring 連携
  - 起動時にプロセス優先度を "high" に設定する呼び出しを run_monitoring/run_execution に追加（最初に実行）。
  - duckdb との連携: duckdb のファイルパス設定（DUCKDB_PATH）および起動時接続をサポート。

- Portfolio 関連（純粋関数ライブラリ）
  - portfolio/portfolio_builder.py を追加: 候補選定と重み算出（select_candidates, calc_equal_weights, calc_score_weights）。  
    - スコア降順ソート、同点時の tie-breaker、スコア0時のフォールバック等を実装。
  - portfolio/risk_adjustment.py を追加: セクター集中制限とレジーム乗数の計算（apply_sector_cap, calc_regime_multiplier）。  
    - セクターごとの既存エクスポージャーを算出し、上限超過セクターの候補除外を実施。unknown セクターは除外対象外。  
    - 市場レジームに基づく multiplier (bull:1.0, neutral:0.7, bear:0.3)、未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py を追加: 株数決定ロジック（risk_based / equal / score）と aggregate cap / lot_size による丸め・スケーリングを実装。  
    - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct に基づいてポジションサイズを算出。  
    - aggregate cap: 利用可能現金を超えた場合のスケーリングと端数調整（lot 単位で残余キャッシュを再配分）を実装。  
    - lot_size、cost_buffer（手数料・スリッページ見積もり）を加味した保守的計算。

- Research / 分析
  - research/factor_research.py を追加（部分実装）: DuckDB を利用したファクター計算の設計。  
    - Momentum, Value, Volatility, Liquidity といったファクターを想定。モメンタム関係の定数や計算方針を定義。  
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計思想を採用。※ファイル末尾での実装途中で切れている（続きあり）。

- Tools
  - tools/paper_verification_report.py を追加: Paper Trading 用の検証レポート生成ツール。  
    - SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。  
    - Pass/Fail 判定ルールを実装（例: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。  
    - CLI 引数で期間指定（--from, --to）や DB パス指定（--db）をサポート。

Changed
- 設計上の決定（挙動）
  - 監視（monitoring）は環境にかかわらず production sqlite_path を使用して監視テーブルを初期化する設計（環境分離は行わない）。  
  - 実行（execution）は paper_trading 環境時に専用 SQLite を使用して本番 DB と完全に分離することで安全性を高める。  
  - .env の自動ロードはデフォルトで有効だが、テスト等で無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

Fixed
- （該当なし — 初期リリース）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数のシークレット値は対話ウィザード等でマスクして表示する等の配慮あり（.env 自体は Git にコミットしない旨を README に明示）。

注記 / 実装上の補足
- .env パーサはクォート内のバックスラッシュエスケープやインラインコメントの扱いに対応していますが、非常に複雑なケースでは差異が出る可能性があります。  
- process_priority は psutil を利用しており、権限不足や未対応 OS では操作がスキップされ警告が記録されます。  
- position sizing や sector cap などの金融ロジックは純粋関数として実装されており、ユニットテストが容易になる構造です。  
- research/factor_research.py は実装途中で切れている箇所が確認できます（ファイル末尾の途中行）。必要に応じて続きを実装してください。

---  
今後の予定（提案）
- factor_research の残り実装（SQL クエリと出力整形）の完了。  
- ユニットテスト、CI、ドキュメント（README/PortfolioConstruction.md 等）とサンプル config の整備。  
- モニタリング/実行の統合的な運用手順とデプロイ手順の文書化。