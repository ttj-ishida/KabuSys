CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本パッケージ初期リリースを追加（バージョン 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。プロセス優先度を起動時に "high" に設定、停止用フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）に対応。Engine を別スレッドで実行し、停止フラグまたはタイムアウトにより安全にシャットダウンする仕組みを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用する仕様。プロセス優先度設定、ログ設定、監視 DB 初期化などを実行。
- 設定管理
  - config.py: .env 自動ロード（プロジェクトルートの .env / .env.local）機能を実装。プロジェクトルートの検出は .git または pyproject.toml を基準に上位ディレクトリを探索する方式。複雑な .env 行（export 付き、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント）に対応するパーサを実装。Settings クラスを追加し、環境変数アクセスを型的に提供（トークン、DB パス、paper_trading 用設定、閾値など）。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。必須項目・選択肢の提示、既存値の再利用、保存確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）、本番用のガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）などを実施。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全てゼロの場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を追加。未知のレジーム時のフォールバックと警告ロギングを実装。
  - portfolio/position_sizing.py: 株数算出ロジック（risk_based / equal / score）を追加。単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer を用いた保守的見積り、残差分配アルゴリズムを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log）をルートロガーに設定。既存ハンドラのクリア、ログレベル/ログディレクトリの解決、ファイル出力失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）の設定ユーティリティを追加。Windows / POSIX 差分を吸収し psutil を使って優先度設定を実施。権限不足や未対応 OS の場合は警告でスキップ。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポートを出力する CLI を追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを算出し、基準値との比較で PASS/FAIL 判定を行う（閾値はソース内定義）。日付フィルタ（--from / --to）や DB パス指定（--db）に対応。
- 研究用
  - research/factor_research.py: ファクター計算基盤の骨組み（モメンタム、ボラティリティ、バリュー、流動性などの指標計算）を追加（DuckDB 接続ベース）。（モジュールは一部実装継続中）
- パッケージ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

Changed
- N/A（初期リリースのため既存機能からの変更は無し）

Fixed / Improved
- .env パーサの堅牢化: export prefix、引用符内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮してパースするよう改善。無効行のスキップやエラー時の警告出力を実装。
- MONITOR_POLL_INTERVAL の取り扱い: 環境変数が不正（数値化できない、0 以下）の場合にログで警告しデフォルト（60 秒）にフォールバックするよう安全化。
- logging_setup: ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを追加。既存ハンドラの二重登録を防ぐためハンドラを明示的にクリアするように変更。
- position_sizing: 合計投資額が利用可能現金を超えた場合にスケールダウンするアルゴリズムを採用し、端数（lot 単位）を残余キャッシュで再配分する機構を実装。price の欠損/0 の扱いについてログ出力で説明を追加。
- risk_adjustment: セクター不明（"unknown"）の銘柄はセクターキャップ適用から除外する仕様を明記。

Security
- .env ファイル生成ウィザードの出力で注意書きを追加（.env を決して Git にコミットしないこと）。

Notes / Known limitations
- research/factor_research.py はファクター計算モジュールの実装が途中であり、未完の関数・ロジックが存在します（今後のリリースで完了予定）。
- 一部機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。実行環境にこれらが揃っていない場合はいくつかのチェックや機能がスキップされるか警告が出ます。
- run_monitoring は監視用 DB に本番 sqlite_path を常に使用するため、環境設定に応じた分離が必要な場合は注意してください（意図的な仕様: 監視は本番 DB を想定）。

Acknowledgments
- 初期バージョンの実装。今後の改善（テスト追加、ドキュメント拡充、研究モジュール完成等）を予定しています。