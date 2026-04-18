# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このファイルは Keep a Changelog の慣例に従っています。フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 小さな改善・拡張予定:
  - research/factor_research.py の実装続行（現在ファイル末尾で未完了）。
  - 銘柄ごとの単元株（lot_size）を銘柄マスタで管理する拡張（position_sizing の TODO）。
  - 価格欠損時のフォールバック戦略（前日終値など）の追加（risk_adjustment に注記あり）。

---

## [0.1.0] - 2026-04-18
初回リリース。本リポジトリに含まれる主要機能・CLI・ユーティリティ・ポートフォリオ構築ロジックなどを実装。

### 追加 (Added)
- コア実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と完全分離する仕組みを実装。
    - BrokerClientFactory を介して実際のブローカー or MockBrokerClient を切り替え可能。
    - 実行中 PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - 停止フラグファイル検知によりループを安全に終了。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装し、.env/.env.local の自動読み込みを行う（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の堅牢なパーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス等に対応）。
    - Settings クラスを実装して各種設定をプロパティ経由で取得（バリデーションを含む）。
    - Paper Trading 向けの設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）を提供。
    - 監視や閾値関連の設定プロパティ（CPU/MEM/DISK の閾値、pid/kill flag 等）を提供。

- 設定支援 CLI
  - config_setup.py
    - 対話的ウィザードで .env を作成/更新するツールを追加。
    - デフォルト値・選択肢・シークレット入力・既存 .env の読み取りをサポート。
    - 生成された .env は Git にコミットしない旨の注意を出力。

  - validate_config.py
    - 起動前の設定・環境チェック CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境用の追加ガードなどを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の優先解決・ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX 間の差異を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足時や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築モジュール (純粋関数群 / DB 参照なし)
  - portfolio/portfolio_builder.py
    - 売買シグナルの候補選定 select_candidates を実装（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別時価を計算し、上限超過セクターから新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック calc_position_sizes を実装。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate 上限（available_cash）によるスケーリング、cost_buffer を考慮した保守的推定、残差分の lot 単位での配分アルゴリズムを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。 --db オプションや PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。

- パッケージメタ
  - __init__.py にてパッケージバージョンを 0.1.0 として定義。

### 変更 (Changed)
- なし（初回リリースのため新規実装中心）

### 修正 (Fixed)
- なし（初回リリース）

### 注意・既知の制約 (Notes / Known limitations)
- run_monitoring は「監視用 DB」として Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。KABUSYS_ENV による切替は行いません（監視データは本番と同一 DB を想定）。
- run_execution は paper_trading 時に paper_sqlite_path を使用して本番 DB と分離します。環境設定による誤運用に注意してください。
- position_sizing や apply_sector_cap は価格データが欠損（0 や None）の場合の扱いに注意（ログに記録してスキップするが、エクスポージャー過小評価によるブロックの逸脱リスクあり）。将来的にフォールバック価格の導入を推奨（TODO コメントあり）。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存し、失敗時は警告を出してスキップします。
- config/.env パーサは多くのケースに対応しているが、特殊な .env フォーマットには想定外の動作をする可能性があります。
- research/factor_research.py は一部未完（ファイル末尾で途中）。

---

貢献・バグ報告・改善提案は Issue を立ててください。