# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

履歴はコードベースから推測して記載しています（実装意図・利用方法を含む推定が含まれます）。

## [Unreleased]

### Added
- ドキュメント化 / ツール
  - 対話式 .env 作成ウィザードを追加（kabusys.config_setup）。既存値の読み込み／編集、シークレットマスク表示、.env の書き出し機能を提供。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数や config/*.yaml の存在・パースを事前チェックし、--strict モードで警告を FAIL 扱いにできる。
  - Paper Trading 用検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。稼働率、注文成立率、送信率、API レイテンシ（P95）などの集計と PASS/FAIL 判定を出力。
- 実行スクリプト
  - SystemMonitor のポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）の検出、例外時のログ出力、sqlite/duckdb のクローズ処理を行う。
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。KABUSYS_ENV=paper_trading 時は paper 専用 SQLite を使用し本番 DB と分離。Broker クライアントのファクトリ利用、エンジンスレッド起動・停止制御、PID ファイルパス管理、停止フラグ検知による安全停止を実装。
- 設定管理
  - Settings クラス（kabusys.config）を導入。環境変数の取得ラッパー、型変換、検証（KABUSYS_ENV、LOG_LEVEL 等）、デフォルトパス（duckdb, sqlite 等）や paper_trading 用パス分離を提供。
  - .env 自動ロード機能を実装（プロジェクトルート自動検出：.git または pyproject.toml を基準）。OS 環境変数を保護する protected モードや .env.local 上書きルールを採用。自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - .env パーサー改良：export プレフィックス対応、クォート文字内のバックスラッシュエスケープ処理、行内コメントの扱い等を実装（複雑な .env の妥当な扱いを想定）。
- ポートフォリオ構築（純粋関数群）
  - 候補選定および重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順・同点時は signal_rank でタイブレーク
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化（全スコア 0 の場合は等金額にフォールバック）
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中上限チェック（売却予定コードを除外可能）。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム毎の投下資金乗数（bull/neutral/bear、未知レジームはフォールバックと警告）
  - ポジションサイジング（kabusys.portfolio.position_sizing）
    - risk_based / equal / score の配分ロジック、単元株（lot_size）丸め、per-stock 上限・aggregate cap（利用可能現金）によるスケーリング、コストバッファ考慮、残余配分ルールを実装。
- ユーティリティ
  - ロギングセットアップ（kabusys.utils.logging_setup）
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、作成失敗時はファイル出力をスキップするフェイルセーフ。ログレベル / ログディレクトリの解決優先度を提供。
  - プロセス優先度／CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX を吸収する set_process_priority: "high"/"normal"/"low" を指定可能（psutil ベース）。set_cpu_affinity によりプロセスを先頭 N コアにピン留め可能。権限不足や未対応環境では警告ログでフォールバック。
- データ分析 / リサーチ
  - 基本的なファクター計算モジュールを追加（kabusys.research.factor_research）。Momentum（1M/3M/6M、MA200乖離）、ATR、流動性等を DuckDB の prices_daily / raw_financials を参照して計算する設計（関数インターフェース・定数を定義）。

### Changed
- DB 周りの挙動
  - 監視（monitoring）プロセスは KABUSYS_ENV に関係なく本番 sqlite_path を使用する設計に変更（監視データは常に単一の場所に集約する想定）。
  - ExecutionEngine は paper_trading 環境なら paper_sqlite_path を使用し、本番と完全に分離して記録する。
- ログの取り扱い
  - ログ出力は標準エラーではなく標準出力（stdout）を採用。cron や Task Scheduler で stdout/stderr を一本化して使う運用を想定。
- .env 読み込み順序
  - OS 環境 > .env.local（上書き）> .env（未設定時に適用）という読み込み優先度。OS 環境変数は保護（protected）され、自動ロードを無効にするフラグを追加。

### Fixed / Robustness
- 各起動スクリプトでプロセス優先度を最初に設定するようにして、重要プロセスの優先度問題に対処。
- run_monitoring / run_execution: stop flag の検知ループと例外ハンドリング（monitor.check_once() の例外をログ出力して継続）で安全に長時間稼働できるように改善。
- .env 読み込みでファイル I/O エラーを warnings.warn により非致命的に扱う（フォールトトレランス）。
- logging_setup: 既存ハンドラを安全に flush/close してからクリアすることで二重登録を防止。

### Removed
- 該当なし（初期リリース想定）

### Security
- シークレット値（J-Quants トークン、kabu API パスワード、LINE トークン）は Settings で必須扱いにし、config_setup では入力時にマスク表示。ファイルや .env を Git にコミットしないようウィザード注記を追加。

---

## [0.1.0] - initial release (推定)
リリース: 初期リリース。上記の機能群（設定管理、起動スクリプト、ポートフォリオ構築、ポジションサイジング、ロギング・プロセス制御ユーティリティ、検証・ウィザード・検証レポートツール、リサーチの骨子）を実装。

- 主要なエントリポイント・モジュール一覧（実装済み／追加）
  - kabusys.__init__ にてバージョンを "0.1.0" と定義
  - 起動スクリプト: run_monitoring.py, run_execution.py
  - 設定: config.py, config_setup.py, validate_config.py
  - ポートフォリオ: portfolio/{portfolio_builder, position_sizing, risk_adjustment}.py
  - ユーティリティ: utils/{logging_setup, process_priority}.py
  - ツール: tools/paper_verification_report.py
  - リサーチ: research/factor_research.py（モジュール骨子・定数・calc_momentum 等のインターフェース実装）

- 動作・運用上の設計方針（要点）
  - 本番とペーパートレードのデータを分離して扱う設計
  - ログの一元管理（stdout＋日次ファイルローテーション）
  - 環境変数の自動ロード・検証ツールを備えた運用フロー
  - 単体関数中心の純粋関数実装によりテスト容易性を確保

---

## 既知の制約・ TODO / 注意事項（コードからの推測）
- factor_research.calc_momentum の実装が途中で途切れているように見える（ファイル末尾付近）。完全実装が必要。
- position_sizing の lot_size 固定（現状全銘柄で共通 100）／銘柄別単元対応は将来的な拡張予定。
- apply_sector_cap の価格欠損（price = 0）の扱いに TODO コメントあり。フォールバック価格（前日終値等）での改善が推奨される。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームで無視されるため、期待通りに動作しない場合がある（ログで警告）。
- .env パーサは多くのケースを扱うが、極端なフォーマットや複雑なコメント組み合わせでは想定外の挙動をする可能性あり。

---

（この CHANGELOG はコードの内容から推測して作成しました。実際の変更履歴・日付やリリースノートは開発履歴に合わせて調整してください。）