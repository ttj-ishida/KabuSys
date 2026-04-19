# Changelog

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※ この CHANGELOG は与えられたコードベースの内容から推測して作成しています（実装コメント・ドキュメント文字列に基づく要約）。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- パッケージ初期リリース。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを追加。
    - 環境が `paper_trading` の場合は paper 用 SQLite（デフォルト: data/paper_trading.db）を使用して、本番 DB と完全に分離。
    - BrokerClientFactory によりブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) による安全な停止をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループ終了。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化のための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - 必須環境変数未設定時に ValueError を送出する `_require()` と Settings クラスを提供。
    - 各種設定プロパティ（DB パス、paper_trading 用パス、しきい値、PID / kill flag パス、環境判定メソッド等）。
    - `PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）。
- 設定ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 必須・任意・秘密情報の扱い、デフォルト値や選択肢提示、既存 .env 読み込みのサポート。
    - 保存前の確認プロンプトと .env 書き出し（テンプレートヘッダ付き）。
  - validate_config.py
    - 起動前チェック用 CLI を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース確認、ライブ環境のガード等を検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一セットアップを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベル解決順、ログディレクトリ解決順を定義。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プロセス優先度（Windows と POSIX を吸収）と CPU affinity 設定ユーティリティを実装。
    - `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(cpu_count)` を提供。権限不足等は警告でスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナルのソート・候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全ゼロの時は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック）。
    - 不明レジームや unknown セクター時のフォールバックとログ警告を実装。
  - portfolio/position_sizing.py
    - 複数の割り当て方式（risk_based / equal / score）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（利用可能現金に応じたスケールダウン）と残差処理を実装。
    - cost_buffer による保守的コスト見積りをサポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading 用 SQLite からレポートを生成する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを集計し、PASS/FAIL を判定する基準を実装（閾値はスクリプト内定数）。
    - --from / --to / --db オプションをサポート。DB が存在しない場合のエラーメッセージを実装。
- 研究用モジュール（partial）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高等の設計方針と定数を定義）。
    - calc_momentum のドキュメントと定数が含まれる（コード末尾で途中まで実装／続きありの様子）。
- パッケージメタ
  - __init__.py にてバージョンを "0.1.0" として定義。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Security
- N/A（初回リリース）

### Notes / Known issues / TODO（コード内コメントより）
- research/factor_research.calc_momentum はファイル末尾で途中に見える（未完の可能性あり）。さらなる実装が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO がある。
- position_sizing:
  - 単元株（lot_size）は現時点で全銘柄共通で 100 を想定。将来的に銘柄ごとの lot_size を持たせる拡張予定あり。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する安全設計。
- 実行時の停止・kill フラグや PID 管理に関わるファイルパスは Settings / スクリプトで提供される既定値（data/*.flag / data/*.pid）を使用。運用時は適切な場所・権限で配置すること。

---

参照:
- 環境変数の自動ロード: KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可
- 設定検証: python -m kabusys.validate_config
- 環境設定ウィザード: python -m kabusys.config_setup
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report

（以上）