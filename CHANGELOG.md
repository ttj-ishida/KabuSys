# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載します。  
フォーマットは日本語で記載しています。

## [Unreleased]

- ドキュメント/脚注の追記や内部ログ・警告文の文言調整など、マイナーな改善を予定。

---

## [0.1.0] - 2026-04-18

初回リリース。ローカル開発からペーパートレード・本番運用までを想定した日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py; __version__ = 0.1.0）。
  - プロジェクトルート自動検出と .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - .env/.env.local の読み込み順序、OS 環境変数保護、複数形式のパース（クォート、export、インラインコメント）に対応。
    - Settings クラスを提供し、環境変数をプロパティ経由で安全に取得する API を実装（J-Quants、kabu API、DB パス、監視閾値等）。
    - PAPER_TRADING 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）をサポート。
- CLI / 開発補助
  - 環境設定ウィザード（.env 作成/更新）を対話式に行う `config_setup` を追加（src/kabusys/config_setup.py）。
    - 入力のマスク（シークレット）、選択肢、デフォルト表示、既存 .env の読み込み・再利用をサポート。
  - 起動前設定検証 CLI `validate_config` を追加（src/kabusys/validate_config.py）。
    - 必須環境変数／ローカルパス／YAML 設定ファイルの存在とパース（PyYAML 利用有無を考慮）／本番環境向けガード等の検査を実装。`--strict` オプションで警告も失敗扱いにできる。
  - Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシを集計し PASS/FAIL 判定を出力。期間フィルタ、DB パス指定オプションをサポート。
- 実行/監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 DB に切り替え、Mock ブローカーの利用想定で本番 DB と完全分離。
    - プロセス優先度設定、高優先度での起動、PID ファイル管理、停止フラグ（data/stop_requested.flag）でのシャットダウン制御を実装。
    - コンポーネント組立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の起動）を行う。
  - SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）。監視 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して初期化。
    - 停止フラグ、例外ハンドリング、リソースクリーンアップを実装。
- ロギング / プロセス管理
  - 統一されたロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーへ設定。LOG_DIR / LOG_LEVEL 優先順位に対応。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 差異吸収（psutil 利用）、set_process_priority と set_cpu_affinity を提供。権限不足等は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合はフォールバック）を実装。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションを考慮して新規候補からセクター過集中を除外）、calc_regime_multiplier（bull/neutral/bear マッピング）を実装。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）対応。リスクベースの株数算出、単元（lot_size）丸め、1銘柄上限・アグリゲート上限、コストバッファ反映、スケールダウンロジックを実装。
  - portfolio パッケージのエクスポートを用意（src/kabusys/portfolio/__init__.py）。
- リサーチ
  - DuckDB ベースのファクター計算モジュールの雛形を追加（src/kabusys/research/factor_research.py）。
    - モメンタム／MA200／ATR／ボリューム等の計算方針と定数を定義。calc_momentum 等の実装（ファイル末尾が一部切れているため継続実装が必要）。
- その他ユーティリティ
  - tools パッケージ用の __init__（src/kabusys/tools/__init__.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記
- 多くのモジュールで「ファイルが途中で切れている」「TODO コメント」など今後の拡張ポイントがあります（例: factor_research の継続実装、position_sizing の銘柄別 lot_size 拡張等）。
- 実行スクリプトは stop フラグや PID 管理、ログ設定、プロセス優先度変更を行います。運用時には権限やプラットフォーム依存（psutil による権限エラー等）に注意してください。
- .env は機密情報を含むため絶対に VCS にコミットしない旨が config_setup に明記されています。

もしリリースノートに追加したい項目（既知の制限、今後の予定、マイグレーション手順など）があれば教えてください。必要に応じてバージョン分割（プレリリース、パッチ）や日付の調整も行います。