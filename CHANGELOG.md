# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
過去の変更履歴は Semantic Versioning を想定しています。

今回のコードベースは初回の公開リリース相当の内容を含んでいるため、以下はこのリポジトリの初期リリース (v0.1.0) の変更点をまとめたものです。

全ての日付はリリース作成日（本ドキュメント作成日: 2026-04-19）を使用しています。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージ `kabusys` を追加。
  - __version__ を "0.1.0" に設定。

- 起動スクリプト / ランタイム
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告後にデフォルトにフォールバック。
    - 停止制御はリポジトリ直下の data/stop_requested.flag を監視して行う。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - 停止フラグと PID ファイル（data/execution.pid）に対応。バックグラウンドスレッドでエンジンを実行し、停止フラグで安全停止を試みる。

- 設定管理
  - config.Settings: 環境変数から設定値を取得するクラスを提供。
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）と入力検証を実装。
    - KABUSYS_ENV / LOG_LEVEL の値チェックを実装（不正値は ValueError）。
  - config_setup: 対話式 .env 作成ウィザードを追加。
    - 保存前に確認プロンプトを表示し `.env` ファイルを生成。
    - デフォルト値、シークレット項目扱い、選択肢表示などの UX を提供。

- 設定検証 CLI
  - validate_config: .env と config/*.yaml の存在・基本検証を行う CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの確認、YAML のパースチェック（PyYAML がインストールされている場合）。
    - --strict オプションで警告を失敗と見なす。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging:
    - stdout (StreamHandler) と 日次ローテートファイル (TimedRotatingFileHandler) をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - デフォルトログディレクトリ: logs/、日次ローテーション・30世代保持。
    - ログレベルの解決順序: 引数 > 環境変数 LOG_LEVEL > "INFO"。
  - utils.process_priority:
    - cross-platform（Windows / POSIX）でプロセス優先度設定を提供（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - psutil による操作で失敗した場合は安全に警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で上位候補を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で配分（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を元に新規候補を除外する機能。
      - "unknown" セクターは上限対象外となる。
      - 当日売却予定銘柄を除外して既存エクスポージャーを計算可能。
      - 既存ポジションの時価算出に price_map を使用（価格欠損時の注意点あり）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。
      - 未知のレジームはフォールバックで 1.0（警告出力）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数を計算。
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - lot_size（単元株）を考慮した丸め、max_position_pct（銘柄上限）、max_utilization（投下上限）、cost_buffer（スリッページ・手数料の保守的見積）に対応。
      - aggregate cap により利用可能現金を超える場合はスケーリングし、端数は lot_size 単位で再配分。
      - 価格が欠けている銘柄はスキップし、ログでデバッグ通知。

- 研究／ファクター計算
  - research.factor_research: モメンタム / Value / Volatility / Liquidity などのファクター計算モジュールの骨格を追加（DuckDB を使った計算を想定）。
    - 定数類（ウィンドウ長等）を定義。モメンタム計算関数 calc_momentum の実装を開始（未完の部分あり）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値に基づき PASS/FAIL を判定。
    - CLI オプション: --from, --to（YYYY-MM-DD）、--db（DB パス）。
    - 主要閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- run_monitoring と run_execution の起動時にプロセス優先度を最初に設定する流れを統一（`set_process_priority("high")` を導入）。
- Settings の PAPER_FILL_MODE に対する入力検証を強化（有効値チェックとエラー通知）。

### Deprecated
- （該当なし）

### Security
- 環境変数読み取り・対話式ウィザードにおいてシークレット項目（トークンやパスワード）はマスク表示。`.env` ファイルは Git にコミットしない注意喚起を README 的に出力する設計。

### Known issues / Notes
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に欠損（price == 0.0）があるとエクスポージャーが過少見積りされ、期待通りに除外されない可能性がある。将来的には前日終値や取得原価でのフォールバックを検討中（TODO コメントあり）。
- portfolio.position_sizing:
  - 現状 lot_size は全銘柄共通で固定。将来は銘柄別 lot_map に拡張予定（TODO コメントあり）。
- research.factor_research.calc_momentum:
  - ファイル末尾に未完の実装（start_da で途切れている箇所）があるため、完全動作のためには追加実装が必要。
- ログディレクトリ作成に失敗した場合はファイルロギングをスキップするが、stderr に警告を出す設計のため、ログ環境の準備が必要。
- process_priority と set_cpu_affinity は psutil に依存しており、権限不足やプラットフォーム差により設定が適用されないケースがある（その場合は警告を出してスキップ）。

---

以上が現行コードベースに基づく CHANGELOG（Keep a Changelog 準拠）のまとめです。必要であれば各項目をさらに分割してコミット単位やファイル単位の詳細を追記できます。