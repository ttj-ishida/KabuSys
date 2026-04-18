# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。

注意: 本 CHANGELOG は提示されたコードベースの内容から推測して作成したものであり、実際のコミット履歴ではありません。

## [Unreleased]

- ドキュメントやテストの追加予定
- 既知の改善候補（ログ出力の細分化、価格フォールバック処理の強化など）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、実行/監視エントリポイント、ポートフォリオ構築ロジック、検証ツール群を含む最初の安定版です。

### Added

- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

- 環境設定・管理
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
    - .env / .env.local の読み込み順序と上書き保護（OS 環境変数の保護）
    - 複雑な .env 行パース（export 形式、クォート・エスケープ、インラインコメント対応）
    - Settings クラスを実装し、各種設定値（API トークン、DB パス、Paper Trading の挙動、監視閾値、ログ設定等）をプロパティとして提供
    - 環境値の検証（有効な KABUSYS_ENV / LOG_LEVEL 値のチェック、PAPER_FILL_MODE 検証等）

- 設定ウィザード & 検証ツール（CLI）
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する機能を提供
    - 秘匿値のマスク表示、選択肢／デフォルト提示、保存前の確認を実装
  - src/kabusys/validate_config.py
    - .env および config/*.yaml の事前チェック CLI
    - 必須環境変数チェック、パス存在チェック、YAML パース検証（PyYAML 未インストール時はスキップ）、本番環境向けガードチェック
    - --strict オプションで警告を失敗扱いにできる

- 実行用エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db 等）を使用し、本番 DB と分離
    - BrokerClientFactory によりブローカークライアントを生成（実ブローカー / モックを切替）
    - ExecutionEngine/OrderManager/OrderRepository/Reconciler/RiskManager を組み立ててエンジンをデーモンスレッドで実行
    - 停止フラグファイル（data/stop_requested.flag）によるソフトシャットダウン、実行 PID ファイル出力管理
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義

- 監視用エントリポイント
  - src/kabusys/run_monitoring.py
    - SystemMonitor を用いたポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）
    - 監視は常に本番向け sqlite_path を使用して監視テーブルを一元管理
    - 停止フラグファイル検知でループ終了、例外はログに出力して次ポーリングを継続

- ロギング・プロセス優先度ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通ロギング設定関数 setup_logging を実装
    - stdout StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定
    - ログレベル/ログディレクトリは引数・環境変数・デフォルトの優先度で解決
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、signal_rank でタイブレーク）
    - 等重み calc_equal_weights、スコア加重 calc_score_weights（全スコア0.0時は等重みにフォールバック）
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター別エクスポージャを計算して候補を除外）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知値は警告して 1.0 フォールバック）
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes：weights/candidates/portfolio_value/available_cash 等を元に発注株数を算出
    - risk_based / equal / score の配分方式に対応
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を加味した保守的見積り、残余キャッシュに基づく再配分ロジックを実装

- 研究・ファクター計算基盤（部分実装）
  - src/kabusys/research/factor_research.py
    - モメンタム・ボラティリティ等のファクター設計を実装（DuckDB 接続を受け prices_daily / raw_financials を参照）
    - 定数（1M/3M/6M、MA200、ATR20、ボリューム20 等）を定義
    - calc_momentum 関数など、日付窓を用いたファクター計算の土台を提供（実装は継続）

- ツール群
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）
    - --from/--to/--db オプションで期間・DB を指定可能
    - DB が存在しない/テーブル欠如の場合に graceful に N/A を出力

- DB 初期化
  - 監視用テーブルが存在することを保証する init_monitoring_db 呼び出しを run_execution/run_monitoring で実行（冪等性）

### Changed

- ログ出力の標準化
  - すべての起動スクリプトで setup_logging を呼び出し、ログ設定を統一

- プロセス開始時に優先度を上げる挙動
  - 実行/監視スクリプトの初期処理で set_process_priority("high") を実行して安定稼働を目指す

### Fixed

- 環境読み込みの堅牢化
  - .env パース処理でクォート内のバックスラッシュエスケープやインラインコメント処理を改善し、より現実的な .env 記述に対応

### Known issues / TODO

- position_sizing の価格フォールバック
  - risk_adjustment.apply_sector_cap 内の price が 0.0 の場合にエクスポージャが過少評価される可能性があり、前日終値や取得原価を用いるフォールバック機構を検討中（TODO コメントあり）
- research.factor_research.py は途中で切れているため、ファクター計算の完全実装が必要
- 一部の外部依存（psutil, duckdb, PyYAML など）に対するインストールドキュメントやエラーハンドリングの強化が望ましい

---

（末尾）
- 今後のリリースでは、戦略モジュール（signal generation / strategy backtest）や ExecutionEngine の詳細なテスト、Paper Trading の検証強化、監視アラート（LINE 連携）の実装・確認を予定しています。