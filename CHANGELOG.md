CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
このファイルは Keep a Changelog のフォーマットに準拠します。

フォーマットの説明:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

Unreleased
---------

- なし（次回リリースにて詳細を反映予定）

0.1.0 - 2026-04-25
------------------

Added
- 基本アプリケーション骨格を追加（初回リリース）。
  - pakage: kabusys の __version__ を 0.1.0 に設定。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）にデータを記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応し、停止要求で安全にエンジンを終了。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを扱う。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグでループ終了。
- 環境設定管理を追加。
  - config.py
    - Settings クラスを導入。環境変数から各種設定を取得（DB パス、API トークン、ログレベル、各種閾値など）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。読み込み順は OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export 形式、クォート、インラインコメントを扱う。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - helper プロパティ: is_live / is_paper / is_dev。
- .env 初期作成ウィザードを追加。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新可能。
    - デフォルト値や選択肢、シークレットマスク表示などのユーザーインタラクションを提供。
    - 最終確認のうえ .env を書き出す。
- 設定検証 CLI を追加。
  - validate_config.py
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - KABUSYS_ENV=live 向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギングユーティリティを追加。
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を提供。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR 環境変数を尊重。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで動作。
    - 既存ハンドラをクリアして二重設定を防止。
- プロセス優先度・CPU 固定ユーティリティを追加。
  - utils/process_priority.py
    - set_process_priority(level)（high/normal/low）を提供。Windows と POSIX（Linux/Mac/FreeBSD）を吸収。
    - set_cpu_affinity(cpu_count) により最初の N コアに固定可能。
    - psutil による設定を試み、権限不足等は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリを追加。
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み配分（スコア全 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、過剰セクターの候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3）。未知レジームは警告とともに 1.0 フォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジック。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）スケーリング、cost_buffer による保守的見積りを実装。
    - risk_based: risk_pct / stop_loss_pct を用いたポジションサイズ算出。
- Paper Trading 検証レポートツールを追加。
  - tools/paper_verification_report.py
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を対象に検証レポートを生成。
    - CLI 引数: --from / --to / --db。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）。
    - 合格閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）と PASS/FAIL 判定を出力。
- research/factor_research.py（ファクター計算モジュール）を追加（Momentum 等の計算ロジックを実装予定、モジュールは部分実装）。
  - DuckDB を用いた prices_daily / raw_financials 参照設計。

Changed
- なし（初回公開）

Fixed
- なし（初回公開）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 今後の予定
- research/factor_research.py はファイル末尾が未完で一部実装が途中です。今後のリリースで完了予定（モメンタム等のファクター計算の実装完了、ユニットテスト追加）。
- position_sizing の lot_size は現在全銘柄共通の想定。将来的に銘柄別 lot_map を受け取る拡張を検討。
- apply_sector_cap 内の価格欠損時のフォールバック（前日終値など）に関する TODO があり、将来的に改善予定。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後や特定配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に制御してください。

ライセンスや貢献規約、開発ドキュメント等は別途参照してください。