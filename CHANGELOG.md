以下は、提示されたコードベースから推測して作成した CHANGELOG.md（Keep a Changelog 準拠・日本語）です。初期リリースとしての記載とし、コード内の機能・振る舞い・堅牢性対策などを要約しています。必要に応じて日付や項目を調整してお使いください。

CHANGELOG.md
=============
すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------
（現在未リリースの変更はここに記載）

[0.1.0] - 2026-04-19
-------------------
初回公開リリース — 基本機能の実装と運用用ユーティリティ群を追加。

Added
- 基本パッケージとバージョンを追加
  - kabusys パッケージ初期リリース（__version__ = "0.1.0"）。
- 実行／監視用起動スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading のときは専用の paper_trading DB を使用して MockBroker を利用可能（本番 DB と分離）。デーモンスレッドでエンジンを実行し、停止フラグでの安全停止に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知で安全終了。
- 設定管理とウィザード
  - config.py: 環境変数・設定管理クラス Settings を提供。プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込みを実装。PAPER_FILL_MODE のバリデーションなど各種プロパティを実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザード。一般的項目（API トークン、DB パス、ログレベル、Kill Switch 設定等）をサポートし、.env を生成するユーティリティを提供。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合の）パース検証、--strict モードを追加。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギングセットアップ。stdout への StreamHandler（出力を stdout に統一）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップするフェールセーフあり。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を実装。psutil を利用し権限不足や未対応 OS へのフォールバック処理を追加。CPU affinity を設定する set_cpu_affinity を追加。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジーム時はフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: position size の計算 calc_position_sizes を実装。allocation_method="risk_based"/"equal"/"score" をサポートし、lot_size（単元株）丸め、単銘柄上限、aggregate cap のスケーリングと残差配分ロジックを実装。価格欠損時のスキップや cost_buffer（手数料・スリッページ見積り）対応を実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して CLI レポートを生成。閾値を定義して PASS/FAIL 判定を出力。--from/--to/--db オプションを提供。
- 研究用ファクター計算スケルトン
  - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け prices_daily 等を参照する設計）。各定数（窓長）や関数の方針コメントを含む。実装は続行予定。

Changed
- ロギングの出力先の方針
  - StreamHandler を stdout に固定し、ログ出力の一貫性（cron / Task Scheduler でのリダイレクト運用）を考慮。
- .env 読み込みの優先度
  - OS 環境変数 > .env.local > .env の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により自動読み込みを無効化可能（テスト用途）。

Fixed / Robustness
- .env パーサの堅牢化（config.py）
  - export プレフィックス対応、シングル／ダブルクォート値とバックスラッシュエスケープ処理、インラインコメント取り扱い、キー・値のトリミング等を実装。読み込み時の I/O エラーは警告（warnings.warn）で扱う。
- 環境変数の保護（.env の上書き）
  - _load_env_file で override=True の場合でも OS 環境変数を protected として上書きしない安全設計。
- 起動スクリプトの堅牢性
  - run_monitoring.py: MONITOR_POLL_INTERVAL の不正値に対する警告とデフォルトフォールバック、check_once() 内例外の捕捉とログ出力、停止フラグ検出での正常終了処理、DB コネクションの確実なクローズを実装。
  - run_execution.py: 起動時に停止フラグが既に立っている場合は起動を中止、実行スレッドの監視と停止フラグ検出 → engine.stop() の呼び出し、最終的な join と DB クローズを確実に行う。
- ログハンドラ作成失敗時のフォールバック
  - logging_setup はログディレクトリ作成・ファイルハンドラ作成に失敗した場合にコンソールのみで継続。ファイルハンドラの作成失敗は警告ログで通知。

Security
- シークレット値の扱い
  - config_setup の対話表示ではシークレット項目をマスク表示（"****"）して確認可能にした。README 等に .env を絶対に Git にコミットしない旨を書き込む雛形を生成。

Documentation / UX
- 各 CLI スクリプトに使い方コメントを追加（トップドックストリング／help）。
- validate_config に --strict オプションを追加し、警告も失敗扱いにできるように。

Notes / Known limitations
- research/factor_research.py は一部実装が未完（ファクター計算ロジックの継続実装が必要）。
- position_sizing の price フォールバック未実装（price が 0 の場合、エクスポージャー等が過少評価される可能性あり。将来的に前日終値等のフォールバックを検討）。
- process_priority の権限設定は OS 権限や実行ユーザーに依存し、設定失敗は警告となる（動作は保証しない）。
- config/*.yaml の内容検証は PyYAML に依存。未インストール時は検証をスキップして警告を出す。

今後の予定（示唆）
- factor_research の完成（ファクター出力を標準化し、DuckDB クエリ最適化）。
- ExecutionEngine / Monitoring の追加テストとエンドツーエンド検証。
- 銘柄別単元（lot_size）を stocks マスタから参照する拡張。
- さらなる運用性向上（ヘルスチェック API、より詳細な運用ドキュメント等）。

（以上）