# Changelog

すべての変更は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本ファイルはコードベース（src/ 以下）の実装内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-13
初期リリース（推定）。以下の主要コンポーネントを追加しました。

### Added
- 全体
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
  - DuckDB / SQLite を用いた分析・監視・実行の基盤実装を追加。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを実装。
    - 環境変数 `KABUSYS_ENV=paper_trading` 時に paper_trading 用の SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離する挙動をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行するフローを実装。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効としてデフォルトへフォールバック）。
    - 監視（monitoring）は環境にかかわらず本番用の sqlite_path を使用する旨を明記。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動ロードする機能を追加。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用）。
    - `.env` パーサーを実装（`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート）。
    - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別（development/paper_trading/live）など多数のプロパティを提供。
    - `PAPER_FILL_MODE` のバリデーション、`PAPER_TRADING_SQLITE_PATH`、`KILL_FLAG_CLEAR_ON_START` 等の各種設定をサポート。
    - OS 環境変数の保護（protected）を考慮した .env 上書きロジックを実装。

- 監視 / ツール
  - monitoring 用 DB 初期化ユーティリティ呼び出し（init_monitoring_db を run_* から実行）。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率(send rate)、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL を判定するロジックを実装。
    - 日付フィルタ、DB パス指定（引数 `--db` / 環境変数）をサポート。
    - デフォルト閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）を定義。

- ポートフォリオ構築
  - kabusys.portfolio パッケージを追加（純粋関数群）。
  - portfolio_builder.py
    - `select_candidates`（スコア降順・タイブレークルール）、`calc_equal_weights`、`calc_score_weights` を実装。スコア全て 0.0 の場合は等金額割当へフォールバック。
  - risk_adjustment.py
    - `apply_sector_cap`：セクター集中上限チェック（既存保有を考慮して当日売却予定銘柄を除外する挙動を含む）。"unknown" セクターは除外対象外。
    - `calc_regime_multiplier`：市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知のレジームは 1.0 でフォールバック）。
  - position_sizing.py
    - `calc_position_sizes`：allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。損切り率・リスク率・lot 単位で丸め、1 銘柄上限・aggregate cap を適用。合計が利用可能現金を超える場合のスケーリングと fractional remainder に基づく再分配ロジックを実装。
  - モジュール __init__ で上記関数を公開。

- ユーティリティ
  - utils/process_priority.py
    - `set_process_priority(level)` を実装し、Windows（psutil の priority constants）と POSIX（nice 値）を吸収する。未対応 OS は警告でスキップ。
    - アクセス権限不足や未実装 API を考慮して安全に失敗をログ出力してスキップ。
    - `set_cpu_affinity(cpu_count)` を実装。利用可能コア数より大きい指定や権限不足を考慮して挙動を定義。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してファクター（momentum, volatility, value）を計算する関数を実装。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）、calc_value（PER/ROE）を SQL ベースで実装。データ不足時の None ハンドリングあり。
  - research/feature_exploration.py
    - 将来リターン（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py で主要 API を公開（zscore_normalize を data.stats から再エクスポート）。

- AI / ニュースセンチメント
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI API（デフォルト model: gpt-4o-mini）で銘柄ごとのセンチメントを計算し、ai_scores テーブルへ書き込む処理を実装。
    - ニュース収集ウィンドウ（JST ベース、UTC へ変換）関数 `calc_news_window` を実装。
    - バッチサイズ（デフォルト 20）での API 呼び出し、トークン肥大対策（1銘柄あたり最大記事数 / 文字数制限）、429/タイムアウト/5xx に対する指数バックオフでのリトライ、レスポンス検証、スコアを ±1.0 にクリップして保存するフローを実装。
    - API キー未設定時に例外を投げる。書き込みは部分失敗時の保護を考慮して対象 code の置換（DELETE→INSERT）を行う設計。

### Changed
- 自動読み込みの既定挙動として .env/.env.local の読み込みを行い、OS 環境変数を優先・保護する挙動を採用（config.py）。テスト等のために自動ロードは環境変数で無効化可能。

### Fixed
- 初期リリースにつき、実装上の詳細なバグ修正履歴はなし（コード実装が最初期のものとして追加）。

### Security
- 環境変数ファイル読み込み時に読み込み失敗を warnings.warn で扱う（致命的に停止させない実装）。
- OpenAI API キーは明示的に引数または環境変数から取得し、未設定時は ValueError を発生させることで誤操作を明確化。

---

注意:
- 上記はソースコードの実装内容から推測してまとめた変更履歴です。実際のリリースノート作成時はコミット履歴・リリース日・影響範囲を合わせて確認してください。