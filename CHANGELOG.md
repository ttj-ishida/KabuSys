# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初期リリース。システム全体の主要コンポーネント（設定管理、起動スクリプト、監視、実行エンジンの起動支援、ポートフォリオ構築、ユーティリティ、各種 CLI/ツール）が実装されています。

### Added
- 一般
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
  - プロジェクトルート検出と .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - 自動読み込み順: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - .env パースは `export KEY=val` 形式、クォート文字、エスケープ、インラインコメントを考慮。
  - Settings クラスで主要環境変数をラップし、デフォルト値・バリデーションを提供（KABUSYS_ENV、LOG_LEVEL、DB パス等）。

- 起動スクリプト / 実行制御
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - `KABUSYS_ENV=paper_trading` 時はペーパートレード用 DB を利用し（data/paper_trading.db デフォルト）、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成（paper/live に応じて実装切替想定）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による外部停止指示、PID ファイル管理、DB 接続の初期化（監視用テーブルの存在保証）を実装。
    - リスク管理（RiskManager）を組み込んだデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用（監視 DB は環境に依存しない想定）。
    - stop フラグ（data/stop_requested.flag）検知でループを終了、check_once() の例外はログに残して次回に継続。

- 設定ユーティリティ / CLI
  - 対話式設定ウィザード（src/kabusys/config_setup.py）
    - .env の初期作成・更新支援。各種項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, Kill Switch 等）を対話的に設定・保存可能。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェックと（PyYAML が利用可能なら）パース検証。
    - `--strict` オプションで警告をエラー扱いにできる。

- ロギング／プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > "INFO"。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。アクセス権限や未対応 OS の場合は警告を出してスキップ。
    - CPU affinity の設定 (最初の N コアに固定) をサポートし、権限不足の場合でも安全にスキップ。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank（低い方優先）でソート。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重（スコア合計が 0 の場合は等金額にフォールバックして警告）。
  - セクター上限・レジーム係数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター別時価を計算し、1 セクターのエクスポージャが max_sector_pct を超える場合はそのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告と共に 1.0 でフォールバック。
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じて株数を算出（"risk_based"|"equal"|"score"）。
    - risk_based: 許容リスク率・損切り率からベース株数算出、単元（lot_size）丸め。
    - equal/score: weight に基づく配分、ポジション上限（max_position_pct）考慮。
    - aggregate cap: 全銘柄合計が available_cash を超えた場合はスケーリングし、残余は fractional remainder を用いて単元単位で再配分。
    - cost_buffer を用いて手数料・スリッページ分を保守的に見積もる。
    - lot_size は将来的に銘柄別対応へ拡張予定（TODO コメントあり）。

- 分析・検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を算出し、しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 latency 200ms）で PASS/FAIL を判定する CLI を実装。
    - 日付フィルタ (--from/--to)、DB パス (--db / PAPER_TRADING_SQLITE_PATH) に対応。

- 研究用モジュール（部分実装）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム、MA200 偏差、ATR、流動性などの指標計算方針と定数を実装。DuckDB を用いた prices_daily / raw_financials 参照を前提にした設計。
    - 実装途中の箇所あり（calc_momentum が途中で切れているため、追加実装が必要）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Known issues / TODO（コードからの推測）
- research/factor_research.py の calc_momentum 実装が途中で終了している（ファイルが途中で切れている）。完全実装が必要。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャが過少見積りされる問題を指摘する TODO コメントあり。前日終値などのフォールバック価格導入を検討中。
- process_priority/set_cpu_affinity の呼び出しは権限依存（Linux の nice の値変更や Windows の優先度設定）で失敗する可能性があり、失敗時は警告でスキップする設計。
- ログディレクトリ作成やファイルハンドラ作成で例外が発生した場合は stdout のみでログを継続する設計になっているため、運用時はログディレクトリの権限・存在を確認推奨。
- ExecutionEngine / BrokerClientFactory / Execution の詳細実装はこの差分には含まれていない（外部モジュールとの連携を前提）。Paper trading 用 MockBroker の存在が想定されているがコード本体は別モジュールに依存。

---

参考:
- 環境変数の主なキー: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START
- デフォルトパス: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
- ログ: デフォルトは logs/<app_name>.log（daily rotate、30 日保持）

（注）本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。運用上の正確なリリースノート作成時はコミット履歴・変更差分・リリース担当者による確認を行ってください。