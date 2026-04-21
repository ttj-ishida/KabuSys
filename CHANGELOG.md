# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

- リリースノートはセマンティックバージョニングに従います。
- 初回リリース: 0.1.0

---

## [0.1.0] - 2026-04-21

### Added
- プロジェクト初期リリースとして以下の主要機能・モジュールを追加。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB を分離して利用）。
      - 停止フラグ（data/stop_requested.flag）の検出により実行ループを安全に停止。
      - 実行中の PID 管理用ファイル（data/execution.pid）を使用。
      - 起動直後にプロセス優先度を "high" に設定（utils.process_priority によるプラットフォーム差分吸収）。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト: 60 秒）。
      - 監視は環境に関わらず本番用の sqlite_path を使用する設計。
      - 停止フラグの検出、例外時のロギング、KeyboardInterrupt による終了処理を実装。
  - 設定管理
    - config.py
      - 環境変数読み込み/管理クラス Settings を追加。
      - プロジェクトルート自動検出（.git もしくは pyproject.toml を起点）に基づく .env / .env.local の自動読み込み（OS 環境変数を保護）。
      - 必須値チェック（_require）、各種デフォルト値、Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）を実装。
      - KABUSYS_ENV / LOG_LEVEL 等の妥当性チェックと真偽値プロパティ（is_live, is_paper, is_dev）。
    - config_setup.py
      - 対話式 .env 作成ウィザード。既存 .env の読み込み、シークレット項目のマスク表示、.env ファイル書き出し。
      - .env のテンプレートと説明を自動生成。
    - validate_config.py
      - 起動前設定検証 CLI。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パース検証等を実装。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ロギング・プロセスユーティリティ
    - utils/logging_setup.py
      - ルートロガーの統一設定ユーティリティを追加。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログファイル出力（デフォルト logs/<app_name>.log、30 日保持）を実装。
      - LOG_DIR/LOG_LEVEL 環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py
      - Windows / POSIX (Linux/Mac/FreeBSD) を吸収するプロセス優先度設定 (set_process_priority) を追加。
      - CPU affinity を固定する set_cpu_affinity を実装。
      - psutil を使い、アクセス権限エラー等は警告でスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
      - スコア全0 の場合のフォールバック挙動（等金額配分）を WARNING で通知。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
      - 未知レジーム時は 1.0 でフォールバックし警告を出力。
      - "unknown" セクターは上限制限の対象外にする挙動。
    - portfolio/position_sizing.py
      - position sizing ロジック（risk_based / equal / score）を実装。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap によるスケーリング、cost_buffer による保守的見積りをサポート。
      - 将来的な拡張点（銘柄毎の lot_size）についての TODO コメントを残す。
  - リサーチ（ファクター計算）
    - research/factor_research.py（骨格）
      - Momentum/Value/Volatility/Liquidity 等のファクター計算方針を実装予定のモジュールを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計（実装途中の箇所あり）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプト。
      - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計して PASS/FAIL を判定（閾値はソース内定義）。
      - PAPER_TRADING_SQLITE_PATH により DB 指定可能、コマンドラインから期間指定 (--from/--to) が可能。
    - tools/__init__.py（パッケージ化）
  - パッケージ初期化
    - __init__.py にてバージョン情報 __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

## 注意事項 / 既知の制限・ TODO
- config._find_project_root は .git や pyproject.toml を基準にプロジェクトルートを検出するため、パッケージ配布後や特殊な配置では自動 .env ロードがスキップされる場合があります。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- portfolio/risk_adjustment.apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過小推定される可能性がある旨の TODO を残しています。将来的にフォールバック価格の導入を検討。
- portfolio/position_sizing は現状すべての銘柄で共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size のサポートを予定。
- research/factor_research.py はファイル末尾で実装が中断している（calc_momentum の続きを要実装）。実動作前に該当部分の完成が必要です。
- run_monitoring は監視用 DB に常に settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計です。意図的な分離が必要な場合は設定の調整を検討してください。
- process priority / cpu affinity 設定は権限やプラットフォームに依存します。設定に失敗した場合は警告をログ出力してスキップします。

---

もしリリースノートに追加したい項目（例えば内部実装のより詳細な説明、各種 CLI 使用例、互換性に関する注記など）があれば指示してください。必要に応じてリリース履歴を Unreleased セクションで管理する雛形も作成できます。