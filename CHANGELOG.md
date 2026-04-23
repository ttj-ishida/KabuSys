CHANGELOG
=========
(このファイルは "Keep a Changelog" の形式に従っています。)

すべての注目すべき変更を記録します。慣例に従い、セクションは Added / Changed / Fixed / Security / etc. に分かれます。

0.1.0 - 2026-04-23
-----------------

Added
- 初期公開: KabuSys 0.1.0 をリリース。
  - 日本株自動売買システムのコア機能群を提供するモジュール群を追加。
- 実行/監視の起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 経由でペーパートレードを分離して記録。
    - 停止フラグ (data/stop_requested.flag) と実行 PID 管理 (data/execution.pid) に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視用 DB 初期化処理を含む）。
- 設定管理・ウィザード・検証
  - config.py
    - .env 自動ロード（プロジェクトルート検出ベース）を実装。
    - 環境変数パーサの強化（export 付記法、クォートとエスケープ、インラインコメント処理など）。
    - Settings クラスを提供し、アプリケーション設定（DB パス、J-Quants / kabu API、紙取引設定など）をプロパティ経由で取得。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加（既存値の再利用、シークレットマスク表示、ファイル書き出し）。
  - validate_config.py
    - 起動前の設定検証ツールを追加（必須環境変数、KABUSYS_ENV の妥当性、DB パス、config/*.yaml の存在とパース確認等）。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額重み (calc_equal_weights)、スコア重み (calc_score_weights) を実装。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用 (apply_sector_cap)、市場レジームに基づく資金乗数 (calc_regime_multiplier) を実装。
    - 未知レジーム時はフォールバック（1.0）して警告を出力。
  - portfolio/position_sizing.py
    - 単元株単位での株数計算、risk_based / equal / score の配分方式、ポジション上限・集約キャップ（available_cash）および cost_buffer を考慮したスケーリング処理を実装。
    - aggregate cap 超過時のスケールダウンと残差処理（lot_size 単位での再配分）を実装。
- utils
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 制御のユーティリティを追加。権限不足等は警告でスキップ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを集計して PASS/FAIL を出力。閾値はソース内で定義（稼働率 99%、注文成功率 90% 等）。
    - --from / --to / --db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数も使用可。
- research
  - research/factor_research.py（ファクター計算の基盤を追加。モメンタム等の計算関数を実装予定）
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- 初期リリースのため該当なし。

Fixed / Robustness
- .env 読み込みの堅牢化
  - _parse_env_line が引用符あり/なし、エスケープ、インラインコメントに適切に対応するよう実装。
  - .env 自動ロードで OS 環境変数を保護する仕組み（protected set）を導入し、不意の上書きを防止。
- validate_config の堅牢性
  - PyYAML 未インストール時は YAML 検証をスキップし警告を出す。
  - DB パスの親ディレクトリ存在チェックを行い、起動時に自動作成されるケースを考慮して警告出力。
- ロギング設定のフォールバック
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合に StreamHandler のみで継続するようにし、起動失敗を避ける。
- プロセス優先度設定の互換性強化
  - Windows / POSIX の差を吸収し、対応外 OS では警告を出してスキップするように実装。
  - 権限不足等で失敗した場合に警告でスキップ。
- ポートフォリオ/ポジション計算の堅牢化
  - 価格欠損時（価格 <= 0）の扱いをログ出力してスキップ。
  - セクター不明 ("unknown") の取り扱いを明確化（セクター上限チェックの対象外）。
- Paper report の堅牢化
  - テーブルが存在しない場合に例外（OperationalError）をキャッチし、該当指標を N/A 等で処理。

Security
- .env の扱いに関する注意を明示
  - config_setup.py に .env を絶対に Git にコミットしない旨のヘッダを追加。
  - 機密情報（トークン・パスワード）はウィザードでマスク表示。

Notes / Usage
- 主要 CLI/モジュールの起動例
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
  - KABUSYS_ENV (development|paper_trading|live)
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - DUCKDB_PATH, SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL（監視ポーリング秒）
  - PAPER_FILL_MODE（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリア回避推奨）

Breaking Changes
- 初期リリースのため互換性を壊す変更は無し。

Unreleased
- 今後の改善例（予定）
  - factor_research のファクター実装完了および単体テスト充実
  - 銘柄ごとの lot_size 対応（stocks マスタから取得）
  - position_sizing の手数料/スリッページのより詳細なモデリング
  - テストカバレッジ拡充と CI 統合

-----------------------------------------
この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとは異なる場合があります。必要があれば差分や追加の注記（リリース日、著者、コミットハッシュ等）を追記してください。