# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はこのスナップショットの作成日です。

## [0.1.0] - 2026-04-16

### Added
- 全体
  - 初期公開リリース。本パッケージは日本株自動売買システム「KabuSys」のコアユーティリティ群を提供します。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記。
    - stop フラグファイル（data/stop_requested.flag）検知による安全停止実装。
    - DuckDB 接続を使用して分析用 DB と連携。
    - プロセス優先度を起動時に "high" に設定する処理を実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=`paper_trading` の場合は専用（分離された）Paper Trading 用 SQLite（`data/paper_trading.db`）を使用し、MockBrokerClient を利用する設計。
    - 停止フラグおよび実行用 PID ファイル管理（data/execution.pid）。
    - エンジンを別スレッドで起動し、停止フラグ検知で安全に停止する制御。

- 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）を実装し、.env / .env.local の自動読み込みをサポート（OS 環境変数の保護機能あり）。
    - .env パーサは export 構文、クォート文字列内のエスケープ、コメント処理など多様なケースに対応。
    - 環境変数をラップする `Settings` クラスを導入。J-Quants / kabu / LINE / DB / 監視閾値 / システム設定 等のプロパティを提供。
    - `PAPER_FILL_MODE` に対する入力検証（有効値: instant|partial|never|reject）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。
    - `env` / `log_level` の値検証実装（許容値チェック）。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収してプロセス優先度を設定するユーティリティを追加（Windows / POSIX 対応）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装。
    - 権限不足や未対応環境でフォールバックする安全な実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等配分・スコア加重配分の算出関数を追加。
    - スコア合計が 0 の場合に等配分へフォールバックする挙動を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が閾値を超える場合に候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の注文株数決定ロジックを実装（allocation_method: risk_based, equal, score）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケールダウン（余剰キャッシュを考慮した端数配分）に対応。
    - コストバッファ（手数料・スリッページ見積）を考慮した保守的な計算。

- 研究（Research）
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算関数を追加（DuckDB 接続を受け prices_daily/raw_financials を参照）。
    - MA200・ATR20・過去リターン等を SQL ウィンドウ関数で効率的に計算。
  - research/feature_exploration.py
    - 将来リターン計算、スピアマンランク相関（IC）、ファクター統計サマリ、ランク化ユーティリティを実装。
    - 外部ライブラリに依存せずに純粋 Python 実装。

- AI / ニュース解析
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して銘柄ごとに ai_scores テーブルへ書き込む機能を追加。
    - タイムウィンドウ（JST 基準）計算、記事集約、1銘柄あたりの文字数・記事数トリム、バッチ送信（最大 20 銘柄/回）、JSON Mode 期待のレスポンスバリデーション、スコア ±1.0 クリップ、リトライ（429/5xx/ネットワーク断）に基づくエクスポネンシャルバックオフを実装。
    - OpenAI API キー解決（引数 / 環境変数）と未設定時の例外。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出。
    - PASS/FAIL 判定基準（閾値）を定義し、期間フィルタ（--from/--to）に対応。
    - DB が存在しない場合のエラーメッセージや、テーブル欠落時の堅牢なデフォルト処理を実装。

- パッケージエクスポート
  - research と portfolio モジュールの主要関数を __all__ で公開。

### Changed
- 監視 / 実行起動に関する挙動整理
  - run_monitoring は Monitoring 用に常に本番 sqlite_path を使用する仕様を明示（環境に依存しない監視 DB 利用）。
  - run_execution は paper_trading 環境時に専用 DB を使用して本番 DB と完全分離する挙動を採用。

- 環境変数ロードの順序と保護
  - .env 自動ロード時、OS 環境変数を保護しつつ `.env` → `.env.local`（上書き）を適用する順序で読み込む動作を採用。

### Fixed
- 入力検証と安全ガード
  - MONITOR_POLL_INTERVAL の不正値（非数値・0 以下）に対するフォールバック処理を追加（ログ警告してデフォルト 60 秒を使用）。
  - Settings の各種プロパティで不正値が渡された場合に早期に ValueError を投げるようにし、誤設定の検出を容易に。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは明示的に引数渡しまたは環境変数から解決し、未設定時はエラーにすることで誤送信・誤実行を防止。

---

## Unreleased / TODO / 既知の制約
- ai/news_nlp.py
  - 実装説明は詳細に記載済みだが、現ファイルの末尾で記事取得関連処理の続きを期待する箇所（_fetch_articles 等の呼び出し以降）が途中で切れているため、完全な DB からの取得・aggregatation → API 呼び出し → DB 書き戻しの一連処理の実装が必要（本 CHANGELOG 作成時点のソースが切れていることを確認）。
- price の欠損処理
  - risk_adjustment.apply_sector_cap 内の TODO: price が欠損（0.0）だった場合にエクスポージャーが過小見積りされる問題について、将来的に前日終値や取得原価でのフォールバックを検討する旨の注記あり。
- 単体テスト・エンドツーエンドテスト
  - 主要ロジックは純粋関数として実装されているが、統合テスト・負荷テストは今後整備推奨。

このリリースはコードベースの現状から推測して作成した CHANGELOG です。実際のコミット履歴や既存 CHANGELOG と合わせて調整してください。