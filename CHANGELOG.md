# Changelog

すべての notable な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。<br>
リリース日付はコードベースの参照日を基準に推測しています。

## [Unreleased]

- 次期リリースでの予定（コード内コメント・TODO に基づく）
  - research モジュールのファクター計算（momentum 等）の実装完了
  - 銘柄ごとの単元株サイズ（lot_size）をマスタから取得する拡張
  - 価格欠損時のフォールバックロジック（前日終値や取得原価など）実装
  - テストカバレッジの整備（特に position sizing / risk adjustment 周り）
  - 監視・実行プロセスのより詳細なメトリクス収集・アラート強化

---

## [0.1.0] - 2026-04-23

初期公開リリース。以下の主要機能・設計を含みます。

### Added
- 基本アーキテクチャと起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプト。環境に応じて paper_trading 用 DB を使い分け、停止フラグ検知・スレッド実行制御を提供。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を制御可能。
- 環境設定・CLI ツール
  - config_setup.py: .env の対話式ウィザード（作成・更新支援）。
  - validate_config.py: .env や config/*.yaml の起動前検証ツール（--strict オプションをサポート）。
- 設定管理
  - config.py: 自動 .env ロード（プロジェクトルート検出）、環境変数パース（クォート、エスケープ、インラインコメント対応）、Settings クラスによる集中管理。環境値の妥当性チェック（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL など）を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を使った統一ログ設定。ログディレクトリ自動作成とフォールバック処理。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティ（Windows/Linux/macOS を考慮）。set_process_priority/set_cpu_affinity を提供し、権限不足時は安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア順ソートと上位 N 選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全ゼロ時は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑制するフィルタリング（売却予定銘柄と unknown セクター取り扱い）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の配分方式に対応した株数計算。単元株丸め、per-position 上限、aggregate cap によるスケール調整（cost_buffer を考慮）。
- 実行系の依存組み立て（コード参照）
  - run_execution は BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等を組み合わせて ExecutionEngine を起動する設計を提供（paper_trading 時は専用 DB を使用）。
- 監視系
  - run_monitoring は SystemMonitor を使った監視ループを実装。監視 DB は環境にかかわらず本番 sqlite_path を参照する仕様。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper_trading の SQLite DB を解析して稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを集計・判定するレポート生成。閾値（稼働率 99%、成立率 90% 等）による PASS/FAIL 判定を実装。
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" とエクスポート定義を追加。

### Changed
- ログ出力の標準化
  - 全スクリプトから utils.setup_logging を呼び出すことでログ挙動を統一（ファイル名は app_name に基づく）。
- .env 自動ロード仕様
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。OS 環境変数を保護する protected 処理を導入。
- DB パスの振る舞い
  - ExecutionEngine 起動時は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を優先して使用する（本番 DB と分離）。
  - Monitoring 初期化は環境にかかわらず本番 sqlite_path を使用する旨を明確化。

### Fixed / Robustness
- 環境変数パースの堅牢化
  - クォート有り/無し両ケース・バックスラッシュエスケープ・インラインコメントなどを考慮した .env 行パーサを実装。無効行は無視。
- ログハンドラの重複登録防止
  - setup_logging は既存ハンドラを flush/close してから再設定することで二重出力を防止。
- プロセス優先度設定の安全化
  - psutil のプラットフォーム差分や権限不足を例外ハンドリングして、失敗時は警告を出し処理を継続。
- MONITOR_POLL_INTERVAL の不正値対応
  - run_monitoring で環境変数が不正（ゼロ・負・非整数）の場合、警告を出してデフォルト 60 秒にフォールバックする。

### Notes / Known limitations
- portfolio.position_sizing.calc_position_sizes:
  - price の欠損（0.0）時にエクスポージャが過少見積りされる可能性がある旨の TODO コメントあり（将来的な前日終値フォールバック検討）。
  - 単元株数は現状グローバルな lot_size 引数で指定。将来的に銘柄別の lot_map を想定。
- research/factor_research.py:
  - ファイル冒頭でファクター計算の設計が記載されているが、calc_momentum の実装が途中（切れている）であり追加実装が必要。
- config/*.yaml の検証は PyYAML が存在する場合にのみパース検査を行う（インストール要件に依存）。

---

メジャー/マイナー/パッチの分類:
- 本初期リリースは機能追加を中心とした v0.1.0（Initial release）です。

もし CHANGELOG に記載してほしい追加の観点（例: 各モジュール別の詳細変更履歴、将来の改善優先度、リリース手順など）があれば教えてください。必要に応じて追記・修正します。