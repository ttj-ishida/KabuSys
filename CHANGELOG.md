# Changelog

すべての非破壊的変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
日付はリリース日または変更検出日です。

## [Unreleased]

## [0.1.0] - 2026-04-25
初回公開リリース。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys/__init__.py: __version__ = "0.1.0"）。
  - モジュール群を整理して公開 API を定義（kabusys.portfolio の __all__ 指定など）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をバックグラウンドスレッドで実行し、停止フラグ（data/stop_requested.flag）や PID ファイルを扱う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler の組み立てを行う。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を定期実行し監視データを記録。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用途では環境に関わらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - 環境変数/設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）。
    - export KEY=val 形式・クォート付き値・インラインコメントなどを適切にパースする堅牢な .env パーサを実装。
    - 多数の設定プロパティ（DB パス、PID/kill flag、閾値、環境種別判定、PAPER_FILL_MODE の検証など）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。シークレットは入力表示をマスク、既存 .env の読み込みと Enter による再利用が可能。
    - 保存前に設定を表示して確認を促す。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数・KABUSYS_ENV 値・LOG_LEVEL・DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）などを行う。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - ログ初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力の StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - LOG_DIR/LOG_LEVEL の既定値と解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX の差分を吸収して set_process_priority("high"|"normal"|"low") を提供（psutil ベース）。CPU affinity の設定関数も実装。

- ポートフォリオ構築
  - 銘柄選定・重み付けモジュールを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順、同点は signal_rank によるタイブレーク）、calc_equal_weights、calc_score_weights（全スコア0のとき等金額にフォールバック）を実装。
  - セクター上限・レジーム乗数ロジックを追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存保有を元にセクター上限を超える場合に新規候補を除外、"unknown" セクターは除外しない）、calc_regime_multiplier（bull/neutral/bear に応じた乗数、未知はフォールバック）。
  - 株数計算・リスク制限ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method="risk_based" / "equal" / "score" に対応した position sizing を実装。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）でスケーリング、cost_buffer を考慮した保守的推定、スケールダウン後の端数配分ロジックなどを実装。

- ツール類
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite の paper_trading DB からシステム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。
    - PASS/FAIL 判定の閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - --from/--to/--db オプションを提供。PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能。

- 研究用ファクター計算（作業中）
  - 基礎構造を追加（src/kabusys/research/factor_research.py）。
    - モメンタム（1/3/6M）、MA200 乖離、ATR、流動性等の定義と計算方針、DuckDB 接続を受ける設計などのスケルトンを実装（関数 calc_momentum 等のインターフェース定義を開始）。

### Changed
- .env パース/読み込みの挙動
  - .env の読み込み順序を OS 環境 > .env.local（上書き） > .env（未設定のみ）にして、OS 環境変数の保護を実装。
  - export 形式・引用符・エスケープシーケンス・インラインコメントの取り扱いを精密化。

- ログの出力先
  - コンソール出力は stdout を使用（stderr ではない） — タスクスケジューラ等で stdout/stderr を一本化してリダイレクトする運用を想定。

### Fixed / Defensive
- 環境変数値の検証とフォールバック
  - MONITOR_POLL_INTERVAL が 0 または負数、非整数の場合に警告を出してデフォルト（60 秒）にフォールバックするように修正（run_monitoring）。
  - PAPER_FILL_MODE の無効値を検出して ValueError を送出する検証を実装（config.Settings.paper_fill_mode）。
  - KABUSYS_ENV / LOG_LEVEL の不正値を検出して早期にエラーまたは警告を出す検証ロジックを追加（config, validate_config）。
- DB 初期化の冪等化
  - init_monitoring_db を起動時に呼び出し、監視用テーブルが存在することを保証（run_execution, run_monitoring）。
- ログハンドラ二重設定防止
  - setup_logging が既存ハンドラを flush/close してから削除することで、複数回の初期化時にハンドラが重複して出力される問題を回避。

### Notes / Limitations
- research/factor_research.py は計算ロジックの骨格を実装済みですが（関数定義や定数）、一部実装が未完（ファイルの末尾が途中で切れている状態）であり、完全なファクター計算のエンドツーエンド検証は今後の作業を要します。
- position_sizing の lot_size は現状すべての銘柄で共通設定を仮定している（将来的に銘柄別 lot_map の導入を検討）。
- apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーが過少見積もりになる旨の TODO コメントあり。将来的な価格フォールバックを推奨。

---

開発・デプロイ時の参考:
- 設定検証: python -m kabusys.validate_config
- 環境設定ウィザード: python -m kabusys.config_setup
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

（必要に応じて、各機能ごとの詳細な使用方法・設計ドキュメントを別途作成してください。）