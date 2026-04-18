# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
リンク先: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- リポジトリの初期機能群に対する最終調整・ドキュメント補完。
- factor_research モジュールの実装途中（モメンタム計算など）を追加（実装継続の目印）。

### Known issues / TODO
- src/kabusys/research/factor_research.py が途中で切れている（`start_da` の途中で終端）。継続実装が必要。
- apply_sector_cap 内の価格欠損時のフォールバック（前日終値等）について TODO コメントあり。
- 単元株 (lot_size) の銘柄別対応は将来的な拡張予定。

---

## [0.1.0] - 2026-04-18

初回リリース — KabuSys のコア機能を実装。

### Added
- 基本パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報（`__version__ = "0.1.0"`）を追加。

- 環境設定・読み込み
  - .env ファイル自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env のパース機能: コメント、`export KEY=...` 形式、クォート文字列、インラインエスケープを適切に処理。
  - 環境変数読み込み順序: OS 環境 > .env.local > .env。
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - Settings クラスを提供し、主要な設定値（API トークン、DB パス、ログレベル、各種閾値、環境判定フラグ等）をプロパティとして取得可能。

- 設定ウィザード / 検証 CLI
  - src/kabusys/config_setup.py:
    - 対話式ウィザードで .env を初期作成 / 更新する機能を提供。
    - 質問項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL 等）。
  - src/kabusys/validate_config.py:
    - 起動前に .env と config/*.yaml の検証を実行する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が存在する場合）。
    - 本番環境（KABUSYS_ENV=live）向けの追加警告（LINE 通知や Kill Switch 設定など）。

- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout） + TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時にはファイル出力をスキップして標準出力のみで継続。
    - ログレベル・ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）。
  - src/kabusys/utils/process_priority.py:
    - プラットフォーム依存差分を吸収するプロセス優先度設定。
    - Windows / POSIX（Linux/Mac/FreeBSD）対応で high/normal/low を指定可能。
    - CPU affinity を最初 N コアに固定するユーティリティを追加。
    - 許可エラーや未対応 OS では安全にフォールバックし警告を出す。

- 実行系 / 監視スクリプト
  - src/kabusys/run_execution.py:
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動・停止（stop flag / pid ファイル管理）。
    - プロセス優先度を起動時に "high" に設定。
  - src/kabusys/run_monitoring.py:
    - SystemMonitor ポーリングループの起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視 DB は環境にかかわらず本番用 sqlite_path を使用する（意図的分離）。
    - 停止フラグファイルを検知してループを終了。

- 監視 DB 初期化ユーティリティ
  - run_* スクリプトから呼ばれる init_monitoring_db によって監視テーブルが存在することを保証（冪等処理）。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading データベース（SQLite）から稼働率、注文成功率、送信率、レイテンシ等の指標を集計してレポートを生成する CLI。
    - P95 レイテンシ計算、基準値による PASS/FAIL 判定（しきい値はソース内で定義）。
    - コマンドライン引数で期間指定 (--from / --to) および DB パス指定可能。
    - DB が存在しない場合の明確なエラーメッセージ。
    - SQL 実行時の OperationalError を想定した保護処理。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - シグナル選定（score 降順、タイブレークに signal_rank）と候補絞り込み。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコア 0 の場合は等金額にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）：既存保有のセクター比率が上限を超える場合に新規候補を除外。
    - レジームに応じた乗数（calc_regime_multiplier）："bull" / "neutral" / "bear" をマップし、不明レジームは警告して 1.0 でフォールバック。
  - src/kabusys/portfolio/position_sizing.py:
    - 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベース、等配分、スコア配分に基づくターゲット株数計算、単元株（lot_size）丸め、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - コストバッファ（手数料・スリッページ見積り）を考慮した安全なスケールダウンと余剰配分ロジック。
  - src/kabusys/portfolio/__init__.py で上記関数を公開。

- リサーチ / ファクター計算（部分実装）
  - src/kabusys/research/factor_research.py:
    - モメンタム、移動平均乖離、ATR、流動性等のファクター設計（Docstring と定数を実装）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。
    - 現時点ではモジュールの一部が実装済み（定数、関数シグネチャ、説明）。計算ロジック続行中。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- 環境変数やシークレットは .env に保存するが、生成スクリプトのヘッダに「.env を絶対に Git にコミットしないこと」を明記。

---

開発者向け補足
- ログ出力は標準で stdout を使用する（cron 等で stdout/stderr を一本化する運用に配慮）。
- process priority / affinity の設定は権限不足時に安全にフォールバックし、ログで警告を出す設計。
- Paper Trading と Live のデータ分離を明確に行っている（paper_sqlite_path を利用）。
- CLI エントリポイント:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

以上。必要であれば各コミット単位に分解した詳細な変更履歴や、未実装箇所のチケット提案リストを作成します。どちらを優先しますか？