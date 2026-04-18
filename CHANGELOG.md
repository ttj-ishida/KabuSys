# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

このリポジトリの現在バージョン: 0.1.0

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite (data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可) を使用する。  
    - BrokerClientFactory 経由で実際のブローカー or MockBroker を生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動する。  
    - 停止制御: data/stop_requested.flag と execution.pid による起動/停止管理をサポート。スレッドで実行し、停止フラグ検出で安全に停止する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は実行環境にかかわらず本番用の sqlite_path を使用する設計（監視 DB は環境分離しない想定）。
- 設定管理
  - config.py: 環境変数 / .env ファイルの読み込み・アクセス用 Settings クラスを追加。  
    - 自動 .env ロード（.env, .env.local、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。  
    - .env の堅牢なパース（export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメント処理など）。  
    - 多数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV 等）。
- 設定関連 CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加（.env のテンプレート生成・既存値の再利用・シークレットマスク表示など）。  
  - validate_config.py: 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV, LOG_LEVEL の妥当性、DB path の親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML が無い場合はスキップ）など）。--strict オプションで警告をエラー扱いにできる。
- 分析/検証ツール
  - tools/paper_verification_report.py: Paper Trading の実行検証レポート生成ツールを追加。  
    - CLI オプション: --from, --to, --db（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）。  
    - 稼働率、注文成功率(fill), 送信率(send), リスク却下数、API レイテンシ（平均/最大/P95）を算出し PASS/FAIL を判定するしきい値を実装。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額/スコア加重の重み計算(calc_equal_weights, calc_score_weights) を追加。スコア全0時のフォールバックロジックを含む。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加。未知レジーム時のフォールバックとログ警告を実装。
  - portfolio.position_sizing: position sizing ロジック(calc_position_sizes) を追加。  
    - risk_based / equal / score の配分方式を実装。  
    - 単元株(lot_size)丸め、1銘柄上限(max_position_pct)、投下資金上限(max_utilization)、cost_buffer（手数料/スリッページ見積）を考慮したスケーリングと再配分ロジックを含む。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーへ設定。既存ハンドラの二重登録を防止するため一旦クリアする実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ使用するフォールバックを実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - Windows/Linux/macOS を吸収。psutil を利用して nice 値 / HIGH_PRIORITY_CLASS を設定。権限不足や未対応環境では警告を出してスキップ。
- research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum/Value/Volatility/Liquidity の設計・定数・calc_momentum の実装着手）。DuckDB を用いた prices_daily/raw_financials の参照設計。
- パッケージメタ
  - パッケージ初期化 (kabusys/__init__.py) にバージョン __version__ = "0.1.0" を設定。
  - package export: portfolio モジュールの関数をトップレベルからインポート可能にした __all__ を設定。

### Changed
- デフォルト設定・動作の明文化
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず monitoring DB（SQLITE_PATH）を使用する仕様を明示。
  - run_execution は paper_trading 実行時に paper_sqlite_path を使用して本番 DB と完全分離するように実装。
- ロギングの挙動
  - StreamHandler を stdout に固定（stderr ではない）し、cron 等からのリダイレクト運用を意識した設計。
  - ロガー初期化時に既存ハンドラを flush/close/削除して二重出力を防止。

### Fixed
- .env パーサの堅牢化
  - 引用符付き値内でのバックスラッシュエスケープ処理や、行内コメントの認識ルールを実装し、.env の読み込みが実際のシェル表記に近くなるよう改良。
- 設定検証の堅牢化
  - validate_config で PyYAML が未インストールの場合は YAML 検証をスキップして警告するようにして、外部依存がなくても実行できるようにした。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密情報の扱い
  - config_setup の対話UIではシークレット項目（J-Quants トークン、kabu API パスワード等）をマスク表示。`.env` を絶対に Git にコミットしない旨をテンプレートに明記。

---

注記:
- 一部モジュール（例: research.calc_momentum の実装途中）は骨組みが含まれており、将来的に拡張される予定です。  
- 実行・監視プロセスは stop flag / pid file を利用する設計になっているため、本番運用時は data ディレクトリ内のフラグファイルの取り扱いに注意してください。  
- この CHANGELOG はリポジトリ内のコードと docstring から機能を推測して作成しています。細部の挙動は実際の実行時設定や外部コンポーネント（BrokerClient 等）の実装に依存します。