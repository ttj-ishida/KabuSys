# Changelog

すべての変更は Keep a Changelog の方針に準拠して記載しています。  
訳注: 本 CHANGELOG は提示されたソースコードの内容から機能・振る舞いを推測して作成したものです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-22

Added
- 基本アプリケーション基盤を追加
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として初期リリース相当の実装を提供。
- 実行用スクリプト / デーモン的コンポーネント
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止制御ファイル `data/stop_requested.flag` を監視して安全にループを終了。
    - 監視用 DB 接続は環境に依らず本番向け `sqlite_path` を使用する仕様。
    - duckdb 接続を併用。
    - 例外発生時はログ出力のうえ次ポーリングに耐久的に継続。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - `KABUSYS_ENV=paper_trading` 時はペーパートレード用の専用 SQLite（`data/paper_trading.db` デフォルト）を使用し、本番 DB と完全分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（モック/実ブローカーを切り替え）。
    - 停止フラグ `data/stop_requested.flag` の検出で安全にエンジン停止。
    - PID ファイル（`data/execution.pid`）のサポート。
- 設定管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートの検出: .git / pyproject.toml を検索）。
    - `.env` / `.env.local` の読み込み優先度を実装（OS 環境変数は保護）。
    - 複雑な .env の解析に対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール）。
    - Settings クラスを提供し、主要な環境変数（J-Quants、kabu API、データベースパス、監視閾値、環境判定 など）をプロパティ経由で取得。
    - `KABUSYS_ENV`、`LOG_LEVEL` 等の妥当性チェックを実装（許容値チェック）。
- 設定支援・検証ツール
  - config_setup.py
    - 対話的ウィザードで初期 `.env` を生成・更新する CLI を提供。
    - 各設定項目にラベル・説明・デフォルト・選択肢を用意。シークレット項目はマスク表示。
    - .env の読み書きロジックを実装（既存値の再利用 / キャンセル挙動を考慮）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を提供。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス / YAML ファイル存在チェック、`--strict`（警告を FAIL 扱い）オプションを提供。
    - PyYAML 不在時には YAML の検査をスキップして警告を出す堅牢性を実装。
- 運用補助ツール
  - tools/paper_verification_report.py
    - ペーパートレードログ（SQLite）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）などを計算・出力。
    - レポート期間指定（--from / --to）および DB パス指定（--db / 環境変数）に対応。
    - 合格基準（閾値）を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順・同点タイブレーク）を実装（select_candidates）。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用して候補フィルタする apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは除外しない挙動等）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ見積）を考慮したスケールダウンと残差処理（fractional 残差の順に lot 単位を追加）を実装。
    - price 欠損時のスキップやログ出力の実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して stdout ストリームハンドラと日次ローテートするファイルハンドラ（TimedRotatingFileHandler）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化して標準出力のみで継続する堅牢性を実装。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な解決。
  - utils/process_priority.py
    - cross-platform のプロセス優先度設定（Windows の priority class / POSIX の nice）を実装。
    - psutil を利用し、権限不足や非対応 OS では警告のうえ安全にスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
- monitoring DB 初期化ユーティリティの呼び出し所（init_monitoring_db）を run_* から行い、監視テーブルが存在することを保証する冪等性を提供。
- research/factor_research.py（部分実装）
  - DuckDB を利用した定量ファクター計算のための骨子を追加（Momentum 等の指標、計算窓・定数の定義）。関数の実装途中で切れているが設計方針・定義は含まれる。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- （該当なし）

Notes / 備考
- 環境依存の挙動（本番/ペーパートレードの DB 分離、Kill/Stop フラグ、PID ファイル、プロセス優先度設定等）は設計上明確に分離されているため、運用時は .env の設定（特に KABUSYS_ENV、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START）とログディレクトリの権限を確認してください。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされます。CI / テスト環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

（以上）