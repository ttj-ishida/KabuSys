# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
安定版リリースや重要な実装追加・修正の要点を日本語でまとめています。

全般:
- Semantic Versioning を意識（パッチ / マイナー / メジャー区分）。
- リリース日: 2026-04-18

## [Unreleased]
（現時点での未リリースの作業項目・既知の注意点）
- research/factor_research.calc_momentum の実装が途中（ファイル末尾で切れている）。継続実装が必要。
- 細かなエラーハンドリングや追加テストの整備が残存。
- 将来的に銘柄ごとの lot_size を stocks マスタ等でサポートする拡張検討中（TODO コメントあり）。

---

## [0.1.0] - 2026-04-18

### Added
- 初回リリースとして以下の主要機能を実装・追加。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動用エントリポイントを実装。
      - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite を使用して本番 DB と完全分離。
      - プロセス優先度を起動直後に "high" に設定する仕組みを組み込み。
      - 停止フラグ（data/stop_requested.flag）検知で安全にシャットダウン。
      - 実行中の PID 管理用の execution.pid ファイルパスを利用。
    - run_monitoring.py
      - SystemMonitor（監視ループ）起動用エントリポイントを実装。
      - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
      - 監視は環境に依らず本番用 sqlite_path を使用。
      - 停止フラグ検知で監視ループを終了。
  - 設定管理・CLI
    - config.py
      - .env 自動読み込み（.env, .env.local）機能を実装（OS 環境変数優先、保護）。
      - .env パーサは export プレフィックス・クォート・エスケープ・インラインコメントに対応。
      - Settings クラスを提供し、環境変数経由で各種設定（DB パス、API トークン、閾値等）を取得可能。
      - KABUSYS_ENV / LOG_LEVEL 等の検証ロジックを含む。
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新が可能。
      - J-Quants / kabu API / DB パス / ログレベル / Kill Switch の設定項目を網羅。
      - 既存 .env の読み込み・マスク表示・書き込み機能を実装。
    - validate_config.py
      - 起動前に .env と config/*.yaml を検証する CLI 実装。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML の読み取り検証（PyYAML がある場合）など。
      - --strict オプションで警告も失敗扱いにできる。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なロギング設定ユーティリティを実装。
      - stdout への StreamHandler と日次ローテーション付き TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）を設定。
      - 既存ハンドラをクリアして二重設定を防止。
      - LOG_DIR 環境変数や引数でログディレクトリを上書き可能。作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py
      - Windows / POSIX 差分を吸収するプロセス優先度設定ユーティリティ。
      - set_process_priority(level)（high|normal|low）で優先度を設定、失敗時は警告ログでスキップ。
      - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定する機能（未指定時は何もしない）。
  - ポートフォリオ構築（純関数群）
    - portfolio/portfolio_builder.py
      - 銘柄選定 select_candidates（スコア降順、同点は signal_rank 昇順）と重み計算 calc_equal_weights / calc_score_weights を実装。
      - calc_score_weights は全スコア 0 の場合に等金額配分へフォールバックして警告ログを出力。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限を適用する関数を実装。売却予定銘柄はエクスポージャー算出から除外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear。未知レジームは 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes 実装（allocation_method="risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）でのスケールダウン、cost_buffer による保守的見積り等を実装。
      - aggregate スケール時の残差処理（lot_size 単位での追加配分）を実装。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを実装。
      - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）等を算出・判定（閾値はソース内定義）。
      - P95 計算の実装と期間指定 (--from / --to) によるフィルタリングをサポート。
  - monitoring
    - monitoring_db 初期化フックを各起動スクリプトから呼び出すことで監視テーブルの存在を保証（冪等な初期化）。
  - パッケージ基盤
    - __init__.py によりパッケージメタ情報（__version__ = "0.1.0"）を追加。

### Changed
- （初回リリース）コードベース整備に伴う初期設計方針の明文化:
  - .env の自動ロードはデフォルト有効。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基に行い、CWD に依存しない設計。
  - logging_setup は stdout を使用することで cron / Task Scheduler 等でのリダイレクト運用を考慮。
  - run_monitoring と run_execution は起動時にプロセス優先度を設定し、Data/flag による外部制御を想定。

### Fixed
- .env パーサの堅牢化:
  - export プレフィックスの処理、クォートされた値内でのバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応。
  - 不正な環境変数値は適切に警告・例外で処理（Settings のプロパティで妥当性チェック）。
- logging_setup:
  - ログディレクトリ作成に失敗した場合にファイルハンドラ作成をスキップしてもプロセスが続行するように改善。

### Known issues / Notes
- research/factor_research.calc_momentum がファイル末尾で切れているため、ファクター計算の一部が未完成。リリース後の追実装予定。
- position_sizing の price フォールバック（価格が欠損した場合の代替ソース）は未実装（TODO コメントあり）。欠損時は対象銘柄をスキップする仕様。
- set_process_priority や set_cpu_affinity は権限不足や未対応プラットフォームで例外を投げず警告でスキップする挙動。運用環境では適切な権限付与が必要。
- Paper Trading と本番 DB は分離設計だが、運用時の誤設定（環境変数混在等）に注意。

---

## 出典 / 参考
- この CHANGELOG はコードベース（src/kabusys 以下）から推測して作成したリリースノートです。実際の運用・仕様変更はプロジェクトの公式ドキュメントに従ってください。