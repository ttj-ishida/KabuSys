CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています（カテゴリー: Added, Changed, Fixed, Removed 等）。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース: KabuSys コードベースの主要機能群を追加。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading モードでは MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag の存在を検知して安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - デフォルト PID ファイル path: data/execution.pid（Settings 経由で上書き可）。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring 用テーブルの初期化を保証）。
    - stop フラグ (data/stop_requested.flag) による終了監視、KeyboardInterrupt のハンドリング、DB 接続のクローズ処理を実装。
- 設定管理
  - config.py: Settings クラスを追加し、環境変数のラッパーを提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml により検出）を基準に .env/.env.local を自動読み込み（OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須環境変数取得のヘルパー (_require) と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス、Paper trading 設定、監視閾値、ログレベルなど）を実装。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のデフォルト値。
- 設定ユーティリティ・CLI
  - config_setup.py: インタラクティブな .env 作成ウィザードを追加。
    - デフォルト項目群（KABUSYS_ENV, トークン類, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話式に入力・保存可能。
    - .env の既存値読み取り、秘密項目のマスク表示、保存確認を実装。
  - validate_config.py: 起動前に環境変数・config/*.yaml の不備を検出する CLI を追加。
    - --strict オプションで警告を FAIL 扱いにできる。
    - 必須/任意環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、PyYAML が存在する場合は YAML ファイルのパース検証、本番環境向けの追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の警告）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler, 30 日保持）をルートロガーへ設定。
    - ログディレクトリの解決（引数 > 環境変数 LOG_DIR > デフォルト logs/）。ファイルハンドラ作成失敗時はコンソール出力のみで継続。
    - LOG_LEVEL 解決（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）での優先度設定を抽象化。アクセス権限不足などの例外は警告にフォールバック。
    - set_cpu_affinity による最初 N コアへの固定機能を実装（未指定時は変更なし）。
- ポートフォリオ構築ライブラリ（pure function）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分、全てのスコアが 0 の場合は等配分にフォールバック（warning）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存エクスポージャが max_sector_pct を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 でフォールバックし警告を出力。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を決定。
    - risk_based: 損切り・リスク率からベース株数を計算し単元（lot_size）で丸め。
    - equal/score: ウェイトに基づく割当、per-position と aggregate の上限を考慮。cost_buffer を使った保守的見積。
    - 需要に応じたスケーリングロジック（available_cash を超えた場合の縮小と余剰配分）を実装。ロット単位での端数取り扱いと再現性を担保。
    - 複数の保護（価格未取得時のスキップ、単元丸め、per-stock 最大数計算）を実装。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加（DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシを集計）。
    - デフォルト閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。PASS/FAIL レポートを標準出力へ出力。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db) をサポート。P95 計算と欠測値に対する N/A 表示を実装。
- リサーチ/ファクター
  - research/factor_research.py（部分実装）:
    - Momentum 等のファクター計算（mom_1m, mom_3m, mom_6m, ma200_dev 等）の方針と一部実装開始。DuckDB 接続により prices_daily / raw_financials を参照して計算する設計。

Changed
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に列挙。

Fixed
- （初期リリースのため特定の bug fix 履歴はなし。実装中の安全弁や例外処理を多数追加。）

Known issues / Notes / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積りされ、ブロックが外れる可能性がある旨の TODO を残しています（将来的に前日終値等のフォールバック価格を採用する予定）。
- position_sizing:
  - 将来的に銘柄別 lot_size をサポートするための拡張予定が明記されています（現状は共通 lot_size）。
- research/factor_research.py:
  - ファイル末尾が途中で切れているため、Momentum 計算の詳細実装が未完（以降のファクター実装も継続予定）。
- run_monitoring.py:
  - 監視は常に Settings.sqlite_path（本番用）を使う仕様のため、paper_trading と monitoring の DB 分離が必要な場合は運用上の注意が必要。
- 権限・環境依存の処理:
  - set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出してスキップする設計。期待する効果を得るには適切な権限とプラットフォームのサポートが必要。

ライセンス・貢献
- 初期リリース。以降の変更はこの CHANGELOG に追記してください。