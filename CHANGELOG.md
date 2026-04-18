CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本リリース: KabuSys 初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0" （src/kabusys/__init__.py）。
- 起動スクリプト
  - 実行エンジン起動スクリプト: run_execution.py を追加。起動時にプロセス優先度を "high" に設定し、ExecutionEngine をスレッドで実行。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite(DB) を使用して本番データと分離（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプト: run_monitoring.py を追加。SystemMonitor を用いたポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用（src/kabusys/run_monitoring.py）。
  - 停止制御: data/stop_requested.flag ファイルを監視して優雅に停止する仕組みを導入（両スクリプト）。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。.env 自動読み込み（.env、.env.local、OS 環境変数の保護）を実装し、各種設定プロパティ（DB パス、LINE トークン、KABUSYS_ENV、ログレベル、paper_trading 関連など）と検証ロジックを提供。
  - .env パース機能を強化: export プレフィックス、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理に対応（src/kabusys/config.py）。
- 設定ユーティリティ / CLI
  - 対話式設定ウィザード: config_setup.py を追加。.env の初期作成・更新を対話式で支援し、テンプレート書き出し機能を提供（src/kabusys/config_setup.py）。
  - 設定検証ツール: validate_config.py を追加。.env と config/*.yaml の存在／基本整合性チェックを行う。--strict オプションで警告を FAIL 扱いにできる（src/kabusys/validate_config.py）。
- ログ / プロセス管理ユーティリティ
  - 統一ログ設定: utils/logging_setup.py を追加。ルートロガーに stdout StreamHandler と TimedRotatingFileHandler（日次、30日保持）を設定。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続する挙動。（src/kabusys/utils/logging_setup.py）
  - プロセス優先度・CPU アフィニティ: utils/process_priority.py を追加。Windows/Linux（POSIX）の差異を吸収して優先度設定（high/normal/low）と CPU affinity 固定機能を提供。権限不足や未対応 OS の場合は警告を出して安全にスキップする（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築ロジック
  - portfolio モジュールを追加（純粋関数群、DB 非依存）:
    - portfolio_builder.py: 候補選定、等分配／スコア加重の重み算出（calc_equal_weights, calc_score_weights, select_candidates）。
    - risk_adjustment.py: セクター上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - position_sizing.py: 発注株数計算（複数方式: risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金を超える場合のスケールダウンロジック）を実装。
  - モジュール群は logging を用いた警告出力や TODO コメントで将来の拡張（銘柄毎 lot_size 等）を示唆（src/kabusys/portfolio/*）。
- Paper Trading ツール
  - paper_verification_report.py を追加。Paper Trading 用 SQLite からシステム安定性（稼働率）、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、閾値に基づく PASS/FAIL レポートを出力する CLI（src/kabusys/tools/paper_verification_report.py）。

Changed
- 設計上の分離
  - Execution と Monitoring の DB 使用方針を明確化: monitoring は環境にかかわらず本番 sqlite_path を使用、execution は paper_trading 環境時に専用 DB を使用（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- ログ出力先の統一
  - ロガー設定は全スクリプトが setup_logging() を呼ぶ設計になり、ログの一貫性を向上（src/kabusys/utils/logging_setup.py）。
- .env 自動ロードの挙動
  - プロジェクトルート探索ロジックを導入（.git、pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能（src/kabusys/config.py）。

Fixed
- .env のパース精度を向上させ、クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメント扱いの改善を行い、想定外の文字列解釈を緩和（src/kabusys/config.py）。
- Logging 設定で、ログディレクトリ作成失敗時に例外で停止せずコンソール出力にフォールバックするように堅牢化（src/kabusys/utils/logging_setup.py）。
- process_priority.set_process_priority が未サポート環境でクラッシュしないよう例外処理を追加（src/kabusys/utils/process_priority.py）。

Security
- .env 生成テンプレート・ウィザードは .env を Git にコミットしないよう警告文を明記（config_setup.py の出力ヘッダ）。
- 設定検証時、本番環境 (KABUSYS_ENV=live) では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告（src/kabusys/validate_config.py）。

Docs / UX
- config_setup の対話的プロンプトによる初期設定フローを追加。既存値の再利用、シークレットマスク表示、確認プロンプトを実装（src/kabusys/config_setup.py）。
- validate_config により起動前に環境変数と config/*.yaml の存在・基本整合性を簡単にチェック可能。--strict モードをサポート（src/kabusys/validate_config.py）。

Known issues / Notes
- research/factor_research.py は実装中でファイル末尾が未完（途中で切れている）：momentum 計算関数の実装が続く想定。今後のリリースで完成予定（src/kabusys/research/factor_research.py）。
- position_sizing.calc_position_sizes 内の price が欠損（0.0） の場合にエクスポージャーが過少見積りされ得る点は TODO として注記。将来的にフォールバック価格戦略を追加予定（src/kabusys/portfolio/risk_adjustment.py）。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）はデフォルト 60 秒にフォールバックする。また環境変数で秒数を整数指定（src/kabusys/run_monitoring.py）。
- process_priority/set_cpu_affinity は権限が必要な場合がある（Linux の -10 等）。失敗時は警告を出して継続する設計（src/kabusys/utils/process_priority.py）。

Upgrade / Migration notes
- 新規導入: .env をまだ用意していない場合は以下を推奨:
  - python -m kabusys.config_setup で対話的に .env を生成
  - python -m kabusys.validate_config で設定検証
- 本番運用時:
  - KABUSYS_ENV を適切に設定（development / paper_trading / live）。live は特に注意（validate_config が警告）。
  - KILL_FLAG_CLEAR_ON_START は本番で 0 を推奨（自動クリアは危険）。
  - 実行中のプロセス優先度や CPU affinity を変更する権限があるか確認。
- 監視周り:
  - 監視は本番 sqlite_path を使用するため、監視専用 DB を別につくる場合は SQLITE_PATH を適切に設定すること。
  - MONITOR_POLL_INTERVAL を短くしすぎると負荷やレート制限のリスクがあるため注意。

Acknowledgements / Misc
- ログは stdout への出力を基本とし、ファイル出力は logs/<app_name>.log に日次ローテーションで保管（最大 30 世代）。ログディレクトリが作成できない環境でもコンソールログは有効（src/kabusys/utils/logging_setup.py）。

（この CHANGELOG は配布済みコードベースから推測して作成しています。実際のコミット履歴や issue/ticket に基づく詳しい変更履歴はリポジトリの VCS history を参照してください。）