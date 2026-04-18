# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の書式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

## [Unreleased]

### Added
- research.calc_momentum の実装作業を追加（実装途中、未完了の箇所あり）。  
  ※ 現在、ソース内に途中で切れている箇所が存在します（調査/補完が必要）。

### Fixed
- なし

---

## [0.1.0] - 2026-04-18

初期リリース。以下の主要機能・モジュールを実装/追加。

### Added
- 全体
  - パッケージ `kabusys` の初期バージョンを追加（__version__ = "0.1.0"）。

- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離する設計。  
    - BrokerClientFactory 経由でブローカークライアントを生成（MockBroker を切り替え可能）。  
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による停止制御を実装。  
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明確化。  
    - 停止フラグ（data/stop_requested.flag）によるループ終了を実装。  
    - 例外時にログを残して次ポーリングへ継続する耐障害性を確保。
  - tools/paper_verification_report.py: ペーパートレード解析・検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出。  
    - デフォルト閾値を用いた PASS/FAIL 判定を実装（閾値はソースに定義）。  
    - コマンドライン引数で期間指定（--from / --to）や DB パス（--db）を指定可能。

- 設定関連
  - config.py: 環境変数／.env ロードと Settings クラスを実装。  
    - プロジェクトルート自動検出（.git / pyproject.toml を基準）により .env 自動読み込みを行う。  
    - .env 読み込みロジックは export プレフィックス、クォート、インラインコメント等に対応。  
    - Settings 経由で各種設定をプロパティ化（J-Quants / kabu / DB パス /監視閾値 / 環境判定 等）。  
    - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。  
  - config_setup.py: 対話式ウィザードで .env を作成/更新するツールを追加。  
    - 入力のプロンプト、既存 .env の読み込み、値の確認、保存機能を提供。  
    - secret 項目はマスク表示、選択肢・デフォルトのサポートを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在 / パース検証（PyYAML があれば）を実施。  
    - --strict モードで警告をエラー扱いにするオプションを実装。  
    - 本番環境（KABUSYS_ENV=live）向けのガードチェック（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の危険性）を追加。

- ポートフォリオ構築（pure function）
  - portfolio/portfolio_builder.py: 候補選定と重み計算を実装。  
    - select_candidates: スコア降順＋タイブレーク（signal_rank）で最大 N 件を選択。  
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重（0スコア時は等分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター制限とレジーム乗数を実装。  
    - apply_sector_cap: 既存保有のセクター別エクスポージャーから新規候補の除外ロジックを提供（"unknown" セクターは除外対象外）。  
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。  
    - risk_based / equal / score の割当方式に対応。  
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash とのスケール調整）、cost_buffer を考慮した保守的見積り、端数配分ロジックを実装。  
    - price 欠損時のスキップやデバッグログを追加。

- データ/リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。  
    - DuckDB の接続を受けて prices_daily / raw_financials を参照する設計。  
    - モメンタム計算（calc_momentum）の枠組みと定数を実装。ただしソース末尾が途中で切れているため calc_momentum は未完成。

- 実用ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテートされる TimedRotatingFileHandler をルートロガーに設定。  
    - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順を実装。  
    - 既存ハンドラのクリーンアップ処理を行う（多重設定防止）。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定を追加。  
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応した nice/priority 設定を実装。  
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足時は警告でスキップ。

- 監視 / モニタリング
  - monitoring.monitoring_db.init_monitoring_db を利用して起動時に監視用テーブルの存在を保証（冪等）。  
  - SystemMonitor（起動スクリプトで使用）を組み込み、check_once() を定期実行する設計。

### Changed
- なし（初期リリースのため新規追加が中心）

### Fixed
- なし

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues
- research/factor_research.calc_momentum の実装が途中で切れている（ソースに "start_da" 等の未完了記述がある）。該当機能は未完成のため、動作検証・実装完了が必要です。  
- 一部 TODO コメントあり（例: position_sizing における銘柄別 lot_size の将来的拡張、risk_adjustment の価格欠損時のフォールバック等）。将来的な改善ポイントとして残しています。  
- .env 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。運用時は .env の取り扱い（Git へ commit しない等）に注意してください。

---

（以降のバージョンでは、上記の未完成箇所の修正、テスト追加、ドキュメント整備、さらに監視/実行のロバスト化やリサーチ関数群の完成を予定）