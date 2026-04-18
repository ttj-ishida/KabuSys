# Changelog

すべての注目すべき変更履歴をここに記載します。  
本ファイルは Keep a Changelog の形式に準拠しています。  
詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし（将来の変更をここに記載）

## [0.1.0] - 2026-04-18
初回リリース。KabuSys の基本コンポーネント（設定管理、起動スクリプト、ポートフォリオ構築、ユーティリティ、ツール類）を追加。

### Added
- 基本パッケージ情報
  - `src/kabusys/__init__.py` にバージョン情報 `__version__ = "0.1.0"` を追加。

- 設定管理
  - `src/kabusys/config.py`
    - .env 自動読み込み機能を提供（プロジェクトルートを `.git` または `pyproject.toml` から特定）。
    - .env の読み込みで `export KEY=val` 形式、クォート文字列、バックスラッシュエスケープ、行内コメントを適切に処理するパーサを実装。
    - 環境変数の必須チェック `_require()` と各種プロパティ（DBパス、APIトークン、環境種別、ログレベル、紙トレード用設定など）を `Settings` クラスで提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化に対応。

- 設定ウィザード / 検証 CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を作成・更新する機能を追加。項目定義・既存値読み込み・保存をサポート。
  - `src/kabusys/validate_config.py`
    - 起動前に環境変数や `config/*.yaml` を検証する CLI を追加。
    - PyYAML が存在する場合は YAML のパース検証を行い、存在しない場合は警告を出力。
    - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動用スクリプト。プロセス優先度設定、DB 接続（paper_trading 時は専用 DB を使用して本番 DB と分離）、ブローカークライアント生成、依存コンポーネント組立、デーモン実行・停止フラグ監視を実装。
    - 停止フラグファイル（data/stop_requested.flag）を検出して安全に停止する仕組み。
    - paper_trading 環境では MockBrokerClient を使用して `data/paper_trading.db` に記録（注釈としての挙動説明）。

  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でループ間隔を上書き可能（デフォルト 60 秒）。不正値／非正の値は警告を出してデフォルトにフォールバック。
    - 監視プロセスも本番用の sqlite_path を使用して監視テーブルを初期化。

- 監視 DB 初期化
  - `src/kabusys/monitoring/monitoring_db.py`（参照されているが本チェンジログでは主要機能として言及）
    - 監視テーブルの初期化を idempotent に行う呼び出しをスクリプトから利用。

- ロギング & プロセス管理ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガー設定ユーティリティを追加。stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler を設定（デフォルト logs/ に出力、30 日分ローテート）。
    - LOG_LEVEL / LOG_DIR の解決順やハンドラの二重登録防止処理を実装。
    - ファイル出力ディレクトリ作成失敗時はコンソール出力のみで動作継続。

  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームなプロセス優先度設定ユーティリティを追加（Windows の priority class、POSIX の nice 値を吸収）。
    - CPU affinity 固定関数 `set_cpu_affinity()` を実装（利用可能なコア数を考慮、アクセス権限等の失敗は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、同点は signal_rank による tiebreak）、等重・スコア重みの計算関数を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限適用（既存保有のセクター比率を計算して新規候補を除外）と市場レジームに対する投下資金乗数（bull/neutral/bear）を実装。
    - 未知レジームや unknown セクターへのフォールバック動作を定義。
  - `src/kabusys/portfolio/position_sizing.py`
    - allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、集計上限（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した安全な配分ロジックを実装。

- 解析・リサーチ
  - `src/kabusys/research/factor_research.py`（骨組み）
    - DuckDB 接続を受け取り、モメンタム等のファクター算出を行うための関数群（設計方針、定数、calc_momentum の雛形）を追加（未完部分あり、設計に則した API を提供）。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを算出して PASS/FAIL 判定を出力。
    - P95 算出ロジック、期間フィルタ、SQLite からの耐障害性のあるクエリ実行を実装。
    - 環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで DB を指定可能。

### Changed
- ログ出力の標準化
  - 全起動スクリプトが logging_setup.setup_logging を呼ぶことでログ出力の形式・ファイルローテーションが統一された。

- .env 読み込み順の明確化
  - OS 環境変数 > .env.local > .env の優先順位で読み込まれる仕様を明示。既存の OS 環境変数は保護され、.env.local での上書きは許容される（ただし保護されたキーは上書きされない）。

- 安全性 / 耐障害性の向上
  - 各種ファイル I/O（ログディレクトリ作成、.env 読み込み、SQLite / DuckDB の接続）で失敗しても適切にフォールバックして継続動作するように設計。
  - `run_monitoring` のポーリングループは例外を捕捉してログに記録し、次回ポーリングに継続するようになっている。
  - `run_execution` / `run_monitoring` で停止フラグを検出した場合に安全に停止する機構を導入。

### Fixed
- 環境変数パーシングの厳密化
  - `config._parse_env_line` がクォート付き値のエスケープと閉じクォート探索、インラインコメントの扱いを正しく処理するよう改善（`export ` プレフィックス対応含む）。

- ポーリング間隔の不正値ハンドリング
  - `run_monitoring._get_poll_interval()` が負の値や 0、非数文字列に対して警告を出しデフォルト（60 秒）にフォールバックすることで `time.sleep` に渡したときの ValueError を防止。

- position sizing の集計スケール処理
  - 利用可能資金を超えた場合にスケールダウンし、残余キャッシュで lot_size 単位の追加配分を行うロジックの実装によりオーダー決定がより保守的かつ再現性を持つように修正。

### Documentation
- 各モジュールに docstring を追加し、設計方針・使用方法・主要引数の説明を充実させた（設定モジュール、ウィザード、検証ツール、ログ設定、プロセス優先度、ポートフォリオ関連、検証レポート等）。

### Security
- 機密情報（API トークン・パスワード等）は .env に保存する想定で、config_setup の出力に明示的に「.env は絶対に Git にコミットしないこと」を記載。

---

注: 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば、実際の git コミットログを基に正確な CHANGELOG を生成できます。