# Changelog

すべての注目すべき変更履歴を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased: 開発中の変更（リリース前に編集）
- 各バージョン: 実装された機能・変更点をカテゴリ別に記載

---

## [Unreleased]

- （なし）

---

## [0.1.0] - 2026-04-20

初期リリース。以下の主要機能とユーティリティを実装しました。

### Added
- 基本アプリケーション情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境/設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（src/kabusys/config.py）。
  - .env ファイルパーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。空行・コメント行の扱い、上書き制御（protected）をサポート（src/kabusys/config.py）。
  - Settings クラスを追加し、主要な環境変数アクセスをプロパティで提供（J-Quants、kabu API、DB パス、監視閾値、環境判定等）（src/kabusys/config.py）。
  - 対話式の環境設定ウィザードを追加（.env の初期作成・更新支援）。デフォルト、シークレット入力、選択肢表示、保存確認を実装（src/kabusys/config_setup.py）。

- 設定検証ツール
  - validate_config CLI を追加し、必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば）を検証。--strict モードで警告を失敗扱いにできる（src/kabusys/validate_config.py）。

- 実行/監視プロセス起動スクリプト
  - 実行エンジン起動スクリプトを追加（run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動処理（スレッド駆動）。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。PID ファイル管理と DB 接続のクローズを保証。
  - 監視ループ起動スクリプトを追加（run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出す。
    - 監視（SystemMonitor）用 DB 初期化を行い、例外発生時もループ継続する堅牢な実行 / KeyboardInterrupt のハンドリングを実装。
    - 監視は環境に関わらず本番 sqlite_path を参照する設計を採用（運用上の注意点を明示）。

- ロギング/プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール（stdout）出力と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する安全設計。
    - ログレベルとログディレクトリ解決の優先順を実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する実装。psutil を用いて優先度設定、CPU 固定を行い、権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築モジュール
  - 銘柄選定・重み付け関数を実装（select_candidates, calc_equal_weights, calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順、signal_rank によるタイブレークなどの挙動を明確化。
  - セクター集中制限とレジーム乗数ロジックを実装（apply_sector_cap, calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター別エクスポージャ計算、上限超過セクターの候補除外、未知レジームのフォールバック等を実装。
  - 株数決定・リスク制限・単元丸めロジックを実装（calc_position_sizes）（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた算出（risk_based / equal / score）、単元株（lot_size）単位で丸め、per-stock 上限・全体 aggregate cap のスケーリングと余剰分配アルゴリズムを実装。
    - cost_buffer による保守的見積りを考慮。

- 研究/ツール
  - DuckDB ベースのファクター計算モジュールを追加し始め（ファイル冒頭実装。prices_daily / raw_financials を前提。src/kabusys/research/factor_research.py）。
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を抽出してレポート化。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）で PASS/FAIL を判定。
    - DB 未存在時やテーブル欠損時の耐性（存在チェック・例外捕捉）を持たせる。

- その他
  - monitoring の DB 初期化関数 init_monitoring_db を実行前に呼び出し、監視用テーブル存在を冪等に保証（run_* スクリプト）。
  - 各スクリプト・ユーティリティで接続クローズや例外ハンドリングを適切に行う try/finally を実装。

### Changed
- ログ出力先の選定方針を明示
  - ログの標準ストリームは stdout を使用（cron 等のリダイレクト運用を想定）。ファイル出力はログディレクトリが作成できた場合にのみ有効（src/kabusys/utils/logging_setup.py）。

- DB パスの方針
  - 監視プロセスは環境に関わらず本番 sqlite_path を参照する決定（run_monitoring.py）。一方で実行エンジンは paper_trading モード時に paper_sqlite_path を使用して完全分離する設計（run_execution.py）。

### Fixed
- 各種堅牢性の向上
  - run_monitoring のポーリングループで check_once() が例外を投げてもループを継続するようにし、例外時にログ出力して次回ポーリングまで待機するように実装（監視の安定性向上）。
  - DB 接続や DuckDB 接続を finally で必ず閉じることでリソースリークを防止。
  - .env ファイル読み込み時のファイルアクセス失敗を警告に変換して処理を継続（テストやパッケージ配布時の堅牢性）。

### Notes
- 設計上の重要事項
  - run_monitoring は監視目的で本番監視 DB を参照するため、開発環境で起動する際は運用上の注意が必要です。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等、Paper Trading 関連の環境変数により動作が大きく変わります。config_setup／validate_config を用いた事前検証を推奨します。

---

参照:
- 各実装ファイル: src/kabusys/*.py およびサブパッケージ内のモジュール群
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/