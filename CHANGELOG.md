# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- 重要な変更点はカテゴリごとに分けて記載します（Added / Changed / Fixed / Deprecated / Removed / Security）。
- コマンドラインや環境変数の既定値、動作の注意点なども併記します。

## [0.1.0] - 2026-04-23

Added
- 基本アプリケーション骨格を追加（初回リリース）。
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を利用して paper-trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録し、本番 DB と分離。
    - 実行前にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - stop フラグ（data/stop_requested.flag）を監視し、検知時にエンジンを安全に停止。
    - 実行時にプロセス PID を data/execution.pid に書き込む仕組みを前提（ExecutionEngine 側で利用）。
    - duckdb 接続（デフォルト path は DUCKDB_PATH / data/kabusys.duckdb）を利用。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値（0 以下・非数）はデフォルトにフォールバックして警告を出力。
    - 監視用 DB 接続は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用して接続（監視は常に本番監視 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）を検出してループを終了。
    - 例外発生時でもログを残して次回ポーリングまで待機する耐障害性を確保。

- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動ロード機構:
      - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
      - 標準の読み込み順: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止可能（テスト用）。
      - .env のパースはクォートやエスケープ、コメント（'#'）の扱いに対応。
    - 各種設定値をプロパティとして提供:
      - J-Quants, kabuステーション, LINE API トークン、DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、監視閾値（CPU/MEM/DISK）、KABUSYS_ENV 判定（development/paper_trading/live）など。
      - PAPER_FILL_MODE のバリデーション（"instant","partial","never","reject"）。
      - KILL_FLAG_CLEAR_ON_START の bool 解釈（"1" で True）。

  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話形式で .env を作成/更新する run_wizard（保存時に .env を書き出す）。
    - 各項目の説明、デフォルト、シークレット入力、オプション項目の扱いをサポート。
    - コマンド例: python -m kabusys.config_setup

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の存在・基本整合性チェックを実行。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック等を行う。
    - PyYAML がない場合は YAML 内容検証をスキップして警告を出力。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict フラグで警告もエラー扱いにして exit(1) を返す。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順・タイブレークは signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア比例配分（全スコアが 0 の場合は等金額にフォールバックし warning を記録）。

  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中制限を適用（既存保有を基にセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外）。"unknown" セクターは除外対象にしない。
      - sell_codes（当日売却対象）をエクスポージャ計算から除外可能。
      - 価格欠損（0.0）の取り扱いに関する注意コメント（将来的にフォールバック価格を検討）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。不明なレジームは 1.0 にフォールバックして warning を出力。

  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: 各銘柄の発注株数を算出する主要ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: risk_pct, stop_loss_pct に基づくポジションサイズ計算（portfolio_value を使った per-stock cap を適用）。
      - equal/score: weight ベースで per-position 上限、lot_size（デフォルト 100）で丸め。
      - aggregate cap: 全銘柄の投資総額が available_cash を超える場合、スケールダウンを行い、fractional remainder に応じて lot 単位で追加配分するロジックを実装。
      - cost_buffer を考慮して保守的なコスト見積りを行う。
      - lot_size を将来的に銘柄別に拡張する TODO コメントあり。

  - portfolio パッケージの __all__ を整備しエクスポートを提供（src/kabusys/portfolio/__init__.py）。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - 既存ハンドラをクリアして二重設定を防止。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > LOG_DIR 環境変数 > デフォルト "logs/"。
    - ファイル出力用ディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。

  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / Windows priority class）を設定するユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - アクセス権限不足や未対応 OS では警告を出力してスキップ。

- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite の監査・検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 閾値（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンド例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 研究用モジュール
  - research/factor_research（src/kabusys/research/factor_research.py）
    - ファクター計算モジュールを追加。Momentum / Value / Volatility / Liquidity を想定。
    - Momentum 関連パラメータ（1M/3M/6M、MA200、ATR など）の定数と calc_momentum の骨格が実装されている（DuckDB 接続を受け取って prices_daily 等のテーブルを参照する設計）。
    - ※ ファイルの末尾に実装の途中と思われる切れが見られる（今後の続きが必要）。

Changed
- （初回リリースのため「変更」はありませんが、各モジュールは今後のリリースで拡張予定）

Fixed
- （初回リリースのため「修正」はありません）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 注意点 / TODO
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされます（配布後に CWD に依存しない挙動を確保するため）。
- run_monitoring は監視 DB に常に settings.sqlite_path（本番向け path）を使用します。監視データを別 DB に分離したい場合は設定を変更してください。
- position_sizing / apply_sector_cap の一部では価格欠損時のフォールバックが未実装（コメントで TODO）。実運用前に価格取得ロジックの補完を検討してください。
- research/factor_research は継続実装が必要（現状ではファイル末尾が途切れている）。
- 実行環境（特に本番: KABUSYS_ENV=live）では LINE 通知や kill-switch の扱いなどの設定を慎重に行ってください（validate_config にて注意喚起あり）。

今後の予定（提案）
- factor_research の完成（各種ファクターの実装・テスト）。
- ExecutionEngine / BrokerClient の統合テストと paper_trading の挙動検証。
- 個別銘柄単位の lot_size 管理や価格フォールバック実装。
- ドキュメント（README / PortfolioConstruction.md 等）の整備と例の追加。

-----
この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴に基づく厳密な差分はバージョン管理履歴（git）を参照してください。