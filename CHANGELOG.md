# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 破壊的変更 (Removed) — 必要な場合のみ

## [Unreleased]

---

## [0.1.0] - 2026-04-22

### Added
- 基本パッケージ初期実装: KabuSys 日本株自動売買システムの初期リリース。
  - パッケージバージョンは `__version__ = "0.1.0"`。

- 実行用スクリプト / ランナー
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト配下 `data/stop_requested.flag` によるフラグ検知で行う。
    - Monitoring は環境に依らず本番の sqlite_path を使用する設計。
  - run_execution: ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
    - エンジンはデーモンスレッドで実行され、停止フラグ検知で安全に停止する。
    - 実行 PID を data/execution.pid に記録する仕組み（Engine に PID ファイルパスを渡す）。

- 設定管理・検証・ウィザード
  - config.Settings クラス: 環境変数ベースの集中設定管理を提供。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定など多数のプロパティを用意。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH による paper_trading 専用 DB パスなどをサポート。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込み（OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export プレフィックスやシングル/ダブルクォート内のエスケープ、インラインコメントなどに対応。
  - validate_config: 起動前チェック CLI。
    - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML があれば内容検証）を実行。
    - --strict オプションで警告を失敗として扱う。
  - config_setup: 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - シークレット項目は入力時マスク表示、保存時もマスクして確認。
    - デフォルト値や選択肢を提示して .env を安全に生成。

- ロギング & プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定。
    - ハンドラの二重設定を防止するため、既存ハンドラをクリアして再設定する。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils.process_priority:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール (純粋関数群、DB 非依存)
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順 + 同点時 signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別の既存保有比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング、未知のレジームは警告と 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、残差処理による追加配分アルゴリズムを実装。
      - price 欠損や 0 値を安全にスキップ、必要に応じてログを出力。

- 分析・検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite DB を走査して稼働率、注文成功率、送信率、P95 レイテンシなどを集計・判定するレポートをコンソール出力。
    - しきい値（稼働率 99% など）で PASS/FAIL 判定を出力。--from / --to / --db オプションをサポート。
    - P95 計算、NULL 対応、テーブル未存在時のフォールバックを考慮。

- 研究用モジュール（骨格）
  - research.factor_research: DuckDB からデータを読み取りモメンタム等のファクターを計算するモジュールの骨格を追加（関数インターフェースと定数群を定義）。

- DB 統合
  - run_* スクリプトや各モジュールで SQLite / DuckDB の接続を使用するための基本実装を追加。
  - monitoring 初期化関数 (init_monitoring_db) 呼び出しにより監視テーブルの存在を保証（冪等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env のパースロジック強化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いを改善。
  - 無効行や空行、コメントをスキップする動作を明確化。

### Removed
- （初期リリースのため該当なし）

---

注記:
- 本リリースは初期実装をまとめたものであり、多くの機能が実用化に向けた骨格実装として提供されています。詳細な動作や運用ルール（例: 本番環境での Kill Switch 運用、PID/flag の運用フロー、各種 config/*.yaml の具体値）は運用ドキュメントや次版で追記・改善予定です。