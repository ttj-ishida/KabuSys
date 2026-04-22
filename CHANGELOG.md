# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-22
初回リリース。自動売買システム「KabuSys」の基盤機能を実装しました。主な追加内容は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: `__version__ = "0.1.0"`）。

- 環境・設定管理
  - Settings クラスによる環境変数ラップ（src/kabusys/config.py）。
    - J-Quants / kabuステーション / LINE / DB /監視・閾値などのプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の検証、is_live/is_paper/is_dev の簡易判定を追加。
    - Paper Trading 関連設定（paper_sqlite_path、paper_fill_mode）とそのバリデーションを実装。
    - kill フラグ関連設定（kill_flag_path、kill_flag_clear_on_start）、監視閾値（CPU/MEM/DISK）を追加。
  - .env 自動読み込み機能を追加（プロジェクトルート自動検出: .git / pyproject.toml を基準）。
    - .env と .env.local を読み込む優先順を実装。OS 環境変数の保護機能あり。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env ファイルのパース機能を強化（引用符付き値、export KEY=val 形式、インラインコメントの扱い等に対応）。

- 環境設定 / 検証 CLI
  - 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）。
    - 必須/任意項目、マスクされるシークレット表示、確認・保存機能を提供。
  - 設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パスや config/*.yaml の存在・パースチェック、live 環境向けガード等。
    - --strict オプションで警告を失敗扱いにできる。

- 実行 / 監視起動スクリプト
  - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 実行中の停止フラグ（data/stop_requested.flag）検知と PID ファイル管理（data/execution.pid）。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知、例外キャッチでループ継続する耐障害性。

- ロギング / プロセス制御ユーティリティ
  - 統一ロギング初期化ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と 日次ローテーションされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続可能。
    - LOG_LEVEL / LOG_DIR /引数でのオーバーライドをサポート。
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収する API を提供。
    - set_process_priority("high" | "normal" | "low")、set_cpu_affinity(n) を実装。
    - 権限不足等の環境では警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 候補選定と重み付け（portfolio_builder.py）
    - select_candidates: スコア降順・タイブレークによる並べ替えと上位 N 選出。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有を元にセクター上限（max_sector_pct）を超えるセクターの新規候補を除外。unknown セクターは上限の対象外。
    - calc_regime_multiplier: market regime に対する投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知値は 1.0 にフォールバック。
  - 株数決定・資金制限（position_sizing.py）
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、個別上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、残差処理（fractional remainder に基づく追加配分）を実装。
    - 不足データ（価格がない等）に対するスキップとログ出力。

- 解析 / 検証ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading DB（デフォルト: data/paper_trading.db）から集計を行い、稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を算出。
    - PASS/FAIL 判定の閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付フィルタ (--from / --to)、DB 指定 (--db) をサポート。

- 研究用ファクター計算（基礎実装）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - Momentum, Value, Volatility, Liquidity 系の計算方針を定義。DuckDB 接続を受けて prices_daily / raw_financials テーブルから計算する設計。

### Changed
- ログ出力ポリシー
  - stdout を標準出力に統一（stderr ではなく stdout を使用）して cron / スケジューラからのリダイレクト運用を容易に。

- DB の扱い
  - 監視（monitoring）は環境に関わらず本番 sqlite_path を使用して監視情報を保持（明示的な分離ポリシー：実行エンジンは paper_trading 時に専用 DB を使用）。

### Fixed
- 環境変数パースの頑強化により、.env の引用符・エスケープ・コメント処理で誤解釈されるケースを修正。
- process_priority / CPU affinity の呼び出しで未サポートプラットフォームや権限不足時にクラッシュする問題を防止（警告出力で安全にスキップ）。

### Notes / その他
- 一部モジュール（研究用ファクター計算など）は設計稿や TODO コメントを含み、今後の拡張（欠損価格のフォールバック、銘柄別 lot_size 管理など）を予定しています。
- 本リリースは主に基盤・運用（設定、ログ、監視、実行管理）とポートフォリオ構築・発注ロジックのコアを実装することを目的としています。

---

参考:
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定関連: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ポートフォリオ: src/kabusys/portfolio/*
- ユーティリティ: src/kabusys/utils/*
- ツール: src/kabusys/tools/paper_verification_report.py

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース履歴や日付はプロジェクト運用方針に合わせて調整してください。）