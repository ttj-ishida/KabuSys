# Changelog

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

- リリースノートは日本語で記載しています。
- 日付は YYYY-MM-DD 形式です。

## [Unreleased]

- 次回リリースに向けた作業項目や予定をここに記載してください。

---

## [0.1.0] - 2026-04-24

初回公開リリース。本バージョンでは自動売買システムのコア機能群、運用用ユーティリティ群、設定関連 CLI、ペーパートレード検証ツール、およびポートフォリオ構築ロジックの基礎を実装しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - デーモンスレッドでのエンジン実行と stop フラグ（data/stop_requested.flag）による安全停止処理。
    - 実行 PID ファイル管理（data/execution.pid）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検知と例外ハンドリングを含む安定稼働ループを実装。

- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート自動検出）を実装。
    - .env 行パーサーは export 形式、クォート／エスケープ、インラインコメントなどに対応。
    - Settings クラスを提供し、環境変数のラップと型変換・検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
    - paper_trading 用のデータベースパスや PID / kill flag 等の設定プロパティを提供。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を提供（secret 値のマスク、選択肢、デフォルト対応）。
    - 生成・保存用のフォーマット済 .env 出力を実装。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の存在・基本妥当性を検査する CLI を追加。
    - --strict モードで警告を FAIL 扱いにできる。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML の有無に対応）などを実装。
    - 本番環境向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START）を追加。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックする挙動を実装。
  - portfolio/risk_adjustment.py
    - セクター集中（apply_sector_cap）による候補除外ロジックを実装。
    - 市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく株数算出ロジックを実装。
    - 単元株丸め（lot_size）、ポジション上限、aggregate cap スケーリング、手数料・スリッページのバッファ（cost_buffer）対応。
    - 利用可能現金を超える場合のスケーリングと残余配分アルゴリズムを実装。

- 運用ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログディレクトリの解決（引数 / 環境変数 / デフォルト）と既存ハンドラのクリーン再設定に対応。
    - ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。Windows と POSIX 系 OS の差分を吸収。
    - 権限不足や未サポート環境での安全なフォールバックを実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - SQLite（paper_trading.db）から集計を行い、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などの指標を出力するレポート生成スクリプトを追加。
    - デフォルト期間フィルタ、コマンドライン引数（--from/--to/--db）に対応。
    - 合格基準（稼働率 99%、成立率 90% など）に基づく PASS/FAIL 判定を実装。

- リサーチ（骨組み）
  - research/factor_research.py
    - Momentum ファクター等の計算ロジックの実装を開始。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計（実装は継続中）。

- パッケージ初期化
  - __init__.py にてバージョンを 0.1.0 として設定し、主要サブパッケージを __all__ に列挙。

- DB 初期化 / 互換性
  - monitoring.monitoring_db への初期化呼び出しを run_execution/run_monitoring 両方で行う（監視テーブルが存在することを保証）。

### Changed
- ログ出力方針
  - コンソール出力は stdout を使用する方針に統一（cron 等からのリダイレクトを考慮）。
- 環境変数ロード優先度
  - OS 環境変数 > .env.local > .env の順で読み込み（既存 OS 環境を保護するため protected 指定を導入）。

### Fixed
- 設定パーサーの堅牢化
  - .env パーサーで export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応し、テスト環境や配布後の挙動を安定化。

### Security
- .env ファイル生成に関する注意喚起
  - config_setup.py の出力ヘッダに .env を絶対に Git にコミットしない旨の注意を明記。

---

注: この CHANGELOG はリポジトリ内のソースコードから機能・意図を推測して作成したものであり、実際のコミット履歴や設計文書の差分と完全に一致しない可能性があります。必要であればコミットログ（git history）に基づく正確な変更履歴へ置き換えてください。