# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」標準に準拠しています。変更はリリースごとに分類しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 廃止 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [Unreleased]

- 一部モジュールに未完成の実装や TODO コメントが残っています（例: research/factor_research の実装途中）。
- 将来的な改善候補や拡張点をいくつか残しています（lot_size の銘柄別対応、価格フォールバックなど）。

---

## [0.1.0] - 2026-04-23

初回リリース。自動売買システム KabuSys の基礎機能を実装しています。主要な追加点を以下に示します。

### Added
- コアパッケージとバージョン情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行/監視用エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および pid ファイルを扱う仕組み。
    - BrokerClientFactory を使用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - スレッドで実行し、停止フラグで安全に停止可能。
    - RiskManager のデフォルト設定が含まれる（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。

  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の明記。
    - 停止フラグによりループを安全に終了し、例外時はログ出力して次回ポーリングまで継続。

- 設定管理・自動読み込み
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）。
    - 複雑な .env パーサを実装（export 形式、クォート内のエスケープ、インラインコメント処理など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機構。
    - Settings クラスで各種設定プロパティ（DB パス、API トークン、環境判定、paper_trading 用オプション等）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - env/log_level のバリデーション。

- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新するツール。
    - 秘匿項目はマスク表示、既存 .env 読み込み／Enter による既存値再利用、確認プロンプトを実装。
    - .env のテンプレート書き出し機能を提供。

  - validate_config.py
    - 起動前の環境検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML 利用時は）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Flag の自動クリア設定の警告）。
    - --strict オプションで警告を FAIL 扱いできる。

- ロギング・プロセス運用ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（daily ローテーション、30 日保持）を設定。
    - ログディレクトリ作成失敗時にはファイル出力をスキップして stdout のみで動作する耐障害性。
    - LOG_LEVEL / LOG_DIR の解決順を実装。

  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows / POSIX に対応）。
    - CPU affinity 設定補助（最初の N コアに固定）。
    - 権限不足や未対応環境での安全なフォールバック（警告ログ出力）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位選出（スコア降順、signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分（スコア合計 0 の場合は等金額へフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用（既存保有のセクター別時価算出を行い、上限超えセクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 等配分/スコア配分/リスクベース配分に基づく発注株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer の考慮。
    - スケールダウン時の端数処理（残余キャッシュで fractional 残差の大きい順に lot 単位で追加配分）。
    - 各所で不十分な価格データに対するログ出力やスキップ挙動を実装。

- データ検証 / ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数。
    - デフォルト閾値を定義して PASS/FAIL 判定を行う（稼働率 >= 99%、fill >= 90% 等）。
    - 日付フィルタ（--from / --to）に対応。DB 存在チェック・エラーハンドリングあり。
    - p95 計算ユーティリティを実装。

- Research
  - research/factor_research.py
    - ファクター計算モジュールの骨格を実装（モメンタム/MA/ATR/出来高系などを想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。
    - 実装途中の箇所あり（ファイル末尾で切れているため続きが必要）。

- monitoring DB 初期化ヘルパー参照（init_monitoring_db を起動スクリプトで呼び出し）
  - 監視テーブルの冪等初期化を保証する呼び出しを各実行スクリプトで実施。

### Changed
- N/A（初回リリースのため履歴上の変更はなし）

### Fixed
- N/A（初回リリース）

### Notes / Implementation details
- 多くの箇所で堅牢性を重視したフォールバック実装がされている（不正な環境変数は警告・デフォルト利用、ファイル作成失敗時の退避、権限不足時の警告など）。
- Paper Trading と Live の DB を明確に分離（settings.paper_sqlite_path と settings.sqlite_path）。
- ログは stdout を基準にしており、cron 等からのリダイレクト運用を考慮している（stderr ではなく stdout を使用）。
- .env のパースは export 形式、クォート内のエスケープ、インラインコメントなど一般的なケースに対応している。

---

以上が、コードベースから推測した CHANGELOG.md 内容です。必要であれば各項目をさらに細分化したり、未実装箇所（factor_research の続き、将来的な拡張点）を Issue/TODO リストとして変換することもできます。どの形式で出力するか（Markdown ファイルへ保存など）を指定してください。