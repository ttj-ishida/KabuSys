Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。コードベースから推測できる「目立つ変更点／追加機能」を日本語で整理しています。リリースバージョンはパッケージ内の __version__ (0.1.0) を元にし、日付は本日（2026-04-18）を付けています。必要に応じて日付やカテゴリの調整をしてください。

KEEP A CHANGELOG
================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従います。

0.1.0 - 2026-04-18
------------------

Added
- 起動スクリプトを追加
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 停止制御に data/stop_requested.flag を使用。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB に記録）。
    - duckdb と sqlite の両接続を確立し、監視 DB を初期化してからループを実行。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成（paper_trading 時は Mock を使用する想定）。
    - エンジンの PID ファイル管理、停止フラグ監視（data/stop_requested.flag）に対応。スレッドで engine.run_session を起動。
    - 起動時にプロセス優先度を "high" に設定。

- 環境設定・検証関連
  - src/kabusys/config.py
    - .env ファイルの自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から発見）。
    - .env パースで export 形式、クォート文字列（バックスラッシュエスケープ対応）、インラインコメントの扱いを実装。
    - Settings クラスを導入してアプリ設定をプロパティ経由で取得（J-Quants トークン、kabu API パスワード、DB パス、paper_trading 用設定、監視閾値、環境判定ユーティリティ等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
  - src/kabusys/config_setup.py
    - インタラクティブな .env 作成／更新ウィザードを追加。主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch 等）を対話式に生成・保存可能。
    - .env を生成する際のテンプレートと注意書きを出力（Git にコミットしない旨の注意含む）。
  - src/kabusys/validate_config.py
    - .env や config/*.yaml の起動前チェック CLI を追加。
    - 必須環境変数未設定の検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML のパース検査（PyYAML がある場合）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定チェック）を実装。

- ロギング・プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一されたロギング初期化関数 setup_logging を追加。StreamHandler（stdout）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決と既存ハンドラのクリアを実装。
    - ファイル出力に失敗した場合はコンソールのみで継続。
  - src/kabusys/utils/process_priority.py
    - set_process_priority, set_cpu_affinity を追加。Windows (psutil の優先度定数) と POSIX (nice 値) を吸収し、プラットフォーム差分を隠蔽。権限不足等の失敗時は警告を出してスキップ。

- ポートフォリオ構築関連
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。unknown セクターは制限を適用しない等の挙動を documented。
  - src/kabusys/portfolio/position_sizing.py
    - 株数計算ロジック（calc_position_sizes）を実装。allocation_method による振る舞い（risk_based / equal / score）、単元株丸め、単銘柄上限・集計上限のスケールダウン、コストバッファ、lot_size による残差配分ロジックなどを実装。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
    - --from/--to による日付フィルタと --db オプションで DB パス指定が可能。P95 の計算補助や None 値の扱いを実装。

- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- .env 読み込み方針の確立
  - 自動 .env 読み込みの優先順位を明示（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
  - _load_env_file の override/protected 引数で既存 OS 環境変数を上書きしない保護機構を導入。

- ロギングの標準化
  - すべての起動スクリプトは setup_logging を呼び出して統一したログ設定を行うように変更（実装）。

Fixed
- .env パーサーの堅牢化
  - export 付き行や引用符内のバックスラッシュエスケープ、行内コメントの扱いを正しく処理するよう改善。無効行をスキップすることで読み込みの安定性を向上。

Security
- .env の取り扱いに関する注意
  - config_setup に生成ヘッダで「.env は絶対に Git にコミットしないこと」と明示的な注意を追加。

Notes / Implementation details（実装上の重要点・注意）
- run_monitoring は MONITOR_POLL_INTERVAL に不正値が設定されている場合に警告してデフォルトにフォールバックする実装になっている（time.sleep に負の値を渡さないため）。
- run_execution は paper_trading モードで専用の SQLite を使用することで本番データと完全に分離する設計。RiskManager の初期設定で initial_portfolio_value に broker.get_available_cash() を参照しているため、BrokerClient 実装は起動時に利用可能現金を返す必要がある。
- position sizing のスケールダウン処理は lot_size 単位の丸めと fractional remainder の再配分を行い、利用可能現金に収めるロジックを採用している。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合は警告でスキップし、安全に動作を継続できる。

今後の提案（参考）
- validate_config の YAML 検証を強化して config/*.yaml のスキーマ検証を追加するとさらに起動前信頼性が向上します。
- run_monitoring の永続化（systemd/サービス定義）や run_execution のデーモン運用サポートを追加すると運用が楽になります。
- portfolio/position_sizing の lot_size を銘柄別に指定できるよう拡張（stocks マスタに lot_size を持たせる）する予定が既にコメントに記載されているため、将来の改善計画として取り込むと良いです。

--- 

必要であれば、リリースノートを英語版にする、日付を変更する、各エントリに該当するコミットハッシュや影響範囲（影響するモジュール・設定）を付加することも可能です。どのように整形・公開したいか指示ください。