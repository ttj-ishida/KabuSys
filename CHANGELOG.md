# Changelog

すべての変更は Keep a Changelog に準拠して記述します。  
慣例: 追加 (Added), 変更 (Changed), 修正 (Fixed)、非推奨 (Deprecated)、削除 (Removed)、セキュリティ (Security)。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションおよび CLI を実装
  - パッケージ初期バージョンとして core 機能を追加。
  - バージョン識別子: `kabusys.__version__ = "0.1.0"` (src/kabusys/__init__.py)。

- 環境設定・読み込み
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env のパースはクォートやエスケープ、コメント（#）を考慮して安全に扱う実装（src/kabusys/config.py）。
  - 環境変数未設定時にエラーを投げる `_require()`、各種設定プロパティを持つ `Settings` クラスを導入（DB パス、API トークン、環境フラグ等）。

- 環境セットアップウィザード
  - 対話式に .env を作成/更新する CLI を追加（src/kabusys/config_setup.py）。
  - 各種設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL など）をサポート。
  - 秘匿入力のマスク、既存 .env の読み込み、保存確認機能を実装。

- 設定検証 CLI
  - `.env` と config/*.yaml の起動前検証ツールを追加（src/kabusys/validate_config.py）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在／パース検証、production 時の追加ガードなどを実行。
  - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止条件: プロジェクト内 data/stop_requested.flag ファイル検出でループを終了。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する挙動を明示。
  - Execution エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` のときは専用の paper trading SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、MockBrokerClient を選択する設計。
    - PID ファイル管理（data/execution.pid）・停止フラグ検出による安全停止をサポート。

- 実行系コンポーネントの骨組み
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager などを組み合わせて実行エンジンを起動するフローを整備（参照は run_execution.py）。
  - RiskManager に初期ポートフォリオ値をブローカから取得して設定する機能を想定（settings 経由）。

- ロギング/プロセス制御ユーティリティ
  - 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリの作成失敗時はファイル出力をスキップ。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - プラットフォーム間の差を吸収するプロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux、Darwin、FreeBSD) に対応し、アクセス権限や未対応環境では警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア全体が 0 の場合は等配分にフォールバックして警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対応、未知レジームは 1.0 にフォールバックして警告）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分ロジックを実装。
    - 単元株（lot_size）丸め、各銘柄最大比率、aggregate cap によるスケーリング、cost_buffer（スリッページ・手数料）考慮のロジックを実装。

- Paper Trading 検証レポート
  - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポートを出力するツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - CLI オプションで期間指定（--from, --to）や DB パス指定（--db）をサポート。
  - PASS/FAIL 判定のしきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

- リサーチ（ファクター計算）の基盤
  - ファクター計算モジュールの骨格を実装（src/kabusys/research/factor_research.py）。
    - Momentum, Value, Volatility, Liquidity を設計目標に含む。DuckDB 接続を受け取り、prices_daily / raw_financials を参照して計算する方針。
    - Momentum 計算のための定数／スキャン窓を定義（ただしファイル末尾で計算処理が途中で切れているため実装継続が必要）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（初期リリース）

---

注意事項 / 実装上のポイント
- 環境変数関連
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - `PAPER_FILL_MODE` の有効値は "instant" | "partial" | "never" | "reject"。無効な値は ValueError。
  - `KABUSYS_ENV` は "development" | "paper_trading" | "live" のみ有効。無効値は ValueError。
- run_monitoring の挙動
  - MONITOR_POLL_INTERVAL が不正（整数以外、0 以下等）の場合はデフォルト 60 秒にフォールバックして警告を出す。
  - 監視は stop flag ファイル検出で終了。監視 DB は環境に依存せず本番用 sqlite_path を使用する（設計上の注意）。
- run_execution の挙動
  - paper_trading 環境では paper 用専用 SQLite を使用して本番 DB と完全分離。
  - 起動時に既に停止フラグが立っている場合は起動せず終了する安全策を実装。
- ロギング
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップするが、コンソール出力は継続されるよう堅牢化している。
- 未完成・今後の課題
  - src/kabusys/research/factor_research.py はファイル末尾で処理が途中になっており、完全実装が必要。
  - position_sizing の price 欠損時の扱い（コメントでフォールバック価格の導入案を記載）など改善余地あり。

---

この CHANGELOG はソースコードの内容から推測して作成しています。追加・修正・バグフィックスを行った場合は本ファイルを更新してください。