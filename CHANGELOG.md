Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

v0.1.0 - 2026-04-22
-------------------

Added
- 起動スクリプトの追加/整備
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag によるフラグ検知で行う。
    - 監視用 DB は環境に関係なく（paper/live であっても）本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離。
    - 実行中の停止は data/stop_requested.flag により検知し、Engine.stop() を呼び出して安全終了を試みる。
    - 実行 pid を data/execution.pid に出力する仕組みを想定。

- 設定・環境読み込みまわり
  - config.py
    - .env 自動読み込みロジックを実装（プロジェクトルートを .git / pyproject.toml から特定）。
    - .env 行パーサを実装し、export プレフィックス、クォート文字列、エスケープ、inline コメント（スペース前の#のみ）などを正しく処理。
    - Settings クラスを提供し、各種設定（J-Quants / kabu API / DB パス / Paper Trading 用パス / 監視閾値 等）をプロパティとして取得可能に。
    - PAPER_FILL_MODE の検証（有効値チェック）・paper_sqlite_path（paper トレード用 DB）のサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能。

  - config_setup.py
    - 対話式ウィザードで .env を生成 / 更新するツールを追加。
    - シークレット項目はマスク表示、選択肢・デフォルト表示、保存前確認、キャンセル対応などを実装。

  - validate_config.py
    - .env および config/*.yaml の設定内容検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パス、YAML の存在とパース検証（PyYAML がある場合）などをチェック。
    - --strict モード（警告を FAIL 扱い）をサポート。

- ロギング / プロセス優先度ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定する共通ユーティリティを追加。
    - LOG_DIR / LOG_LEVEL と引数優先の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作。
    - stdout を用いることで cron 等の出力リダイレクト想定に対応。

  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収したプロセス優先度設定を実装（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定する実装。
    - calc_equal_weights / calc_score_weights: 等重配分・スコア加重配分を提供。全スコアが 0 の場合は等重にフォールバック（警告出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、セクター上限（max_sector_pct）を超えるセクターの新規候補を除外する実装。
      - "unknown" セクターは上限適用対象外。
      - 当日売却予定銘柄をエクスポージャ計算から除外するオプションを提供。
    - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に応じた投下資金乗数を返すユーティリティ（未知レジームは 1.0 にフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: weight / candidates / portfolio_value / cash 等から銘柄ごとの発注株数を計算。
      - risk_based, equal, score の allocation_method をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング処理を実装。
      - cost_buffer（手数料・スリッページ見積り）を考慮した保守的な評価、残余キャッシュを利用した端数配分ロジックを実装。

  - portfolio/__init__.py
    - 上記関数群をエクスポートするパッケージ初期化を追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定するレポート生成ツールを追加。
    - P95 レイテンシ計算、各種閾値定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 <= 200ms）を実装。
    - コマンドライン引数 --from / --to / --db をサポート。

- その他
  - パッケージ初期化に __version__ = "0.1.0" を設定。

Changed
- DB/ログのデフォルトパスを整理
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- ログ出力挙動
  - ログはデフォルトで stdout に出力するようにし、ファイル出力はログディレクトリの作成に成功した場合のみ有効化する設計へ変更（運用環境での一貫性確保）。

Fixed
- MONITOR_POLL_INTERVAL のパースを厳格化
  - 0 以下や整数変換失敗時は警告を出してデフォルト（60 秒）へフォールバックするように修正（time.sleep に負の数を渡して ValueError になるのを防止）。
- PAPER_FILL_MODE の不正値チェックを実装（無効なモード時は ValueError）。

Known issues
- research/factor_research.py
  - ファイル末尾が途中で切れており（calc_momentum の実装が完全に記載されていない）、このモジュールはまだ完成していません。今後のリリースで完了予定。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size サポート、price が欠損したときのフォールバック処理など）が残っています。実運用で該当ケースがある場合は追加改修が必要です。

Notes / Design decisions
- run_monitoring は監視 DB を常に本番 sqlite_path に接続する設計です（環境に依存せず監視を一元化する意図）。
- run_execution は paper_trading 時に専用の paper DB を使用して本番 DB と完全に分離することでテスト・検証を安全に行えるようにしました。
- logging_setup は stdout を採用しており、cron / systemd / コンテナ実行時にログの取り回しを容易にする方針です。
- process_priority の設定はプラットフォーム依存の挙動を包み込み、安全にフォールバックする実装になっています（権限不足時は警告でスキップ）。

Acknowledgements
- このリリースは初期機能の集合を目的としたもので、設定・運用の確認（validate_config）や環境セットアップ支援（config_setup）を重視しました。今後はテストの追加、factor_research の完成、および運用で見つかった改善点の反映を予定しています。