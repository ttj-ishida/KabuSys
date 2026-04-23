# Changelog

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」のガイドラインに従っています。

なお本ファイルは、提示されたコードベースの内容から機能追加・設計方針・修正点等を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
最初の公開リリース（Initial release）。自動売買システム KabuSys のコアユーティリティ群、実行・監視ランナー、ポートフォリオ構築ロジック、設定/検証ツール、ペーパートレード検証レポート等を含む。

### Added
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
  - ExecutionEngine を起動する CLI スクリプト。バックグラウンドスレッドでセッションを実行し、停止フラグ（data/stop_requested.flag）を監視して安全に停止できる。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
  - 実行時に execution.pid を出力する仕組み（PID ファイル）。

- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
  - SystemMonitor を用いた定期ポーリング監視ループ。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60秒）。
  - 監視 DB は環境にかかわらず本番用 sqlite_path を使用する設計（monitoring 用テーブル初期化を実施）。
  - 停止フラグ（data/stop_requested.flag）によりループを終了。

- 設定管理・自動読み込み
  - src/kabusys/config.py
  - .env と環境変数の優先順位を扱う Settings クラスを提供。自動でプロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
  - 複数の設定プロパティを公開（DB パス、PID/kill flag パス、各種閾値、ペーパートレード設定等）。
  - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV のバリデーションを実装。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py
  - 対話式で .env を作成・更新するウィザード。既存値の読み取り、シークレット項目のマスク表示、保存前の確認を実装。
  - 出力テンプレートは .env に書き込む形式で整備。

- 設定検証ツール
  - src/kabusys/validate_config.py
  - 起動前に必須環境変数や config/*.yaml、DB パス、KABUSYS_ENV の妥当性をチェックする CLI。--strict で警告をエラー扱いにできる。
  - PyYAML 未導入時のフォールバックや、production（live）環境向けの追加警告を実装。

- ペーパートレード検証レポート生成スクリプト
  - src/kabusys/tools/paper_verification_report.py
  - 指定期間の paper_trading DB を解析し、稼働率（uptime）、注文成功率（fill rate）、送信率、API レイテンシ（平均 / 最大 / P95）などを集計して標準出力にレポートを出力。
  - 合否判定閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200ms）を定義。
  - --from/--to/--db オプションに対応。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - 信号のスコア降順選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合のフォールバック動作を備える。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。既存ポジションのセクター別時価を計算し上限を超えるセクターの新規採用をブロック。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元（lot_size）丸め、1銘柄上限、利用可能現金に対する aggregate cap（スケーリング）、コストバッファの考慮、残余分の配分ロジックを備える。
  - ポートフォリオ API をトップレベルで export（src/kabusys/portfolio/__init__.py）。

- ログ設定ユーティリティ
  - src/kabusys/utils/logging_setup.py
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを提供。既存ハンドラはクリアして二重設定を防止。
  - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
  - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定する set_process_priority を実装。psutil の制限（権限不足など）を安全にハンドリング。
  - set_cpu_affinity により最初の N コアにプロセスを固定する機能を追加（未指定時は変更なし）。

- 研究向けファクター計算スケルトン
  - src/kabusys/research/factor_research.py（モメンタム等のファクター計算を行う設計方針と定数を定義）
  - DuckDB を利用した prices_daily / raw_financials を参照する設計。関数 calc_momentum の導入（途中までの実装スケルトンあり）。

- パッケージ基礎
  - src/kabusys/__init__.py にバージョン 0.1.0 を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Internal / Implementation notes
- DB 統合
  - DuckDB（分析用）と SQLite（監視 / 発注履歴用）を併用する設計。各スクリプトは適切なパスに接続し、init_monitoring_db により監視用テーブルの存在を保証する。
- 安全停止
  - run_execution と run_monitoring はプロジェクトルート下の data/stop_requested.flag を監視し、検知時に安全に処理を終了する共通動作を採用。
- 環境ファイル読み込み
  - .env のパースはクォートやエスケープ、インラインコメントに対応する独自実装を持つ（config._parse_env_line）。
  - OS 環境変数は保護され、.env.local は .env 上書き（ただし既存の OS 環境変数は保護）という読み込み順。

### Breaking Changes
- （初回リリースのため該当なし）

### Security
- 機密情報（トークン / パスワード）は .env で管理する設計。config_setup の出力で .env を誤ってコミットしないよう注意喚起を出力。

---

今後の追加予定（推測）
- research.calc_momentum の完成および他ファクター（Value/Volatility/Liquidity）実装
- ExecutionEngine / BrokerClient の詳細実装とテスト補完
- CLI ドキュメントや例、unit tests の追加
- 銘柄別 lot_size や手数料モデルの拡張、ログ周りの運用改善

もし特定ファイルの変更履歴（差分）での記載や、別のバージョン単位での分割が必要であれば、その対象となる差分または過去のバージョン情報を提示してください。