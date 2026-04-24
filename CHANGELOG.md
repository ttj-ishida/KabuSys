CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。
次のバージョンは semver に従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
-------------------

Added
- 基本機能・モジュールの初期実装（初回リリース）。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全分離する設計（README 参照）。
      - 起動時にプロセス優先度を "high" に設定。
      - 停止フラグ（data/stop_requested.flag）検出でエンジン停止。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値（0 以下や整数変換できないもの）は警告ログを出してデフォルトにフォールバック。
      - Monitoring は環境（KABUSYS_ENV）にかかわらず settings.sqlite_path（本番想定）を使用する設計。
      - 停止フラグ検出でループを終了、KeyboardInterrupt をハンドルして終了処理を行う。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - 自動読み込みを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
      - Settings クラスで各種環境変数をプロパティとして提供（J-Quants / kabu / LINE / DB パス / 監視閾値など）。入力値検証（列挙値チェックや数値変換）を行う。
      - paper_trading 用の paper_sqlite_path、paper_fill_mode（instant/partial/never/reject）をサポート。
  - 設定ツール
    - config_setup.py
      - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレットはマスクして表示。
    - validate_config.py
      - .env と config/*.yaml を事前検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、YAML ファイルの存在・パース（PyYAML が未インストールの場合は警告）を実施。
      - --strict を指定すると警告も失敗扱い（exit 1）。
  - ロギングとプロセス制御ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ初期化関数 setup_logging を実装。
      - stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - utils/process_priority.py
      - set_process_priority(level) を実装（"high"|"normal"|"low"）。Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収する実装で、権限不足や未対応 OS は警告でスキップ。
      - set_cpu_affinity(cpu_count) を実装（最初の N コアにピン留め）。権限がない場合は警告でスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）。
      - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックして警告）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap：既存ポジションからセクター別エクスポージャを計算し、1セクター上限（max_sector_pct）を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes：allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。単元株（lot_size）で丸め、1銘柄上限、aggregate cap（available_cash）でスケールダウンするアルゴリズムを実装。cost_buffer による保守的見積もりを考慮。
  - リサーチ
    - research/factor_research.py（モジュール骨組みと定数を追加）
      - モメンタム等ファクター計算の方針と定数を定義（1M/3M/6M リターン、MA200、ATR、出来高等）。（実装はファイル内で継続予定）
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 検証レポート生成ツールを追加。
      - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（P95）などを計算して PASS/FAIL を判定。デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
      - P95 計算、日付フィルタ（--from / --to）をサポート。
  - パッケージ初期情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues
- apply_sector_cap の価格が欠損（0.0）の場合、エクスポージャが過少見積りされる可能性がある旨を TODO コメントで記載。将来的に前日終値や取得原価をフォールバックする予定。
- position_sizing.calc_position_sizes は現状、全銘柄共通の lot_size（デフォルト 100）を使用。将来的に銘柄別 lot_size を持たせる設計への拡張を予定（TODO）。
- monitoring は意図的に settings.sqlite_path（本番向けのパス）を使用する設計になっているため、開発環境で分離したい場合は sqlite_path の環境変数を明示的に設定してください。
- research/factor_research.py の calc_momentum 等の実装はファイル末尾で続く想定（本リリースで一部のみ提供／未完の箇所あり）。

注記
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートはリポジトリのコミット履歴やリリース方針に従って適宜調整してください。