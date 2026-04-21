# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース。

### Added
- 起動/実行用スクリプトを実装
  - run_execution.py
    - ExecutionEngine の起動ラッパーを追加。デーモンスレッドでエンジンを実行し、外部停止フラグ（data/stop_requested.flag）を検出して安全に停止する仕組みを実装。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離して動作。
    - BrokerClientFactory を利用して実際のブローカーまたはモックブローカーを透過的に切替。
    - OrderRepository, OrderManager, RiskManager（デフォルト設定を含む）、Reconciler を組み合わせて ExecutionEngine を構築。
    - PID ファイル管理、停止フラグ検出、最大 30 秒のシャットダウン待機などを実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルト 60 秒、環境変数 MONITOR_POLL_INTERVAL による上書きに対応（不正値はログ警告でデフォルトにフォールバック）。
    - 監視 DB（SQLite）は環境に関わらず本番 sqlite_path を使用して初期化。
    - 停止フラグ検出でループ終了。KeyboardInterrupt による終了ハンドリングと接続クローズ処理を実装。

- 設定管理
  - config.py
    - .env の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - 高度な .env パーサ実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント処理など）。
    - Settings クラスを導入し、環境変数の取得と検証（J-Quants / kabu API の必須項目、DB パス、PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV/LOG_LEVEL の検証など）を提供。
    - paper_trading 用 DB パスや PID / kill flag 等の設定プロパティを提供。

  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを実装。複数の設定項目定義、既存 .env 読み込み、シークレットマスク表示、保存前確認などをサポート。

  - validate_config.py
    - .env および config/*.yaml の起動前チェック CLI を実装。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML の存在/パース検証（PyYAML がある場合）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギングセットアップ関数を追加。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリは引数、環境変数、デフォルトの優先順位で決定。

  - utils/process_priority.py
    - Windows / POSIX 間の差分を吸収するプロセス優先度設定ユーティリティを追加（high/normal/low）。psutil を用いて nice 値や Windows 優先度クラスを設定し、許可がない場合は警告を出してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity() も提供。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全ゼロ時は等分配にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。unknown セクターの扱い、売却予定銘柄の除外などをサポート。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear -> 1.0/0.7/0.3、未知レジームはフォールバック 1.0）。
  - portfolio/position_sizing.py
    - 単元株丸め、リスクベース・等配分・スコア配分の発注株数計算を実装。ポートフォリオ上限、単銘柄上限、lot_size（単元）処理、手数料・スリッページ見積り(cost_buffer) を加味した aggregate cap のスケーリングロジックを実装。
    - risk_based ではリスク % とストップロスでベース株数を算出し、既存保有を差し引いた発注数を算出。

- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に対して各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計して PASS/FAIL 判定を出力する。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - 日付フィルタ（--from/--to）、DB パス上書き（--db）に対応。

- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py
    - Momentum 等のファクター計算を行う基盤を追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。1M/3M/6M リターン、MA200 乖離、ATR、出来高などを計算する方針を反映。関数 calc_momentum の骨子を追加（実装途中）。

### Changed
- パッケージの公開情報を追加
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Fixed
- 初期リリースのため特定のバグ修正履歴はなし。

### Security
- 特になし。

---

注記:
- ここに列挙した変更はソースコードから推測して要約したものです。実際の運用・公開リリースでは各モジュールのテスト結果、外部依存（psutil, duckdb, PyYAML 等）のバージョン適合、環境変数の取り扱い（秘密情報の保護）を十分に確認してください。