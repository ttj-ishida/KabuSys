# CHANGELOG

このファイルは Keep a Changelog のガイドラインに準拠して作成されています。  
主にコードベース（src/kabusys 以下）の実装内容から推測して記載しています。

## [Unreleased]

マイナー改善・既知の改善予定点（コード内の TODO / コメントに基づく）:

- 既知の改善予定
  - risk_adjustment.apply_sector_cap:
    - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる問題があり、前日終値や取得原価などのフォールバック価格利用を検討中。
  - position_sizing.calc_position_sizes:
    - 将来的に銘柄別単元（lot_size）を stocks マスタから取得する設計に拡張予定。
  - research.factor_research:
    - モジュールは設計ドキュメントに基づいて準備されているが一部実装が途中（ファイル末尾で切れている）であり追加実装・テストが必要。
  - ロギング:
    - ファイルハンドラ作成失敗時に StreamHandler のみで継続する仕様はあるが、運用上の監視・警告周りを強化する余地あり。

- 小さな仕様調整（計画）
  - monitor のポーリング挙動や停止フラグの運用について啓蒙ドキュメントの整備。
  - Paper Trading の検証ツール（paper_verification_report）に追加メトリクスや出力フォーマットの改善。

---

## [0.1.0] - 2026-04-25

初期リリース。以下の主要機能を実装・公開しました。

Added
- 基本アーキテクチャ・起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - Engine をデーモン Thread で起動し、停止フラグ（data/stop_requested.flag）検知で graceful stop を実装。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグ検知によるループ終了処理と例外ハンドリングを実装。

- 設定管理
  - config.py
    - .env の自動読み込み機構（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 複雑な .env 行のパース対応（引用符、export 形式、インラインコメント等）。
    - 必須/オプション設定の accessor（Settings クラス）を提供。環境名・ログレベルの検証を行う。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - シークレット項目はマスク表示、選択肢・デフォルト値サポート。
  - validate_config.py
    - 起動前チェック CLI。env 値や config/*.yaml の存在・パース検証を実行。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの一元化設定。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収するプロセス優先度設定ユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 設定失敗時は警告ログでフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコアでソートして上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中度の上限チェック（既存保有時価ベース）と候補除外ロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株丸め、aggregate cap によるスケーリングと端数配分処理。
    - cost_buffer による手数料・スリッページの保守的見積りをサポート。

- Paper Trading ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果を SQLite（PAPER_TRADING_SQLITE_PATH）から読み取り、システム稼働率、注文成功率、送信率、レイテンシ（P95 含む）などを集計してレポート出力。
    - デフォルトの合格閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付範囲指定（--from / --to）や DB パス指定（--db）に対応。

- 研究・データ処理（下準備）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity といったファクター計算の設計を実装開始。DuckDB 接続を受け取り prices_daily / raw_financials を利用する設計。

- パッケージ情報
  - __init__.py にてバージョンを `0.1.0` に設定。

Changed
- 初期リリースのため該当なし。

Fixed
- 入力値の堅牢化
  - run_monitoring: `MONITOR_POLL_INTERVAL` が不正な文字列や 0 以下の値のときにデフォルト値（60 秒）にフォールバックして警告を出力する実装を追加。
  - logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラ作成をスキップし、stderr に警告を出力するようにし、アプリが停止しないように設計。

Security
- 機密情報の取扱いに関する注意
  - config_setup で生成される .env に関して「.env は絶対に Git にコミットしないこと」を明記。

Notes / Migration
- 環境変数の追加 / デフォルト
  - 新しい/重要な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（デフォルト: development）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - LOG_DIR / LOG_LEVEL
    - MONITOR_POLL_INTERVAL（monitor 用、秒）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると .env 自動ロードを無効化）
- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合、発注処理は MockBrokerClient（実装は broker_factory 側）を使い、DB は紙取引用に分離されるので、本番 DB に影響しない。

Deprecated / Removed
- なし（初期リリース）

---

メジャー機能の追加や破壊的変更を行う場合は本 CHANGELOG を更新します。問題や誤記があれば issue を立ててください。