# Changelog

すべての変更は Keep a Changelog の形式に従います。  
安定したリリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-21
初回公開リリース。

### Added
- 実行エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 組み立て、別スレッドでのエンジン実行と停止フラグ監視を実装。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する挙動をサポート。
    - 起動時に停止フラグ（data/stop_requested.flag）を検知すると起動を中止する。
    - 実行中は同フラグを監視して検知時に安全に停止する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視（monitoring）は環境にかかわらず本番用 sqlite_path を使用する（監視データは一元管理）。
    - 停止フラグでループを終了し、KeyboardInterrupt にも対応。

- 設定管理
  - config.py: 環境変数／.env 読み込みと Settings クラスを提供。  
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。  
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
    - .env を読み込む際、OS 環境変数は保護（上書きされない）。.env.local は .env を上書きする（ただし OS 環境変数は保護）。  
    - .env 内の export 形式、シングル／ダブルクォート内のエスケープ、インラインコメントなどに対する堅牢なパーサ実装。  
    - 必須値チェック用の _require ユーティリティと各種設定プロパティ（DB パス、paper_trading 用設定、監視閾値、KABUSYS_ENV/LOG_LEVEL 判定など）を提供。

- 設定ツール
  - config_setup.py: 対話式 .env 作成／更新ウィザードを追加。  
    - 主要設定項目（KABUSYS_ENV、J-Quants token、kabu API password、DB パス、LINE 通知設定、LOG_LEVEL、Kill flag の自動クリア設定など）を対話的に設定・保存可能。
    - 既存 .env 読み込み・Enter で既存値再利用・確認プロンプトを備える。

  - validate_config.py: 起動前チェック CLI を追加。  
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの存在確認、config/*.yaml の存在・YAML パース検証（PyYAML がインストールされている場合）を行う。  
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を警告。  
    - --strict オプションにより警告を FAIL として exit(1) にできる。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。  
    - LOG_LEVEL / LOG_DIR / 引数による設定解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加。  
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収。設定失敗時は警告を出力してスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコア順）・等配分・スコア加重配分を実装（スコア 0 の場合は等配分へフォールバックの警告）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。  
    - apply_sector_cap は既存ポジションのセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外する（unknown セクターは除外対象外）。  
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対応。未知レジームは警告と共に 1.0 でフォールバック。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based、equal、score の各配分方式をサポート）。  
    - 単元株（lot_size）に丸め、1 銘柄上限・総投下上限・cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング処理を実装。残差処理により余剰キャッシュでの lot 単位追加配分を行う。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。  
    - SYSTEM / ORDER / RISK / LATENCY 指標を SQLite（デフォルト: data/paper_trading.db）から集計してレポート出力。  
    - P95 計算、各種閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。  
    - --from/--to/--db オプションをサポート。

- 研究モジュール（骨格）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加。モメンタム、MA200、ATR、出来高等を計算する設計方針と定数群を定義（実装の続きを想定）。

- パッケージ基礎
  - __init__.py によるバージョン管理（__version__ = "0.1.0"）と主要サブパッケージのエクスポート設定を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサの堅牢化  
  - export プレフィックス、引用符内エスケープ、インラインコメントの扱い、未設定行の無視などに対応。これにより .env による設定読み込みの信頼性が向上。

### Security
- 機密情報取り扱いに関する注意の追加（.env を Git にコミットしない旨を config_setup の生成ファイルヘッダに明記）。

### Notes / Usage
- 環境変数の自動ロードはプロジェクトルートが検出できない場合スキップされます（配布パッケージ化後の挙動を考慮）。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。  
- 本番運用時は KABUSYS_ENV を "live" に設定し、validate_config による事前チェックを実施してから起動することを推奨します。  
- run_execution / run_monitoring のログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト LOG_DIR=logs）。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。

--- 

（将来のリリースでは、research/factor_research の完全実装、追加のユニットテスト、より細かなエラーハンドリングや observability 機能の拡充等を予定しています。）