CHANGELOG
=========

すべての注目すべき変更履歴を記録します。フォーマットは "Keep a Changelog" に準拠します。
リリース日はコードから推測した日付を使用しています。

Unreleased
----------
（なし）

0.1.0 - 2026-04-25
-----------------

Added
- 基本リリース: KabuSys 自動売買システムの初回リリース相当の機能群を追加。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine を起動するランナー。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading 用 DB に切り替え。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定管理
  - config.py: 環境変数読み込み／Settings クラスを提供。プロジェクトルート自動検出 (.git or pyproject.toml) と .env / .env.local の自動読み込み（任意で無効化可能）。
  - config_setup.py: 対話式 .env 作成ウィザード（secret マスク表示、既存値再利用、.env ファイル書き込み）。
  - validate_config.py: 起動前に .env および config/*.yaml の基本チェックを行う CLI（--strict オプションで警告を FAIL 扱いにできる）。
- Portfolio（銘柄選定・配分・サイズ決定）
  - portfolio.portfolio_builder: シグナル選定（上位N取り）、等金額・スコア加重の重み計算。
  - portfolio.risk_adjustment: セクター上限適用、レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio.position_sizing: 単元株丸め・リスクベース / 等配分 / スコア配分による株数算出、aggregate cap によるスケール調整と切り捨て/残差配分ロジック。
  - portfolio.__init__: 主要関数のエクスポート。
- ユーティリティ
  - utils.logging_setup: 統一的ログ初期化（stdout StreamHandler + 日次ローテーションの FileHandler、ログディレクトリ自動作成、既存ハンドラのクリア）。
  - utils.process_priority: psutil を用いたプロセス優先度設定と CPU affinity 設定（Windows/Linux/Mac 対応、許可エラーを安全にスキップ）。
- データベース / 分析
  - DuckDB 統合ポイント: execution / monitoring 起動で duckdb 接続を確立（Settings.duckdb_path）。
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプト（期間指定 --from / --to、PAPER_TRADING_SQLITE_PATH 環境変数対応）。稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
- パッケージ定義
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を追加。

Changed / Behaviour
- .env の自動読み込み
  - プロジェクトルートが特定できた場合は .env（低優先）および .env.local（高優先）を自動的に読み込む。既存の OS 環境変数は保護される（上書きされない）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- .env パーサ
  - export KEY=val 形式やシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応したパーサを実装。
- run_monitoring の DB 挙動
  - 監視（monitoring）は起動環境にかかわらず本番用 sqlite_path を使用する仕様（安全設計として明示的に本番パスを参照）。
- run_execution の DB 分離
  - paper_trading 環境時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
- ロギング挙動
  - ログディレクトリの作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。既存ハンドラは初期化前に flush/close して二重出力を防止。
- モニターポーリング間隔
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能。不正（整数変換失敗や 0 以下）の場合はデフォルト 60 秒にフォールバックし警告を出力。

Fixed / Robustness improvements
- 設定検証 validate_config.py
  - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 不在時は警告でスキップ）等を実装。
  - KABUSYS_ENV=live に対する追加警告（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定の指摘）。
- process_priority / set_cpu_affinity
  - サポート外 OS やアクセス権限不足の際に例外を握り潰しログ警告で安全にスキップ。
- paper_verification_report
  - データ不足やテーブル未存在を考慮した例外ハンドリング（sqlite3.OperationalError を捕捉して N/A 表示）。
  - P95 計算で空リストに対応（None を許容）。
- Portfolio ロジック
  - スコア重みが全て 0 の場合に等金額配分へフォールバック（警告ログ）。
  - price が欠損／0 の場合作業をスキップする保護ロジックを追加（ログ出力でデバッグ可能）。
  - aggregate cap スケーリング時の切り捨て・残差配分ロジックで再現性と安全弁を確保。
- run_execution / run_monitoring の停止フラグ
  - data/stop_requested.flag、pid ファイル、起動時の停止フラグ検出を実装。停止フラグ検知時は安全にループ／エンジンを終了。

Security
- config_setup と表示機能で秘密情報はマスク表示（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN 等）。
- .env ファイル生成時に「.env は絶対に Git にコミットしないこと」を README 的に強調。

Documentation / Developer experience
- 各モジュールに docstring と使用例／設計ノートを追加（portfolio や research の設計参照の記載など）。
- CLI（config_setup, validate_config, tools.paper_verification_report）にヘルプと使い方を付記。

Notes / Known limitations
- 一部の TODO や将来的な拡張点をコード内コメントで明示:
  - position_sizing: 銘柄別の lot_size を将来的に対応予定（現在は全銘柄共通の単元数を想定）。
  - risk_adjustment.apply_sector_cap: price 欠損時にエクスポージャー過少見積の可能性あり。前日終値等でのフォールバックを検討。
- research.factor_research モジュールは計算ロジックの実装途中（ファイル末尾が途中で切れていることを示唆）であり、追加実装が必要。
- 一部機能は外部ライブラリ（psutil, duckdb, PyYAML）が必要。インストール状況により機能の一部が警告を出してスキップされる場合がある。

参考: 実行例
- 環境セットアップ: python -m kabusys.config_setup → .env 作成
- 設定検証: python -m kabusys.validate_config [--strict]
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 監視起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution

貢献・今後の予定
- research.factor_research の完成、Strategy モジュールとの統合、テストの充実（ユニットテスト／CI）、および運用監視のさらなる強化を予定しています。