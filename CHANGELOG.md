# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]

## [0.1.0] - 2026-04-24
最初の公開リリース。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB から完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応。停止フラグ検出時は安全にエンジンを停止。
  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値時はデフォルトにフォールバックして警告。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ (data/stop_requested.flag) 検出でループを終了。
    - 例外発生時はログを残して次ポーリングへ継続。
- 設定管理
  - config.py
    - .env 自動ロード機能を導入（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env / .env.local の読み込み順序と OS 環境変数保護（上書き禁止）に対応。
    - 詳細な .env パーサを実装:
      - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント処理等。
    - Settings クラスで環境変数をラップ。各種パス、ログレベル、環境種別（development/paper_trading/live）、paper_trading 用の設定（PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH）等を提供・検証。
    - settings インスタンスをモジュールレベルで公開。
- 設定支援ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目はマスク表示、選択肢・デフォルト提示、既存 .env の読み込み/再利用に対応。
    - 最終確認後に .env を書き出す機能。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML がインストールされている場合）を実施。
    - --strict モードで警告を FAIL 扱いにできる。
- 監視関連
  - monitoring_db 初期化呼び出しを各起動スクリプトから行い、監視用テーブルが存在することを保証（冪等）。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログディレクトリ自動作成機能と作成失敗時のフォールバック（コンソール出力のみ）に対応。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils/process_priority.py
    - psutil を利用してクロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応環境では警告ログを出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補銘柄選定（スコア降順、タイブレークに signal_rank）。
    - 等金額配分（calc_equal_weights）/ スコア加重配分（calc_score_weights。全スコア0の時はフォールバック）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピングし、未知レジームは警告の上フォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング処理を実装。
    - 価格欠損時のスキップとデバッグログを提供。
  - portfolio パッケージの __all__ を整備して上記関数群を公開。
- 研究用モジュール（初期実装）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの枠組みを追加（Momentum / Value / Volatility / Liquidity を計画）。
    - モメンタム計算関数の実装を開始（ファイル末尾で未完の箇所あり／継続実装予定）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。--db オプションや環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。
    - P95 計算、日付フィルタ、欠損テーブルに対する耐障害性（OperationalError をハンドリング）を備える。

### Changed
- N/A（初回リリースのため既存変更は無し）

### Fixed
- N/A（初回リリースのため修正履歴は無し）

### Removed
- N/A

### Security
- .env は決してリポジトリにコミットしない旨を config_setup とトップメッセージで明示。
- validate_config により本番環境（KABUSYS_ENV=live）使用時に重要設定（LINE トークン等）が未設定だと警告を出力。

### Notes
- Monitoring は設計上「環境にかかわらず本番 sqlite_path を使用」するため、開発時に監視データを分離したい場合は sqlite_path を変更してください。
- PAPER_FILL_MODE（paper_trading の注文約定挙動）や PAPER_TRADING_SQLITE_PATH 等、ペーパートレード用の環境変数で本番と処理を分離可能。
- research/factor_research.py の一部（ファイル末尾）が未完のため、ファクター計算の追加実装・テストが必要です。
- run_monitoring/run_execution は stop/kill フラグファイルに依存するため、運用時のフラグファイル配置・管理に注意してください。

---

今後の予定（参考）
- factor_research の完成とユニットテスト追加
- ExecutionEngine / SystemMonitor の統合テスト強化
- 各種 CLI のヘルプ改善とログ構成改善オプションの追加
- ポートフォリオ構築の端数処理や lot_size を銘柄毎に指定できる拡張

---

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成したものです。実際の変更履歴やリリースノートはプロジェクトの運用方針に合わせて調整してください。