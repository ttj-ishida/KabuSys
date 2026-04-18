# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

初回リリース。

### Added
- 基本アプリケーション構成
  - パッケージ初期化 (src/kabusys/__init__.py) にバージョン "0.1.0" を追加。
- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db を想定）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由して本番/モックのブローカークライアントを切替。
    - ExecutionEngine を別スレッドで起動し、stop フラグ検知で安全終了。
    - 標準的なリスク管理設定（RiskConfig のデフォルト値）を組み込み。
  - システム監視（SystemMonitor）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず指定された sqlite_path（本番想定）を使用して監視テーブルを初期化。
    - 停止フラグファイル (data/stop_requested.flag) による外部停止制御をサポート。
    - プロセス優先度を起動時に "high" に設定する処理を組み込み。

- 設定管理とワークフロー支援
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - .env / .env.local の自動ロード（プロジェクトルート検出ロジックを用いる）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - export KEY=val、クォート、インラインコメント等を考慮した堅牢な .env パーサー実装。
    - 多数の設定プロパティを提供（J-Quants トークン、kabu API、DB パス、paper trading 設定、監視閾値、環境種別など）。
    - PAPER_FILL_MODE の検証、paper_sqlite_path、PID／kill flag 関連のデフォルトを提供。
  - .env を対話式に生成・更新するウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 項目定義、既存 .env 読込、シークレットマスク表示、確認プロンプト、保存機能を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスと config/*.yaml の存在・パース検証（PyYAML がない場合は警告）を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（スコアが全て 0 の場合のフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率に基づき新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投入資金乗数（bull/neutral/bear をマップし、不明値はフォールバックと警告）。
  - 位置サイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づき発注株数を算出。
    - 単元株丸め（lot_size）、per-stock 上限、aggregate cap（available_cash を超える場合のスケーリングと残差配分）を実装。
    - cost_buffer を用いた保守的コスト見積もり、価格欠損時のログ出力などの実装。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 系の差分を吸収して優先度設定（high/normal/low）を提供。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を実装。
    - 設定失敗時は警告でフォールバック（権限不足や未対応 OS に配慮）。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20 等）、流動性指標の計算を DuckDB 上の prices_daily テーブルを参照して実装。
    - スキャンレンジ・ウィンドウサイズは定数化。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポート出力。
    - 判定基準（稼働率 99%、成立率 90% 等）と PASS/FAIL 判定ロジックを搭載。
    - --from / --to / --db オプションをサポート。

- DB 初期化 / 連携
  - 監視用 DB 初期化呼び出し（init_monitoring_db）を run_monitoring/run_execution の起動シーケンスに統合。
  - DuckDB 接続を分析処理と ExecutionEngine に提供。

### Changed
- なし（初回リリースのため新規追加中心）。

### Fixed
- なし（初回リリース）。

### Notes / Implementation details
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、実行カレントディレクトリに依存しません。
- .env 読み込みの挙動:
  - OS 環境変数を保護（.env.local の上書き時にも既存 OS 環境変数を保護）。
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応。
- run_monitoring は監視専用に sqlite_path を明示的に使う設計（環境に依らず本番の監視 DB を利用することを想定）。
- run_execution は paper_trading 用に DB とブローカーを分離することで、本番運用とテストを明確に切り分け。
- position sizing の aggregate cap スケーリングは残差再配分ロジックにより再現性と公平性を考慮している。

### Security
- .env を生成する際に「絶対に Git にコミットしないこと」を README コメントで明示。

----

変更点や不明点について追記が必要でしたら、どのモジュール・機能について詳しく記載するか指示してください。