# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成したリリースノートです（自動生成・推測による内容を含みます）。

## [0.1.0] - 2026-04-17

### Added
- 基本機能の初回リリース。
- 実行エントリ / ユーティリティ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御ファイル data/stop_requested.flag を検知してループを終了。
    - 監視用 DB は環境に依らず production の sqlite_path を使用。
    - check_once() の例外を捕捉して次のポーリングに継続する堅牢化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - 停止フラグと execution.pid を使用した起動/停止制御を実装。
    - ExecutionEngine をスレッドで起動し、停止フラグ検知でエンジン停止。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - 稼働率、注文成功率・送信率、レイテンシなどを集計・判定する CLI。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプション対応。

- 設定・検証系
  - config.py: 環境設定読み込み・Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - .env / .env.local の自動ロード機構（OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env 行パーサは export 構文、クォート、バックスラッシュエスケープ、インラインコメントに対応。
    - 各種環境変数取得用プロパティ（DB パス、PID パス、閾値、PAPER_FILL_MODE 等）を提供。値検証（有効値チェック）を実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - .env の既存値読み込み、マスク表示、選択肢・デフォルト提示、確認後ファイル書込みを実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、ライブ環境向けガード等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を追加。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を回避するフィルタを実装（売却予定銘柄の除外、"unknown" セクター扱いの挙動明示）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数を返す（bull/neutral/bear + 未知レジームでフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数決定ロジックを実装。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash に合わせたスケーリング）、cost_buffer（手数料・スリッページ見積り）考慮、残差処理による追加入庫のロジックを実装。

- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB に対して Momentum / Volatility / Liquidity / Value 系ファクターを計算する関数を追加（prices_daily / raw_financials を参照）。
    - モメンタムや MA200 乖離、ATR、20日平均出来高などを計算。データ不足時の None 処理を実装。
    - 計算ウィンドウやスキャン日数等の定数を定義。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) により Windows / POSIX を吸収した優先度設定を実装（psutil 利用）。
    - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を固定（可能な環境でのみ）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- パッケージ管理
  - __init__.py に __version__="0.1.0" を設定。

### Changed
- 監視・実行の挙動設計に安全ガードを導入（プロセス優先度設定を起動初期に行う、停止フラグ検知で優雅に終了）。
- run_execution は paper_trading 環境時に専用 DB を使用することで本番データと完全分離する設計を明確化。
- config の自動 .env ロードは OS 環境変数を保護するため既存キーを上書きしない（.env.local は上書き可能）。

### Fixed
- .env パーサの改善（クォート内のバックスラッシュエスケープ、export 形式のサポート、インラインコメント処理）により一般的な .env 形式の誤読を回避。
- MONITOR_POLL_INTERVAL の不正値（0 以下や数値以外）に対してデフォルトにフォールバックし、ログ出力で警告するように修正。
- PAPER_FILL_MODE の無効値に対して明示的な ValueError を発生させ、設定ミスを早期検出するように修正。
- DuckDB / SQLite 接続やテーブル未存在時の例外を監視ツールやレポートで耐障害化（例: OperationalError を捕捉して N/A 扱いに）。

### Documentation / UX
- config_setup.py の対話ウィザードでシークレット値をマスク表示、説明文と選択肢を提示。生成される .env にヘッダコメントを付与して注意喚起（.env を Git にコミットしない旨）。
- validate_config.py は INFO/WARNING/ERROR を出力し、状況に応じたメッセージと次のステップ案内を出力。

### Security
- 環境変数の取り扱いにおいて、OS 環境変数を保護する設計（.env の自動上書きを制御）を導入。

---

注記:
- 上記は提供されたソースコード内容から推測して作成した CHANGELOG です。実際のコミット履歴や外部ドキュメントが存在する場合はそれに合わせて調整してください。