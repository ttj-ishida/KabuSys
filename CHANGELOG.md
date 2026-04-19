# CHANGELOG

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-19

初回公開リリース — KabuSys の基盤機能を実装しました。日本株自動売買システムの起動スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ、および検証/レポート用ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, バージョン 0.1.0）。

- 環境設定・読み込み
  - .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git / pyproject.toml から検出して .env / .env.local を読み込む。
    - export 形式、クォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応する独自パーサを実装。
    - OS 環境変数の保護（protected）と上書き制御を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得（必須キー検証や既定値の解決、enum 的検証を含む）。
    - データベースパス、PID/kill flag パス、閾値（CPU/MEM/DISK）や env/log レベル判定、Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）等を提供。

- 設定関連 CLI
  - 設定ウィザード: `.env` を対話的に作成・更新する CLI を追加（src/kabusys/config_setup.py）。
    - よく使う設定項目のプロンプト、既存値の読み取り、シークレットマスク表示、確認後ファイル書き込みをサポート。
  - 設定検証ツール: 起動前の設定チェック CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML があれば内容検証を実施）、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視起動スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を高に設定して起動、KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動、外部停止フラグ検知による安全停止、PID 管理を実装。
    - 監視テーブルの初期化を保証（冪等）。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に依らず本番 sqlite_path を使用する仕様、停止フラグ検出でループ終了。
    - check_once() の例外をキャッチしてログ出力し継続する耐障害性を実装。

- ポートフォリオ構築ロジック（メモリ内純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等金額へフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションを基にセクター比率を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を提供（bull/neutral/bear、および未知レジームのフォールバック）。
    - セクター計算で価格欠損時の注意点（TODO コメントあり）。
  - 株数決定・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元（lot_size）丸め、ポジション別上限・aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - コストバッファ（手数料・スリッページ）を反映した保守的見積りと、端数処理による追加配分ロジックを実装。

- ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - すべての起動スクリプトで共通利用できる setup_logging を実装。StreamHandler（stdout） + TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR と引数優先の解決ロジック、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux（POSIX）差分を吸収してプロセス優先度を設定する set_process_priority を実装。psutil を利用し除外や権限エラーを許容する堅牢化。
    - set_cpu_affinity により最初 N コアに固定可能（例外処理あり）。

- 検証ツール・レポート
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 指定期間（--from/--to）または DB 全期間で稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシなどを計算してレポート表示。
    - 既定の閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）に基づく PASS/FAIL 判定を実装。
    - 実行時は PAPER_TRADING_SQLITE_PATH または --db で DB を指定。

- リサーチ基盤（着手）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - DuckDB を用いたモメンタム等のファクター計算基盤の実装を開始（モジュール設計、定数、calc_momentum などの骨子を追加。実装の続きあり）。

### Fixed
- .env パーサの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォート付き値、エスケープ、インラインコメントの扱いで誤解析しないよう改善。
- 起動時のログハンドラ二重登録回避（src/kabusys/utils/logging_setup.py）
  - 既存ハンドラを一旦閉じてから再設定するようにして、複数回 setup_logging を呼んだ際の重複出力を防止。
- プロセス優先度の例外耐性（src/kabusys/utils/process_priority.py）
  - AccessDenied 等発生時に警告ログを出して処理を継続するようにした。

### Notes / Known issues
- risk_adjustment.apply_sector_cap 内で価格が 0.0／欠損の場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO を残しています。
- position_sizing は現状で全銘柄共通の lot_size（単元）を仮定している。将来的に銘柄別 lot_map を受け取る拡張を想定。
- factor_research モジュールは作業途中（ファイルは途中で切れている）です。完全実装は今後のリリースで対応予定。
- 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定すると危険（validate_config でも警告）。本番では 0 を推奨します。
- 監視（monitoring）は設計上 sqlite_path を本番用に固定している点に注意（paper_trading と分離したい場合は設定を確認してください）。

---

著者: KabuSys 開発チーム  
初版: 2026-04-19

（必要であれば、今後のリリースで変更点・バグ修正・機能追加をここに追記します。）