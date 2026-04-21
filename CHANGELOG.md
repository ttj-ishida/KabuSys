# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
（リリース日付はソースコードから推定したものを使用しています）

## [Unreleased]

- なし（次回リリースに向けた未反映の変更点があればここに記載します）

## [0.1.0] - 2026-04-21

初回公開リリース。以下の主要機能・ユーティリティを実装しています。

### Added
- 全体
  - パッケージの初期バージョンを定義（kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB/SQLite を用いたデータ処理・永続化の統合（Settings にパス指定、各起動スクリプトで接続）。
- 実行系
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - ExecutionEngine を組み立ててバックグラウンドスレッドで実行。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading 環境時は Mock を期待）。
    - paper_trading 環境向けに専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）で本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出で安全にシャットダウン。execution.pid に PID を記録する仕組みの採用を想定。
    - RiskManager, OrderManager, OrderRepository, Reconciler 等の依存コンポーネントを組み合せる初期実装。
- 監視系
  - 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用（監視データの一元化）。
    - stop_requested.flag 検知でループを終了、例外発生時はログに例外情報を残して次周期へ（堅牢化）。
- 設定周り
  - Settings クラス（src/kabusys/config.py）による環境変数ラッパー実装。
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 各種設定プロパティ（DBパス、PIDパス、監視閾値、PAPER_FILL_MODE 等）を提供。
    - KABUSYS_ENV / LOG_LEVEL 等の検証を組み込み。
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）。
    - .env の読み書き、既存値再利用、シークレット値のマスク表示、保存確認。
    - .env にコミットしない旨のヘッダを自動追加。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DBパスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict オプションで警告を失敗扱いにするモードを提供。
- ロギング・プロセス管理
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラと日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL を考慮した解決順と、ログディレクトリ作成失敗時のフォールバック。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を跨いだ優先度設定（"high"/"normal"/"low"）と cpu_affinity 設定を提供。権限不足等は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全て 0 の場合のフォールバックを備える。
  - セクター集中チェック・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター上限超過時に当該セクター銘柄を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に基づく投下資金乗数（未定義レジームは警告の上 1.0 フォールバック）。
  - 株数決定・投下資金制約（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式に対応。lot_size（単元株）で丸め、aggregate cap を超える場合はスケーリング＋端数配分ロジックを実装。
- 解析・レポート
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等の集計・判定。閾値による PASS/FAIL を出力。
    - --from/--to/--db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先して DB を解決。
- リサーチ
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - Momentum/Value/Volatility/Liquidity の設計方針と定数、calc_momentum 等の骨組みを実装（DuckDB 経由で prices_daily / raw_financials を参照する設計）。

### Changed
- 環境読み込みロジックの改善（src/kabusys/config.py）
  - .env のパースで以下に対応:
    - export プレフィックス（export KEY=...）のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし行のインラインコメント扱い（'#' 前が空白/タブの場合のみコメントとみなす）
  - OS 環境変数を保護（.env 上書き時に保護）する仕組みを導入。
- ログ設定（src/kabusys/utils/logging_setup.py）
  - 既存ハンドラがある場合は一旦 flush/close してから再設定（重複出力防止）。
  - 標準出力は stdout を使用する方針を明示（cron/Task Scheduler のリダイレクトを考慮）。
- 監視・実行スクリプトの堅牢化
  - 例外発生時のログ出力強化（monitor.check_once() での例外をキャッチして継続）。
  - 停止フラグの事前検査（起動直後に停止フラグが立っている場合は起動せず終了）。
- 設定検証（src/kabusys/validate_config.py）
  - PyYAML がない場合は YAML 検証をスキップして警告を出す。config/*.yaml の存在チェックとパースエラー報告を実装。
  - 本番環境向け追加ガード（LINE の未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）。

### Fixed
- process_priority のクロスプラットフォーム対応で、psutil のプラットフォーム固有定数がない場合でもロード時に失敗しないように getattr フォールバックを導入。
- .env 読み込み失敗時の警告出力を warnings.warn で行い、フォールバック動作を安定化。

### Security / Usability
- config_setup の対話でシークレットは画面表示時にマスク表示。
- .env ファイル作成時に「絶対に Git にコミットしないこと」を明記するヘッダを自動挿入。
- validate_config によるスタートアップ前チェックで重大な設定漏れを検出できるようにし、運用ミスの抑止を図る。

---

今後の予定（推定）
- factor_research の各ファクター計算（calc_momentum の完全実装など）を完了してユニットテストを追加。
- ExecutionEngine / OrderManager 周りの統合テスト、paper_trading の MockBrokerClient の完全な実装と検証。
- Noramlize/標準化ユーティリティ（Zスコア等）や stocks マスタの導入による lot_size 銘柄別対応。

備考: 上記はソースコード内容から推測した初期リリース向けの変更履歴です。実際のコミット履歴やリリースノートと異なる可能性があります。必要であれば差分（ファイル単位／機能単位）や追加の注記を反映して更新します。