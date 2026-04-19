# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

### Added
- 初回リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の MockBrokerClient を使用し、データは分離された SQLite（デフォルト: data/paper_trading.db）に記録。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。値が不正な場合はデフォルトにフォールバックして警告出力。
    - 監視は実行環境にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) による終了処理を実装。
- 設定管理 / CLI
  - config.py: 環境変数・設定読み込みモジュールを追加。  
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み（.env.local を優先して上書き可能）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロード無効化可能。
    - .env ファイルのパーサは quotes / エスケープ / コメントに堅牢に対応。
    - Settings クラスで各種設定値（DB パス、API トークン、動作モード、閾値など）とバリデーションを提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。既存 .env の読み込み、シークレットのマスク表示、保存前確認を実装。
  - validate_config.py: 設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証を実装。`--strict` モードで警告を失敗扱いにできる。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア順）と重み計算（等分配 / スコア加重）を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやフォールバック動作を明記。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。  
    - 複数の割当方式に対応（risk_based / equal / score）。  
    - 単元株丸め（lot_size）、per-stock 上限、aggregate cap（available_cash に基づくスケーリング）、コストバッファ考慮を実装。残余の再配分ロジックも実装。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。  
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。  
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。ログレベルとログディレクトリの解決順を明記。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS（対応 OS）間の差分を吸収し、設定失敗時は警告を出してスキップする安全設計。
- DuckDB / SQLite の統合
  - run_*.py などで DuckDB と SQLite の接続を確立し、monitoring テーブルの初期化（init_monitoring_db）を起動時に行うことで冪等に対応。
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs 等の集計から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を計算し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。  
    - CLI で期間（--from / --to）と DB パス（--db / 環境変数）を指定可能。
- 研究用モジュール（骨格）
  - research/factor_research.py: ファクター計算の骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB の prices_daily / raw_financials を参照する設計。P95 等のユーティリティや定数も定義（※一部実装は継続中）。

### Changed
- ログ出力の標準を stdout に統一（logging_setup が stdout を使用）。cron 等からの起動時のリダイレクト運用を考慮。
- .env の自動読み込み挙動を明確化（OS 環境変数を保護する保護集合 protected を導入）。

### Fixed
- 環境変数パーサの強化: クォート内エスケープ、インラインコメント、`export KEY=val` 形式、無効行のスキップ等に対応して読み込みの堅牢性を向上。
- run_execution/run_monitoring の終了処理を堅牢化（停止フラグ検知、KeyboardInterrupt ハンドリング、DB 接続の確実なクローズ）。

### Security
- .env ファイルの取り扱いに関する注意書きを config_setup の出力に追加（.env を Git にコミットしない旨を強調）。

### Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの主要部分が未完（calc_momentum の続き実装が必要）。  
- position_sizing の今後の改善点として、銘柄別単元情報（lot_size）を stocks マスタなどから取得する拡張が想定されている（現在はグローバル lot_size を想定）。
- process_priority / set_cpu_affinity は権限やプラットフォームによっては動作しない場合があり、その場合は警告を出してスキップする設計。
- config/*.yaml の検証は PyYAML の有無に依存する。PyYAML がインストールされていない場合は内容検証をスキップして警告を出す。

---

将来的なリリースでは、Strategy 実装・ExecutionEngine の詳細なユニットテスト・research モジュールの完実装・監視アラート（LINE 通知等）の追加を予定しています。