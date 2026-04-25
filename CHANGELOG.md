# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
このファイルはコードベースの現在の状態（バージョン 0.1.0）を、ソースコードの内容から推測して要約したものです。

なお、以下の記載はリポジトリ内の実装内容から推定した変更点・機能説明であり、実際のコミット履歴とは一致しない場合があります。

## [0.1.0] - 2026-04-25

### Added
- 基本パッケージの初回リリース相当の機能を追加。
  - パッケージメタ情報として `__version__ = "0.1.0"` を定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止制御はプロジェクトルートの `data/stop_requested.flag` ファイルで検知。
    - 監視用途の SQLite DB は実行環境にかかわらず設定された sqlite_path（本番パス）を使用するよう実装。
    - プロセス優先度を起動時に "high" に設定する処理を追加。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用のペーパートレード用 DB（`data/paper_trading.db`、環境変数で上書き可）と MockBrokerClient を使用して本番 DB と分離。
    - エンジンの PID ファイル管理と停止フラグ（`data/stop_requested.flag`）の検知ロジックを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
    - .env のパース実装：コメント、export プレフィックス、シングル/ダブルクォート内のエスケープを考慮。
    - Settings クラスを実装し、各種設定値（J-Quants / kabu / DB パス / PID / Kill flag / 閾値 / environment / log level など）をプロパティとして提供。入力値の検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
    - paper_trading 用 DB パスや fill mode のデフォルトと検証をサポート。

  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - よく使う設定項目（環境、API トークン、DB パス、ログレベル、Kill Switch 設定等）をウィザードで入力できる。
    - 既存 .env の読み込み、マスク表示、保存確認を実装。

  - validate_config.py
    - 起動前に設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス/親ディレクトリの存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証、自動的に本番向けガード（LINE 通知設定や Kill flag の設定）チェックを行う。
    - `--strict` フラグで警告を失敗扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル順位付け（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別エクスポージャ計算と blocked セクターの候補除外を行う。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear、未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ決定ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）およびスケールダウン後の残余配分ロジックを実装。
    - cost_buffer による保守的なコスト見積りを考慮。

- モニタリング DB 初期化
  - run_* スクリプトで使用する monitoring DB 初期化関数（監視テーブルの冪等な確保）を監視モジュール側に連携して使用。

- ログ/プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py
    - psutil を用いてプラットフォーム差異を吸収したプロセス優先度設定（high/normal/low）を実装。POSIX 系では nice、Windows では priority class を利用。権限不足などは警告でスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite のログを解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを集計。
    - PASS/FAIL 基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）を設定し、基準未達の場合は FAIL として指摘。
    - P95 計算、日付フィルタリング、DB 存在チェックを実装。

- 研究用ファクター計算基盤（スケルトン）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの枠組みを追加（モメンタム・Value・Volatility・Liquidity 等の仕様と定数を定義）。実装の続きが存在する構成（途中でファイルが切れているが設計方針が示されている）。

### Changed
- なし（初回リリース想定）。ただし、各モジュール内でデフォルト値・バリデーション・ログ出力の方針を明確化。

### Fixed
- なし（初回リリース想定）。実装にはエラーハンドリング（例: DB パース失敗、ファイル作成失敗、psutil 権限不足）や警告ログが丁寧に追加されている。

### Security
- 環境変数ファイル生成時に `.env` を絶対に Git にコミットしない旨をドキュメント化（config_setup のヘッダ）。
- シークレット項目（トークン・パスワード）を対話時にマスク表示。

### Notes / Implementation details（運用上の注意）
- run_monitoring は監視用 DB に対して「環境にかかわらず本番 sqlite_path を使用する」との実装になっているため、開発環境での運用時は sqlite_path の設定に注意が必要（監視ログが本番 DB に記録されうる）。
- run_execution は paper_trading モード時に専用 DB を使用するよう分離されている点で、本番 DB との分離が考慮されている。
- .env 自動ロードはプロジェクトルート検出に依存し、特に配布後（パッケージ化）や特殊な配置の場合は自動ロードがスキップされる可能性がある。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して手動管理を行ってください。
- 一部モジュール（research/factor_research.py 等）は計算ロジックの骨子が示されているが、完全実装に向けた追加作業が想定される箇所が存在。

---

今後のリリース案（提案）
- Unreleased:
  - research/factor_research の完全実装とユニットテスト追加。
  - ExecutionEngine / SystemMonitor のユニット/統合テスト、モック化の強化。
  - 設定検証・ウィザードの国際化（多言語対応）や CI での自動検証ワークフロー追加。
  - ドキュメント（README、運用ガイド、設計ドキュメント）の整備。