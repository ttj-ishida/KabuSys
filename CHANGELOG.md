# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリース: KabuSys 日本株自動売買システムの基本モジュール一式を追加。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）と完全に分離して動作する。
    - SQLite / DuckDB 接続を確立し、監視用テーブルの初期化を行う。
    - 停止フラグ（data/stop_requested.flag）を検知して安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検知でループを終了、KeyboardInterrupt に対するハンドリングを実装。
- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - .env/.env.local の読み込みロジック（上書きルール・OS環境変数保護）と、.env 行パーサを実装（シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視閾値 /環境フラグ等のプロパティ化を提供。環境変数値の妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
    - settings 単一インスタンスをエクスポート。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。シークレット値のマスク表示や選択肢サポート、.env ファイル書き出しテンプレートを提供。
  - validate_config.py
    - 起動前検証用 CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML が無ければスキップ）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定する共通ユーティリティを実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを持つ。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。
  - utils/process_priority.py
    - Windows/Linux/Mac の差を吸収してプロセス優先度（high/normal/low）を設定する関数を提供。psutil を用い、権限不足や未サポート OS の場合は警告を出してスキップする。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（オプション）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定（スコア降順、タイブレークルール）および等金額・スコア加重の重み計算を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（既存保有のセクター露出を計算して新規候補を除外）と、市場レジームに応じた投下資金乗数（regime multiplier）を実装。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap スケーリング、コストバッファ（手数料・スリッページ見積）を実装。
    - 一部将来の拡張（銘柄別 lot_size 等）に関する TODO コメントを追加。
- 監視・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。指標の閾値はソース中で定義（稼働率 99.0%、成立率 90% 等）。
- 研究用モジュール
  - research/factor_research.py
    - DuckDB を用いたファクター計算の骨組みを追加（モメンタム、移動平均乖離、ATR、流動性など）。calc_momentum をはじめとする関数群を定義（実装方針と定数を含む）。※ ソースに未完の箇所あり（後述）。
- パッケージ初期化
  - __init__.py にバージョン文字列 __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ でエクスポート。

### 変更 (Changed)
- 該当なし（初期リリースのため）。

### 修正 (Fixed)
- 該当なし（初期リリースのため）。

### 既知の問題 / 注意事項 (Notes)
- research/factor_research.py の calc_momentum 実装が途中で切れている（ソースに不完全な行が存在）。本格運用前にファクター計算ロジックの完成とテストが必要。
- position_sizing.calc_position_sizes と risk_adjustment.apply_sector_cap 内に価格が欠損した場合のフォールバックが TODO コメントとして残っている（前日終値や取得原価のフォールバックを検討する必要あり）。
- process_priority.set_process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に動作しない可能性があり、その場合は警告を出してスキップする設計になっている。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで継続する。デプロイ環境でのログディレクトリ権限を事前に確認することを推奨。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 以上の整数でないとデフォルト（60 秒）にフォールバックする。0 や負数、非数は警告ログが出る。
- validate_config は PyYAML が未インストールの場合、config/*.yaml の中身検証をスキップする（代わりに警告を出す）。

### セキュリティ (Security)
- 該当なし。

---

今後の予定（例）
- factor_research の完成とユニットテスト追加
- Broker クライアントのモック/実クライアント切替のドキュメント整備
- 各 CLI のユニットテスト・統合テスト整備
- 銘柄別 lot_size 等の position_sizing の拡張

変更点の詳細や追加の説明が必要であればお知らせください。