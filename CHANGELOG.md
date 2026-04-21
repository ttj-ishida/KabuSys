# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルはコードベース（src/kabusys/...）の内容から推測して作成した変更履歴です。

## [Unreleased]

### 追加予定 / 検討中
- さらなる単体テスト、エラーハンドリング強化、ドキュメント追記
- research.calc_momentum 等のファクションの残り実装（断片的に未完のコードあり）
- 銘柄ごとの lot_size を stocks マスタから読み込む設計への拡張

---

## [0.1.0] - 初回リリース
リリース日: YYYY-MM-DD

### Added
- 基本的なアプリケーション骨組みを実装
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の mock ブローカーを利用可能（paper_trading 時は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用し本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
    - 停止フラグ (data/stop_requested.flag) および PID ファイル (data/execution.pid) の取り扱いを実装。
    - duckdb 接続を使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を利用する挙動を採用。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB の接続初期化とクリーンなクローズ処理を実装。

- 設定管理
  - config.py
    - .env 自動ロード機能を提供（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序、OS 環境変数の保護（上書き禁止）の仕組みを実装。
    - 各種設定取得用プロパティを提供（J-Quants / kabuAPI / DB パス / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE に対するバリデーション（"instant"|"partial"|"never"|"reject"）。
    - 環境変数の必須チェック用ユーティリティ _require。

  - config_setup.py
    - .env を対話的に作成・更新するウィザード CLI を実装。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）をサポート。
    - シークレット項目はマスク表示。保存前に確認プロンプトあり。

  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML が未インストールの場合はスキップ）などを実装。
    - --strict オプションで警告を fail 扱いにするモードを提供。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定する共通セットアップ関数 setup_logging を提供。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで稼働する堅牢さを実装。
    - ログレベルの解決順 (引数 > 環境変数 LOG_LEVEL > デフォルト) を実装。

  - utils/process_priority.py
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定を提供（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足時や非対応 OS でのフォールバックログを実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合のフォールバック動作（等金額配分）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター時価比率を計算して候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。

  - portfolio/position_sizing.py
    - position sizing（株数決定）ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合の縮小）、cost_buffer（手数料・スリッページ考慮）等を実装。
    - リスクベース法に基づく base_shares 計算、スケーリング時の残差配分ロジックを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB からシステム安定性・注文成功率・レイテンシ指標を集計し、PASS/FAIL 判定を行うレポート生成スクリプトを実装。
    - デフォルトの DB パス: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可能）。
    - 判定基準（閾値）をファイル内定数で定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - P95 計算、期間フィルタ、テーブル欠如時のフォールバック処理を実装。

- research/factor_research.py（骨格）
  - ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）に関する設計方針と一部定数、関数の雛形を追加。
  - DuckDB を用いて prices_daily / raw_financials を参照する設計。実装は一部未完。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / 注意点
- run_monitoring は Monitoring 用 DB として settings.sqlite_path（本番用）を常に使用するため、paper_trading 環境でも監視 DB が本番 DB を参照する点に注意。
- 一部モジュール（research.calc_momentum など）に未完成箇所が存在するため、利用前に実装確認が必要。
- position_sizing の price フォールバックが未実装（price が 0 の場合に exposure が過小見積りされる可能性あり）。将来の拡張で前日終値や取得原価等のフォールバックを検討する旨の TODO を含む。
- .env の自動ロードはプロジェクトルートが検出できない場合や環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定した場合はスキップされる。

### Migration notes
- 初回リリースのため移行項目はありませんが、.env ファイルは必ず作成し、必須の環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定してください。validate_config.py を用いた事前検証を推奨します。

---

（補足）
- CLI 実行例:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行エンジン: python src/kabusys/run_execution.py
  - 監視ループ: python src/kabusys/run_monitoring.py

以上。