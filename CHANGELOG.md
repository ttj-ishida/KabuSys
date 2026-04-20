# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般:
- 初期バージョンの機能群を追加（システム監視・実行エンジン起動スクリプト、設定管理、設定ウィザード、検証ツール、ポートフォリオ構築ロジック、ユーティリティ群、Paper Trading 検証レポート 等）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

### Added
- 全体
  - パッケージ初期リリース。モジュール群を追加。
  - バージョン: `kabusys.__version__ = "0.1.0"`

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はリポジトリ直下 data/stop_requested.flag の存在検知で行う。
    - 監視用 DB は環境にかかわらず production の sqlite_path を使用して接続・初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Mock ブローカーを利用し、paper_trading 用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル管理（data/execution.pid）に対応。
    - ExecutionEngine を別スレッドで起動し、停止フラグで安全に停止可能。

- 設定管理
  - config.py: Settings クラスを追加（環境変数/ .env ファイルから設定を読み込む）。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - `.env` / `.env.local` の読み込み順と上書き保護（OS 環境変数を保護）を実装。
    - 各種設定プロパティ（DB パス、PID ファイル、閾値、環境種別判定、paper_trading 関連設定 等）。
    - `PAPER_FILL_MODE` （`instant|partial|never|reject`）のバリデーション。
    - `PAPER_TRADING_SQLITE_PATH` をサポート。

- 設定支援 / 検証ツール
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 秘密値のマスク表示、選択肢・デフォルト、保存前の確認を提供。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ確認、config/*.yaml の存在および（PyYAML がある場合は）パース検証、`--strict` モードをサポート。
    - KABUSYS_ENV=live の際の本番ガード（LINE 通知未設定や Kill Switch の自動クリア設定に関する警告）を追加。

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
    - ログレベル解決順・ログディレクトリ解決順を明確化。ディレクトリ作成失敗時はファイルロギングを無効化して stdout のみにフォールバック。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/macOS/FreeBSD) を抽象化して nice / Windows 優先度クラスを設定（失敗しても警告でスキップ）。
    - set_cpu_affinity により最初の N コアにピン留めする機能を提供（アクセス権限により失敗する場合は警告）。
    - 起動スクリプトでプロセス優先度を "high" に設定する利用例あり。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークロジックで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限の適用ロジック（既存ポジションのエクスポージャ計算、当日売却予定の除外など）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）を実装。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて株数を計算。
    - 単元株（lot_size）丸め、per-position および aggregate cap、cost_buffer を用いた保守的見積り、比例スケーリングと端数処理（fractional remainder による再配分）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の SQLite データから稼働率（uptime）、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を集計してコンソール出力するレポート機能を追加。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - P95 計算、日付フィルタ（--from / --to）をサポート。閾値に基づく PASS/FAIL 判定を導入。

- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 接続を受けて各種ファクター（Momentum / Value / Volatility / Liquidity）を計算するための設計とモジュール雛形を追加（モメンタム関数等を実装開始）。

- パッケージ構成
  - 各モジュールの __all__ エクスポートを整備（portfolio/__init__.py 等）。
  - tools パッケージおよび必要なプログラムエントリポイントを提供。

### Changed
- 環境変数の読み込み仕様
  - .env パーサーの挙動を明確化（export プレフィックス対応、クォート内のバックスラッシュエスケープ、コメント処理ルール）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env の読み込み順: OS 環境 > .env.local > .env（.env.local は上書き、ただし OS 環境は保護）。

- ロギングの動作
  - StreamHandler は stdout に出力するように仕様決定（cron/Task Scheduler でのリダイレクト運用を考慮）。

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報の取り扱いに関するガイダンスを .env 生成ファイルへ明示（.env を Git にコミットしない等）。

### Notes / Known limitations
- research/factor_research.py は実装途中の箇所（ファイル末尾が切れている / 実装継続が必要）。
- position_sizing の price フォールバックロジックは未実装（price が 0.0 だった場合の過少見積りリスクに関する TODO コメントあり）。
- ファイル・ディレクトリ作成やプロセス優先度設定は権限に依存するため、権限不足時は警告ロギングでフォールバックする挙動になっている。
- validate_config の YAML 検証は PyYAML 未インストール時はスキップされる。

---

以上がこのコードベースに基づいて推測した CHANGELOG（Keep a Changelog 準拠）の内容です。必要であれば個々の変更に対するより詳細な説明や抜粋（関連ソースファイル/関数名を含む）を付け加えます。