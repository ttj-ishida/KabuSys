# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般:
- バージョンはパッケージの __version__ に合わせています。

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回リリース。自動売買システムのコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築・サイズ計算、レポート作成などを追加。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを設定: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 起動スクリプト / 実行管理
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止制御のための stop flag（data/stop_requested.flag）および pid ファイル（data/execution.pid）をサポート。
    - プロセス優先度を起動時に "high" に設定。

  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を周期的に実行して system_status 等を記録。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒、無効値時はデフォルトへフォールバック）。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。

- 設定管理・検証・ウィザード
  - 環境変数読み込みと Settings クラス（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env ファイルのパースは export プレフィックス、クォート、インラインコメント（スペース直前の '#'）に対応。
    - 環境ごとのフラグ（is_live / is_paper / is_dev）、各種パス・閾値・紙トレード設定（PAPER_FILL_MODE 等）をプロパティで提供。
    - 必須キー未設定時は明示的なエラーを投げる _require()。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）。
    - 対話式で .env を作成/更新するウィザードを追加。機密値はマスク表示。テンプレートに基づく .env 書き出しを実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合は）パース検証を実行。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
    - LOG_DIR の作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重ログ出力を防止。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して nice / priority_class を設定。
    - set_process_priority(level) で "high"/"normal"/"low" を指定可能。例外（権限不足等）は警告ログで無害に処理。
    - set_cpu_affinity(cpu_count) で先頭 N コアに固定可能（未対応環境や権限不足は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等配分とスコア正規化（全スコア 0 の場合は等分にフォールバックし WARNING）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションを基にセクターごとの時価比率を算出し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知値は 1.0 にフォールバックして警告）。
  - 銘柄ごとの発注株数計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮、残差配分アルゴリズムを実装。
    - price 欠損時はスキップしてログに記録。

- Paper Trading 検証ツール
  - paper_verification_report CLI（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力。
    - Pass/Fail 基準値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from / --to）をサポート。P95 計算、欠損カラム時の安全処理を実装。

- 研究用ファクター計算スケルトン
  - factor_research モジュール（src/kabusys/research/factor_research.py）の雛形を追加。
    - Momentum, Value, Volatility, Liquidity などを算出する方針と定数を記載。DuckDB 経由で prices_daily / raw_financials を参照する設計。

- DB 初期化フック
  - monitoring_db の初期化関数をランナーで呼び出すことで、監視テーブルの存在を保証（冪等）する仕組みを導入（run_execution/run_monitoring から呼び出し）。

### Changed
- （初回リリースのため、既存挙動の変更はありません）

### Fixed
- （初回リリースのため、バグ修正履歴はありません）

### Notes / 注意事項
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。パッケージ配布後や特殊な構成では自動検出に失敗する可能性があるため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を用意してください。
- ログディレクトリ作成やプロセス優先度設定は権限や OS に依存します。失敗した場合は警告ログが出力され、処理は継続します。
- Paper Trading と本番は DB を分離する設計ですが、設定ミスを防ぐため validate_config を事前に実行することを推奨します。

---
（注）本 CHANGELOG は提供されたソースコードから機能・設計を推測して作成しました。実際のコミット履歴や追加変更に基づくものではありません。必要であれば、より詳細なファイル/関数単位の変更点一覧や、将来のリリース向けの Unreleased 項目を追加できます。