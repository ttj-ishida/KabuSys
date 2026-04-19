# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般的な方針:
- バージョン履歴は機能追加・仕様・修正を中心に記載しています。
- 各項目には関係するモジュール／ファイルを併記しています（参照用）。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。

### Added
- 環境・設定管理機能を実装
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）
    - J-Quants / kabuステーション / LINE 等の設定プロパティを提供
    - デフォルト値・妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装
    - paper_trading 用の専用 sqlite パス（PAPER_TRADING_SQLITE_PATH）をサポート
    - KILL フラグ、PID ファイルパスやしきい値（CPU/MEM/DISK）など監視関連プロパティを提供
  - 自動 .env ロード機能を追加
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env/.env.local を読み込む
    - OS 環境変数を保護する仕組みを実装（.env.local は上書き可能だが既存 OS 変数は保護）
    - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加
    - .env の高度なパース（export プレフィックス、引用符、エスケープ、インラインコメント処理）に対応

- 対話式設定ウィザード CLI を追加（src/kabusys/config_setup.py）
  - .env の初期作成・更新を対話形式で支援
  - シークレット項目はマスク表示
  - デフォルト・説明・選択肢を提供し、最終確認後 .env を書き出す

- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・config YAML の存在・パースチェック
  - --strict オプションで警告を失敗として扱う

- 実行用スクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 環境に応じて本番 DB と Paper Trading DB を分離
    - BrokerClientFactory を通じたブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の起動管理
    - 停止フラグ（data/stop_requested.flag）による安全停止、PID ファイル管理
    - プロセス優先度を起動時に High に設定
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視用 DB は環境に依らず本番 sqlite_path を使用
    - 停止フラグ検知・例外時のログ記録・接続クローズを保証

- ロギング周りのユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ統一的に設定
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続
  - LOG_LEVEL / LOG_DIR の優先解決ルールを実装

- プロセス優先度および CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - クロスプラットフォーム対応（Windows / POSIX）
  - set_process_priority(level) で high/normal/low を設定（権限不足時は警告ログでスキップ）
  - set_cpu_affinity(cpu_count) で使用コア数を制限（未対応環境は警告でスキップ）

- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - スコアが全て 0 の場合は等重配分にフォールバック（警告ログ）
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
    - セクター上限適用ロジックと未知レジーム時のフォールバック
  - 株数決定・リスク制限・単元丸め（calc_position_sizes）
    - risk_based / equal / score の配分方式をサポート
    - 単元株（lot_size）に合わせた丸め、aggregate cap によるスケールダウン、コストバッファ考慮、残差分の再配分ロジック

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計
  - 基準値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を出力
  - --from/--to/--db オプションをサポート、PAPER_TRADING_SQLITE_PATH を参照

- 研究用ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）
  - モメンタム・ボラティリティ・バリュー等を DuckDB の prices_daily / raw_financials を基に計算する設計
  - P95 計算など補助関数を含む（モジュールは継続実装を予定）

- パッケージメタ情報（src/kabusys/__init__.py）
  - バージョンを 0.1.0 に設定

### Changed
- none（初回リリースのため過去変更なし）

### Fixed
- none（初回リリースのためバグ修正履歴なし）

### Notes / Implementation details
- .env パースは引用符内のバックスラッシュエスケープや export プレフィックス、インラインコメント判定（クォートなしの '#' の前が空白の場合のみコメント）などを考慮した堅牢な実装になっています（src/kabusys/config.py）。
- ロギング設定は、既存ハンドラを一度 flush/close してから差し替えることで二重ハンドラ設定を防止します（src/kabusys/utils/logging_setup.py）。
- プロセス管理や停止フラグの扱いは起動スクリプト側で一貫しており、監視・実行のどちらも停止フラグを検出して安全に終了する設計です（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- Paper Trading 環境では DB を完全に分離してログを蓄積することで、本番 DB とデータが混在しないように配慮しています（src/kabusys/run_execution.py, Settings.paper_sqlite_path）。

---

今後の予定（例）
- factor_research の各ファクター計算ロジック実装完了
- ExecutionEngine / BrokerClient の詳細実装とユニットテスト追加
- 監視アラート（LINE 通知等）の実装強化

---