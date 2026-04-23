# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

現行バージョン: 0.1.0

## [Unreleased]
- 開発中の小さな改善やリファクタはここに記載します。

## [0.1.0] - 2026-04-23
初回リリース（スナップショット）。以下の機能群とユーティリティを提供します。

### Added
- 全体
  - パッケージ初期リリース。モジュール群をまとめたベース実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行系 / ランタイム
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper-trading 用の専用 sqlite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を行うエントリポイント。
    - エンジンは別スレッドで起動し、 data/stop_requested.flag を監視してグレースフルに停止可能。
    - 実行 PID の記録（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データの統一性のため）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - monitor 起動時にプロセス優先度を高（"high"）に設定。

- 設定・環境
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env と .env.local の読み込み順と上書きポリシー（OS 環境変数を保護）を実装。
    - 複数の設定プロパティをラッパークラス Settings として提供（DB パス、KABUSYS_ENV 判定、paper_trading 用パス、閾値など）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）。
  - config_setup.py:
    - 対話式 .env 作成ウィザードを追加（既存 .env の読み込み・更新、シークレット項目マスク表示、保存）。
  - validate_config.py:
    - 起動前チェック用 CLI を追加（必須環境変数の存在、KABUSYS_ENV の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があれば））。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装（スコアが全て 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有を考慮したセクター集中上限チェック（max_sector_pct）を実装。売却予定銘柄の除外対応と unknown セクターの扱いを定義。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を提供（bull/neutral/bear）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - aggregate cap（available_cash を超える場合のスケーリング）、lot_size（単元）丸め、cost_buffer を考慮した安全なスケーリングを実装。

- モニタリング / DB
  - monitoring.monitoring_db の初期化呼び出しを実装（起動スクリプト内で冪等に監視テーブルを保証）。
  - DuckDB を分析用に利用するための接続ハンドルを各スクリプトで受け渡す（デフォルトパス: data/kabusys.duckdb）。

- ユーティリティ
  - utils.logging_setup:
    - StreamHandler（stdout）と TimedRotatingFileHandler（daily、30日保持）をルートロガーに設定する統一ログ設定を実装。
    - LOG_DIR / LOG_LEVEL の解決順を明示。
    - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority:
    - Windows / POSIX の差分を吸収するプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity 設定ユーティリティを追加（最初の N コアに固定、例外時は警告）。
    - 権限不足や未対応 OS を安全にハンドリング。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成ツールを追加。以下の指標を出力:
      - システム稼働率（uptime %）、総ポーリング数、エラー数
      - 注文成功率（Filled/Created）、送信率（Sent/Created）
      - リスク却下数（risk_logs）
      - レイテンシ（avg/max/P95）
    - P95 計算、期間フィルタ（--from / --to）、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）をサポート。
    - パス/閾値 (稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms) に基づく PASS/FAIL 判定を実装。

- 研究用
  - research.factor_research（ファイル冒頭を追加、モメンタム等のファクター計算を設計。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。モジュールは部分実装（未完）を含む。

### Changed
- ログの標準出力を stdout に統一（cron 等でのリダイレクト運用を考慮）。
- .env 読み込み: export プレフィックスとクォート/エスケープ、インラインコメント処理等を細かく対応。

### Fixed
- 環境変数 MONITOR_POLL_INTERVAL の不正値ハンドリング（負数・非整数はデフォルトにフォールバックし、警告を出力）。
- sqlite/duckdb のコネクションを起動後 finally で確実にクローズするように修正（リソースリーク防止）。

### Known issues / Notes
- research.factor_research の実装が途中で切れており、完全実装は未完（コメント内に設計方針あり）。
- position_sizing.calc_position_sizes:
  - 銘柄別の lot_size を将来的にサポートする旨の TODO コメントあり（現状は全銘柄共通の lot_size）。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少評価される旨の注記があり、フォールバック価格（前日終値等）導入の余地あり。
- config._load_env_file はファイル読み込みに失敗した場合警告を出すが、読み込み競合や同時書き込みへの対策（排他制御）は未実装。
- run_execution/run_monitoring はシンプルな停止フラグを使ったグレースフル停止を行うが、より堅牢なプロセス監視（外部 supervisor 連携等）は外部に委ねる設計。

### Security
- .env は「絶対に Git にコミットしないこと」を README/テンプレートで注意（config_setup に明記）。

---

開発/運用上の参考:
- 起動前に `python -m kabusys.validate_config` で設定検証を推奨。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時など）。
- Paper Trading と本番 DB は分離されているため、ペーパートレード実行時に本番データを書き込む心配は低減されている。

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）