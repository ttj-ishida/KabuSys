# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日はソースコードから推測できる最新日付（2026-04-19）を使用しています。

## [Unreleased]

（次版の変更点をここに記載）

---

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 初回公開。以下の主要コンポーネントを実装・追加。
  - 実行系 / 監視系起動スクリプト
    - run_execution.py：ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じてペーパートレード用の DB / MockBroker を使用する分離を実装。スレッドでエンジンを実行し、停止フラグ / PID 管理を行う。
    - run_monitoring.py：SystemMonitor をポーリングで定期実行する監視ループ。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検知、例外耐性を実装。
  - 環境設定・検証ツール
    - config_setup.py：対話式 .env ウィザード。既存値の読み込み、シークレットのマスク表示、ファイル保存機能を提供。
    - validate_config.py：起動前検証 CLI。必須環境変数・KABUSYS_ENV・YAML の存在/パースチェック・本番環境向けの追加ガードを行う。--strict オプションで警告も FAIL 扱いに可能。
  - 設定管理
    - config.py：Settings クラス。環境変数の安全なロード（.env / .env.local の自動読み込み、OS 環境変数保護）・パースロジック実装。プロジェクトルートの自動検出（.git / pyproject.toml 基準）により CWD 非依存で動作。
    - 詳細なプロパティ実装（DB パス、paper_trading 用 DB/モード、監視閾値、ログレベルなど）と入力検証（KABUSYS_ENV、PAPER_FILL_MODE、LOG_LEVEL など）。
  - ポートフォリオ構築モジュール（純粋関数群）
    - portfolio.portfolio_builder：シグナル選定（select_candidates）、等配分/スコア配分（calc_equal_weights / calc_score_weights）。スコア全0 の際のフォールバックと警告を実装。
    - portfolio.risk_adjustment：セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。未知レジームはフォールバック動作を提供。
    - portfolio.position_sizing：発注株数計算（calc_position_sizes）。risk_based / equal / score の複数手法に対応、単元株（lot_size）丸め、合計投資額が利用可能現金を超えた場合のスケールダウンと残差処理、コストバッファ考慮などを実装。
  - ユーティリティ
    - utils.logging_setup：StreamHandler（stdout）と日次ローテーションファイルハンドラをルートロガーへ設定。ログディレクトリ作成失敗時のフォールバックを実装。
    - utils.process_priority：Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定。psutil 利用、権限不足等は警告でスキップ。
  - ペーパートレード検証ツール
    - tools.paper_verification_report：Paper Trading 用 SQLite から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 など）を集計してレポート出力。閾値に基づく PASS/FAIL 判定を実装。
  - 研究用モジュール（ファクター計算）
    - research.factor_research：DuckDB ベースのファクター計算モジュール（モメンタム・MA・ATR 等の設計。関数定義と定数を含む。実装は一部まで含まれる）。

### 変更 (Changed)
- ロギング
  - すべての起動スクリプトから setup_logging を使用することでログ設定を統一。標準出力は stdout を使用し、ファイルハンドラは日次ローテーションで 30 日分保持する設計。
- データベース取り扱い
  - run_execution は paper_trading 環境の際は paper_sqlite_path を使用して本番データと完全分離する設計。監視用テーブル初期化は冪等に行われる（init_monitoring_db 呼び出し）。
- 環境変数読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- 設定パースの堅牢化
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。

### 修正 (Fixed)
- 起動時の安全性/堅牢性の改善
  - run_monitoring のポーリング間隔読み取りで不正値（0 以下や非整数）を検出してデフォルトにフォールバックする処理を実装（警告ログ出力）。これにより time.sleep に渡す不正値でのクラッシュを回避。
  - logging_setup: ログディレクトリ作成やファイルハンドラ作成に失敗した場合でもコンソール出力にフォールバックして起動が継続するようにした。
  - process_priority: 権限不足や未対応 OS で例外を投げず警告でスキップするようにした。
  - config.validate: PyYAML が未インストールの環境でも警告を出して YAML 内容検証をスキップするようにした（起動環境による不整合検出が可能）。
- ポートフォリオ計算の安全弁
  - position_sizing: 価格欠損や負値に対するスキップ、合計コスト超過時のスケーリングと lot_size 単位での再配分を実装し、不整合な発注数量を出さないようにした。
- apply_sector_cap: セクター未知（"unknown"）銘柄はセクター上限判定から除外する仕様を明確化（誤ブロック防止）。

### 既知の制限 / 注意点 (Known issues / Notes)
- research.factor_research の実装はファイル末尾で途中までとなっており、関数実装が完全に含まれていない可能性がある（追加実装・テストが必要）。
- 一部 TODO コメントあり（価格欠損時のフォールバック価格、銘柄別 lot_size サポート等）は将来の改善対象。
- 本番環境 (KABUSYS_ENV=live) では LINE 通知等の設定が未設定だとアラートが届かないため validate_config での確認を推奨。

### セキュリティ (Security)
- 此のリリースでは特定のセキュリティ修正は記載なし。ただし、.env ファイルは Git にコミットしない旨を config_setup の出力で明示している。

---

参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/