# Changelog

すべての注目すべき変更履歴を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

最新版
- リリース日: 2026-04-17
- バージョン: 0.1.0

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネント群を導入。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用にリポジトリ直下の `data/stop_requested.flag` を監視。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視用テーブルの初期化を実行）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離して動作。
    - 起動時に停止フラグを検知した場合は起動を行わず終了。実行中も停止フラグで安全にエンジン停止を行う。
    - 実行プロセスの PID 管理（`data/execution.pid` を使用）に対応。

- 設定管理
  - config.py
    - 環境変数および .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env パーサを独自実装（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応）。
    - 各種設定プロパティを持つ `Settings` クラスを提供（DB パス、PID ファイル、しきい値、Paper Trading 関連等）。
    - `PAPER_FILL_MODE` や `KABUSYS_ENV`、`LOG_LEVEL` 等のバリデーション実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）での違いを吸収し、アクセス不可や未実装 API の場合は警告を出してスキップする安全設計。

- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレーク処理）、等金額配分、スコア加重配分を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - 未知レジームは警告のうえフォールバック（1.0）。
  - portfolio/position_sizing.py
    - 単元株丸め、risk_based/equal/score ベースの発注株数計算、ポートフォリオ・アグリゲート上限でのスケールダウン（余剰キャッシュによる再配分ロジック）を実装。
    - 手数料・スリッページ見積りに対応する cost_buffer パラメータあり。

- 研究・リサーチ
  - research/factor_research.py
    - Momentum / Volatility / Value のファクター計算を DuckDB を用いて実装（prices_daily / raw_financials を参照）。
    - 各ファクターは対象日ベースで（MA200、ATR20、リターン等）を計算し、データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを標準ライブラリのみで実装。
    - pandas 等の外部依存を避けた軽量実装。
  - research/__init__.py
    - 公開 API として主要関数群をエクスポート。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとの ai_score を生成して ai_scores テーブルへ反映する処理を導入。
    - バッチ（最大 20 銘柄）・トークン肥大化対策（記事数/文字数トリム）・JSON Mode 想定・429/5xx/ネットワーク断に対する指数バックオフリトライ・レスポンスバリデーション・スコアクリッピング（±1.0）などの設計を記載。
    - API キーは引数または環境変数 `OPENAI_API_KEY` で指定。未指定時は ValueError を送出。
    - ニュース時間ウィンドウ計算のユーティリティ calc_news_window を実装（JST ベースで UTC に変換）。
    - （注）ファイル末尾で実装途中で切れている箇所があるため実行時は未完成部分に注意。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、所定の閾値に基づいて PASS/FAIL を判定。
    - コマンドライン引数 `--from`, `--to`, `--db` に対応。デフォルト DB は `data/paper_trading.db`。

- DB（DuckDB / SQLite）関連
  - DuckDB 接続を受ける設計を採用（研究/AI が DuckDB を参照）。
  - 監視や実行は必要に応じて SQLite を使用（Paper Trading 用 DB と本番 DB を分離可能）。

### 変更 (Changed)
- 設計方針
  - 研究モジュールは外部 API にアクセスせず、prices_daily / raw_financials 等のローカル DB テーブルのみを参照する方針に統一。
  - 起動スクリプト共通でプロセス優先度を起動直後に "high" に設定する動作を追加（set_process_priority 呼び出し）。
  - .env 自動読み込みで OS 環境変数を保護する仕組み（protected set）を導入。`.env.local` は OS 環境変数を上書き可能。

### 修正 (Fixed)
- ロバストネス
  - .env パーサを強化し、引用符やバックスラッシュエスケープ、コメント扱いの判定を改善。
  - process_priority と CPU affinity 設定は、権限不足や未サポート環境で失敗しても警告を出して無害にスキップするように変更。
  - Paper verification レポートで P95 計算や集計がデータ不足時に安全に N/A を返すよう実装。

### 注意点 / 既知の制限 (Known issues)
- ai/news_nlp.py の score_news 実装がファイル途中で切れているため、実行前に未実装部分の完成が必要（README やテストで確認することを推奨）。
- position_sizing.calc_position_sizes の単元株（lot_size）は現状グローバル共通パラメータで、将来的に銘柄別単元への拡張が必要（TODO コメントあり）。
- risk_adjustment.apply_sector_cap は価格データ欠損時にエクスポージャーが過小評価される可能性があるため、前日終値等のフォールバック機構が今後必要（TODO コメントあり）。
- Monitoring は環境に依らず本番 sqlite_path を使用するため、開発/検証実行時にデータ分離が必要な場合は注意。

### セキュリティ (Security)
- なし（本リリース時点で特筆すべきセキュリティ修正・脆弱性は報告されていません）。OpenAI API キー等の機密情報は環境変数で管理する設計。

---

今後の予定:
- ai/news_nlp の未完実装の完了とテスト整備。
- 銘柄別 lot_size をサポートする拡張、価格フォールバックロジックの実装。
- 監視・実行のテストカバレッジ強化とドキュメントの充実。