KEEP A CHANGELOG — 日本語訳準拠

全ての変更は SemVer に従い記載しています。初回リリースに含まれる主要機能と実装上の注意点をまとめています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション骨格を実装
  - パッケージ情報:
    - __version__ を "0.1.0" に設定。
  - 起動スクリプト:
    - run_monitoring.py
      - SystemMonitor ベースのポーリング監視ループを実装。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検知で行う。
      - 監視用 DB 接続（SQLite）と分析用 DuckDB 接続を確立し、終了時にクローズする。
      - 監視は環境（KABUSYS_ENV）に関わらず production 相当の sqlite_path を使用する実装（監視データは本番 DB に保存する設計）。
    - run_execution.py
      - ExecutionEngine 起動のエントリポイントを実装。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によりブローカークライアントを生成（paper_trading ではモッククライアントを想定）。
      - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag で停止要求を検出。PID ファイル管理用のパスをサポート。
  - 設定管理・検証・ウィザード:
    - config.py
      - Settings クラスを実装。環境変数から各種設定を取得するプロパティ群を提供（J-Quants、kabuAPI、DB パス、監視閾値、環境判定など）。
      - 自動 .env 読み込み機能を提供（プロジェクトルートを .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
      - .env のパースは export 形式、クォート文字列内のバックスラッシュエスケープ、行内コメントの取扱い等に対応。
      - PAPER_FILL_MODE など列挙的な値チェックや不正値に対する明示的なエラーを実装。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成 / 更新するツールを実装。
      - シークレット値をマスクして表示、選択肢・デフォルト提示、保存前の確認をサポート。
    - validate_config.py
      - 起動前に .env と config/*.yaml の妥当性を検証する CLI を実装。
      - 必須/任意環境変数チェック、KABUSYS_ENV 値チェック、DB パスの親ディレクトリ確認、YAML の存在・パースチェック（PyYAML 未インストール時は警告）など。
      - --strict オプションで警告も失敗扱いにできる。
  - ポートフォリオ構築（純関数群）:
    - portfolio/portfolio_builder.py
      - select_candidates: シグナルのスコア降順ソートとトップ N 選出（タイブレークに signal_rank を使用）。
      - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分。全スコアが 0 の場合は等配分にフォールバックし警告ログを出す。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、指定上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに対する資金乗数（bull/neutral/bear）を提供。未知レジームは警告のうえ 1.0 でフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes: 等配分・スコア配分・リスクベース配分の各方式を実装。
      - 単元株（lot_size）単位で丸め、per-position 上限・aggregate 上限を適用。available_cash を超える場合はスケーリングと残差処理（残余キャッシュで lot 単位で再配分）を行う。
      - 手数料・スリッページ見積り用 cost_buffer による保守的な見積りをサポート。
  - ユーティリティ:
    - utils/logging_setup.py
      - 共通ログ設定ユーティリティを実装。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
      - LOG_LEVEL と LOG_DIR の環境変数/引数優先順位に対応。ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。
      - stdout を使用（stderr ではなく）。
    - utils/process_priority.py
      - psutil を用いたプロセス優先度設定（Windows 用 priority class / POSIX の nice 値）および CPU affinity 設定を実装。
      - 権限不足や非対応 OS の場合は警告を出してスキップ。
  - ツール:
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からデータを集計し検証レポートを標準出力に出力。
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を算出し PASS/FAIL 判定を行う。閾値はソース内で定義（例: 稼働率 >= 99% 等）。
      - --from / --to / --db オプションで期間・DB パスを指定可能。
  - 研究モジュール（draft/部分実装）
    - research/factor_research.py
      - モメンタム・ボラティリティ等のファクター計算を行うモジュールの骨組みを実装（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
      - 関数設計（例: calc_momentum）や定数が定義されているが、ソースが途中で切れている箇所がある（今後実装継続予定）。

Changed
- なし（初回リリース）

Fixed
- 設定・起動まわりの堅牢性向上
  - .env パーサが export 形式やクォート内エスケープ、行内コメントに対応するよう改善。
  - logging_setup はログディレクトリ作成失敗やファイルハンドラ作成失敗をハンドリングしてフォールバックするようにした。
  - process_priority の各種例外（AccessDenied 等）をキャッチして警告に留めるようにした。

Security
- .env は絶対に git にコミットしない旨を config_setup のヘッダに明記。

Notes / 実装上の注意
- run_monitoring は監視データ保存に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データを本番 DB とは別管理したい場合は環境変数で SQLITE_PATH を変更してください。
- run_execution は KABUSYS_ENV により paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使うため、本番とペーパートレードのデータは分離されます。
- config.py の自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml により検出します。配布後や特殊な配置では自動ロードがスキップされることがあります（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御してください）。
- research/factor_research.py は現状で未完部分があります。ファクター計算機能を利用する前に該当モジュールの完成が必要です。
- ログやプロセス優先度の設定は実行環境の権限に依存します。設定に失敗した場合は警告が出力され、プロセスは継続します。

開発予定 / TODO（今後の変更候補）
- SystemMonitor / ExecutionEngine の詳細実装の追加（ex: モニタリングのメトリクス定義、発注ロジックの完全実装）。
- research/factor_research の完実装とテスト。
- 個別銘柄の lot_size 情報を持つマスタとの統合（position_sizing の拡張）。
- 単体テスト・CI の整備、パッケージ配布手順の整備。

--- 
（注）本 CHANGELOG はリポジトリ内のソースコードから推測して作成したもので、実際のコミット履歴に基づく正確な差分ではありません。必要であればコミット履歴やリリースノートに合わせて調整してください。