Keep a Changelog準拠の CHANGELOG.md（日本語）を作成しました。推測に基づく項目を記載しています。必要であれば追記・修正してください。

```
# CHANGELOG

すべての注目変更点はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-04-21
### Added
- 初期リリース: KabuSys 日本株自動売買システムのコアモジュール群を追加。
- 実行系/監視用起動スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプト。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory を用いたブローカー切替（paper_trading 環境時は MockBrokerClient を使用し、専用 DB に記録）を実装。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使用した終了制御を導入。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に依らず本番 sqlite_path を使用する設計。
- 環境設定および検証ツール:
  - config.py: 環境変数・設定管理。プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動ロード機能、.env パース（クォート・エスケープ・コメント対応）、必須変数取得ユーティリティ、各種設定プロパティ（DB パス、KABUSYS_ENV、Paper Trading の挙動など）を提供。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。各設定項目の説明・デフォルト・シークレット入力をサポートし、.env ファイルを書き出す。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ検査、config/*.yaml の存在確認および YAML パースチェック（PyYAML がない場合はスキップ）や本番環境向けのガードチェックを実装。--strict モードで警告を失敗扱いにできる。
- ロギング・プロセス関連ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティ。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ自動作成、および環境変数/引数によるログレベル・保存先上書きに対応。
  - utils/process_priority.py: プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティ。Windows と POSIX を抽象化し、失敗時は警告を出してスキップ。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（スコア・タイブレーク付きソート）、等金額配分・スコア加重配分の関数を追加（score が全て 0 の場合のフォールバックを含む）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。セクター不明は除外しない挙動を明確化。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、per-stock と aggregate のキャップ、コストバッファ考慮、利用可能現金に対するスケーリング処理を実装。
  - portfolio/__init__.py で主要関数を公開。
- 解析・検証ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を行う。P95 計算・日付フィルタ・DB パス解決オプションを提供。
- リサーチ: research/factor_research.py を追加（モメンタム等のファクター計算を実装予定のモジュール。設計・定数が含まれる）。
- パッケージメタ: __init__.py にバージョン 0.1.0 を設定。

### Changed
- ログは stdout に出力するデフォルト設計（Cron/Task Scheduler 環境でのリダイレクト考慮）。
- .env の読み込み順序を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local で上書き可能。

### Fixed
- run_execution.py / run_monitoring.py における DB 初期化処理について、監視テーブルを冪等に保証する init_monitoring_db 呼び出しを追加（監視テーブルが存在しない場面でも安全に起動できるように）。

### Known issues / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的に前日終値などのフォールバック価格を導入することがコメントで示唆されている。
- research/factor_research.py:
  - モジュールはファクター計算の設計と定数が整備されているが、一部実装（calc_momentum の続き等）が未完の可能性がある（ファイル末尾が途中で切れている状態に見える）。
- paper_trading 動作:
  - KABUSYS_ENV=paper_trading の際、paper_trading用 DB（デフォルト data/paper_trading.db）を使用し、本番 DB とデータを完全に分離する設計になっているが、外部 MockBrokerClient の振る舞いは実装依存。
- プロセス優先度 / CPU affinity 設定は権限不足や環境によって失敗する場合があり、その際は警告を出してスキップする挙動。

### Security
- 特になし。

```

必要であれば以下の点を調整します:
- 追加のリリース（Unreleased → 次バージョン）分割
- 日付の修正
- 各変更項目の詳細化（差分行数、関連ファイルなど）