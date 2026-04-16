# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、逆時系列（新しいものを上）で記載します。

注: 以下の変更点は、与えられたコードベースの内容から推測してまとめたものです（実際のコミット履歴ではありません）。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-16

初回公開リリース。システム全体の主要コンポーネント、ユーティリティ、ツール群を実装しました。

### Added（追加）
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 環境・設定管理
  - `kabusys.config.Settings` を追加。環境変数経由で各種設定を提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境判定 等）。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml に基づく）。読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサを強化:
    - `export KEY=val` 形式対応
    - シングル・ダブルクォート内のエスケープ処理対応
    - 行内コメントの扱い（クォートの有無で挙動が異なる）
  - 設定値の検証を実装（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等の有効値チェック）。必須変数未設定時は明示的な例外（ValueError）を投げる。

- 実行 / 監視スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を設定し、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の開始・停止管理を行う。
    - Paper Trading モード (`KABUSYS_ENV=paper_trading`) の場合、paper 専用 SQLite DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - 起動前に `data/stop_requested.flag` をチェックし、停止フラグが立っていれば起動を中止。
    - 実行中は停止フラグを監視し、検知時に安全にエンジン停止を行う。
    - 実行の PID を `data/execution.pid` に書き込む想定（`_EXECUTION_PID`）。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒。
    - 環境変数 `MONITOR_POLL_INTERVAL` により間隔を上書き可能。不正値はログ警告を出してデフォルトにフォールバック。
    - 監視プロセスは環境にかかわらず本番 sqlite_path を使用する設計（監視データは共通で保持）。
    - 停止フラグ `data/stop_requested.flag` 検知でループを終了。

- データベース・分析
  - DuckDB/SQLite を使用した分析・監視基盤を実装。`monitoring_db.init_monitoring_db` 呼び出しにより監視テーブルが存在することを保証（冪等）。
  - `kabusys.research`:
    - `factor_research.py` を実装: Momentum / Volatility / Value の各ファクター計算関数（DuckDB 接続を受け取り SQL で計算）。
      - calc_momentum, calc_volatility, calc_value を提供。
      - 各関数はデータ不足時に None を返す設計、スキャンレンジはバッファを持たせて安定化。
    - `feature_exploration.py` を実装: 将来リターン計算、IC（スピアマンランク相関）計算、ファクター統計サマリーなど。
      - calc_forward_returns, calc_ic, rank, factor_summary を提供。
  - `kabusys.ai.news_nlp`（ニュースNLP）
    - raw_news テーブルを OpenAI API（gpt-4o-mini）でセンチメント解析し、銘柄ごとのスコアを ai_scores へ書き込む処理を実装（API バッチ送信、最大トークン対策、スコアクリップ、リトライ方針を含む設計）。
    - ニュース収集ウィンドウを JST 基準で計算（前日 15:00 JST 〜 当日 08:30 JST を対象）。
    - 失敗に対するフェイルセーフ設計（API エラーは再試行 or スキップ、部分成功時のテーブル更新戦略など）。
    - （注）ファイルは一部で切れているため「未完成/要確認」の箇所あり。

- ポートフォリオ構築
  - `kabusys.portfolio`:
    - `portfolio_builder.py`:
      - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
      - スコア全てが 0 の際のフォールバック（等重配分）とログ警告。
    - `risk_adjustment.py`:
      - セクター上限適用（apply_sector_cap）: 既存保有比率が閾値を超えるセクターの新規候補を除外。
      - レジームに応じた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear → 1.0/0.7/0.3、未知のレジームは警告して 1.0 フォールバック。
    - `position_sizing.py`:
      - 発注株数算出（calc_position_sizes）を実装。`risk_based` / `equal` / `score` の割当方式に対応。
      - 単元株丸め（lot_size）、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウンと残差配分ロジックを備える。
      - 手数料・スリッページの見積り係数 `cost_buffer` を考慮。

- ユーティリティ
  - `kabusys.utils.process_priority`:
    - プロセス優先度（nice / Windows priority）設定ユーティリティを実装（set_process_priority）。
    - CPU affinity を限定する set_cpu_affinity を実装（psutil 利用、例外時は警告してスキップ）。
    - クロスプラットフォーム対応（Windows / POSIX 系）で差分を吸収し、呼び出し側は OS を意識しない。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成ツールを CLI として追加。指定期間の system_status / trade_logs / risk_logs を集計し、
      稼働率、注文成功率、送信率、レイテンシ（P95）等を算出して PASS/FAIL 判定を行う。
    - デフォルト DB パスは `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。
    - P95 計算、NULL / データ不足ハンドリングを実装。

### Changed（変更）
- 監視と実行の DB 利用ポリシー
  - 監視プロセスは環境に関係なく本番 sqlite_path を使用する（設計上の明示）。一方、実行エンジンは paper_trading 環境時に専用 DB を使用することで本番データと分離。

- ログ・例外取り扱い
  - 各種モジュールで入力検証と明示的な例外発生（ValueError）や警告ログ出力を追加し、運用時の早期検出性を向上。

### Fixed（修正）
- .env の読み込みでのエスケープ/クォート・コメント処理に関する複数のケースを正しく処理するよう改善（export プレフィックス、クォート内エスケープ、行内コメントの解釈など）。

### Deprecated（非推奨）
- なし

### Removed（削除）
- なし

### Security（セキュリティ）
- OpenAI API キーは環境変数（OPENAI_API_KEY）または明示的引数で解決。未設定時は ValueError を投げて誤操作を防止。

### Known issues / Notes（既知の制限・注記）
- ai/news_nlp.py はファイル末尾が切れている（提示されたコードが途中で終わっている）ため、完全な動作確認とレビューが必要。特に DB からの記事フェッチ部分や API 呼び出しのループ処理の続きが未確認。
- position_sizing の価格フォールバック: open_prices に欠損（0.0）がある場合、エクスポージャーの過小評価やブロック回避につながる点を TODO コメントで認識。将来的に前日終値等のフォールバック実装が推奨される。
- DuckDB に対する一部の実装（executemany 前の params チェック等）は DuckDB のバージョン依存の制約を考慮している。環境によっては挙動差が出る可能性があるため、本番導入前に DuckDB バージョン互換性を確認してください。
- set_process_priority / set_cpu_affinity は権限不足（非 root / 管理者）やプラットフォーム差異で失敗する可能性があり、その場合は警告ログを出して無害にスキップします。
- `MONITOR_POLL_INTERVAL` に 0 や負数を設定した場合、内部でデフォルト値にフォールバックして警告ログを出します（time.sleep に負数を渡さないための安全対策）。

---

（以上）