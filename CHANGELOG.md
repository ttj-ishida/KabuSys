# CHANGELOG

すべての notable な変更を Keep a Changelog の形式で記録します。  
日付はコードベースの取得日（2026-04-19）を基準に記載しています。実際のリリース運用に合わせて適宜更新してください。

## [Unreleased]

### 追加
- なし（初期リリースにまとめられています）。

---

## [0.1.0] - 2026-04-19

初期リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下はコードベースから推測してまとめた主要な追加点、仕様、および注意点です。

### 追加
- アプリケーション基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境・設定管理
  - Settings クラス（kabusys.config）を実装。環境変数から各種設定（J-Quants トークン、kabuAPI パスワード、DB パス、動作モードなど）を取得。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。`.env` → `.env.local` の優先順で読み込み、OS 環境変数は保護される仕様。
  - .env の行パーサで以下に対応：
    - `export KEY=val` 形式
    - シングル/ダブルクォートとバックスラッシュによるエスケープ
    - インラインコメントの扱い（クォートの有無に応じた適切な解釈）

- 起動・運用ユーティリティ
  - 対話式設定ウィザード CLI（kabusys.config_setup）を追加。`.env` の初期作成・更新を支援。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数・DBパス・config/*.yaml ファイル等のチェック、`--strict` モードをサポート。
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）を実装。コンソール(stdout) と日次ローテートファイル出力（TimedRotatingFileHandler）を統一的に設定。
  - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）を実装。Windows / POSIX を吸収し `set_process_priority` と `set_cpu_affinity` を提供。

- 実行関連スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合は MockBrokerClient を使用し、paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db）に書き込むことで本番 DB と分離。
    - 起動／停止の制御フラグ（data/stop_requested.flag、data/execution.pid）に対応。
    - リスク管理（RiskManager）にデフォルトパラメータを設定し、broker から初期現金を取得して初期化。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を実装。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下はデフォルトにフォールバックして警告）。
    - 監視用 DB 接続は環境にかかわらず本番の sqlite_path を使用する旨の挙動（監視 DB は本番パスを参照）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。例外時もループを継続して次ポーリングへ。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARNING）。
  - risk_adjustment:
    - apply_sector_cap: セクター別上限（max_sector_pct）を考慮して候補を除外（unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数。未知レジームは警告して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を算出。単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）を考慮し、cost_buffer を乗じた保守的見積りでスケーリングするロジックを実装。

- 実行 / 検証ツール
  - paper_verification_report（kabusys.tools.paper_verification_report）を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポート出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- 研究用モジュール
  - factor_research（kabusys.research.factor_research）を追加（モメンタム等のファクター計算を実装予定）。DuckDB の prices_daily / raw_financials を参照してファクターを算出する設計。ファイルは途中まで実装（続きがある想定）。

### 変更
- なし（初期リリースのため変更履歴はなし）。

### 修正
- なし（初期リリース）。

### 破壊的変更（Breaking Changes）
- 監視（run_monitoring）が「環境にかかわらず本番 sqlite_path を使用する」仕様は運用上の重要な挙動です。監視 DB を分離したい場合は運用ドキュメントで明示的に扱うか、設定を追加する必要があります。

### セキュリティ
- .env ファイルについて明示的に「絶対に Git にコミットしないこと」と警告を出力するテンプレートを config_setup に付与。
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を強制し、未設定またはプレースホルダ値の場合に警告・エラーを出す validate_config を提供。

### 既知の問題 / 注意点
- factor_research モジュールは途中実装に見えるため、完全なファクター計算ロジックは未完成の可能性がある。
- process_priority / set_cpu_affinity はプラットフォーム依存・権限依存で失敗する場合があり、失敗時は警告を出してスキップする挙動。
- logging_setup はログディレクトリの作成に失敗した場合、ファイル出力を無効化して標準出力のみで継続する設計。
- .env パーサは多くのケースに対応しているが、非常に複雑なケース（複数行クォートなど）は想定外の挙動を示す可能性あり。

---

メンテナンス運用の推奨:
- 本番運用前に `python -m kabusys.validate_config` で設定を検証してください。
- `.env` の内容は config_setup で生成し、秘密情報は安全に管理してください。
- Paper Trading と本番 DB を完全に分離する運用ルールを明確化してください（run_monitoring の挙動に注意）。