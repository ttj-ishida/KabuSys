CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更履歴は semver を想定しています（ここでは初回リリース v0.1.0 を記録）。
- 日付はリポジトリスナップショットから推測できる現在時点（このドキュメント作成時）を使用しています。

なお、本 CHANGELOG は提供されたソースコードから機能・動作を推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を設定し（デフォルトで "high"）、スレッドでエンジンを起動・監視する機能を提供。停止用フラグ（data/stop_requested.flag）検知時に安全に停止するロジックを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。停止フラグ検知でループを終了。監視用 DB は環境にかかわらず本番 sqlite_path を使用する旨を明記。

- 設定・環境管理
  - config.py: Settings クラスを導入。環境変数の取得 / 必須チェックを行うユーティリティを提供。KABUSYS_ENV, LOG_LEVEL 等の値検証や .env 自動ロード（.env / .env.local）機能を実装。PAPER_FILL_MODE のバリデーション、paper_trading 用 DB パスの取得等を含む。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。既存値読み込み、シークレットマスク表示、保存確認をサポート。
  - validate_config.py: 起動前に環境変数や config/*.yaml の存在・簡易パースをチェックする CLI を追加。--strict フラグで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせた共通ロギング設定を追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで続行するフォールバックを実装。
  - utils/process_priority.py: Windows・POSIX の差異を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity を設定する set_cpu_affinity も実装。権限不足や未対応 OS の場合は警告を出してスキップする。

- ポートフォリオ関連純関数群（DB非依存）
  - portfolio/portfolio_builder.py: シグナルから候補選定（select_candidates）、等ウェイト（calc_equal_weights）、スコア加重（calc_score_weights）を提供。スコアが全て0の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。未知レジームは警告を出してフォールバック（1.0）。
  - portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ考慮をサポート。複数の安全弁（max_position_pct、max_utilization）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite（デフォルト data/paper_trading.db）を解析してレポートを出力する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシなどを計算し、閾値に基づく PASS/FAIL 判定を行う。各種閾値はソース内定数で定義（稼働率 >= 99% 等）。P95 は独自実装で算出。

- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動スクリプトで呼び出し、監視テーブルの存在を保証（冪等）。

Changed
- 一貫したログ設定: 全起動スクリプトが共通の setup_logging を呼ぶ想定でログ管理を統一。
- DB ハンドリング: run_execution/run_monitoring で sqlite3 と duckdb 双方を接続し、終了時にクローズする実装。

Fixed
- MONITOR_POLL_INTERVAL の不正値（負や0、非整数）に対して警告を出し、デフォルト値（60秒）にフォールバックするエラーハンドリングを追加。
- logging_setup でログディレクトリ作成失敗時のフォールバック（ファイルハンドラをスキップしてコンソール出力を継続）を明確化。

Documentation / UX
- 各 CLI にヘルプ・使用方法コメントを追加（モジュールトップの docstring、argparse の説明等）。
- config_setup による .env 出力フォーマットの説明コメントを追加し、.env を絶対に Git にコミットしない旨の注記を出力。

Security
- .env 読み込み時に既存の OS 環境変数を保護するため protected セットを使った上書き制御を実装（config._load_env_file）。
- シークレット入力項目をマスクして表示（config_setup）。

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、前日終値や取得原価などのフォールバック価格使用を検討中（ソース内に TODO コメントあり）。
- position_sizing: 将来的に銘柄別の lot_size をサポートするための拡張（stocks マスタとの連携）を想定する TODO コメントあり。
- research/factor_research.py は途中で切れている（ソースが不完全に終端している）ため、本リリースではファクター計算の一部が未実装／未完。実装継続が必要。

Removed
- （なし）

Deprecated
- （なし）

Notes
- run_execution は KABUSYS_ENV=paper_trading のとき mock ブローカーを想定し、paper_trading 専用の SQLite を使用して本番 DB と完全分離する設計になっている（Settings に is_paper 判定あり）。
- run_monitoring は環境に関わらず監視用に本番 sqlite_path を使用する仕様（意図的な設計として注記あり）。
- ログは stdout とファイルの両方向に出力するが、ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続する。

作者注
- 本 CHANGELOG は与えられたコードから機能・振る舞いを推測して作成しています。実際にコミット履歴がある場合は、そちらに基づいた正確な CHANGELOG（コミット単位の差分）を生成することを推奨します。必要であれば、実際の変更点を反映する形で改善版を作成します。