CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- Unreleased: 今後のリリースに向けた未リリースの修正・改善
- 各リリースは日付付きで記載

Unreleased
----------
### Added
- run_monitoring エントリーポイントを追加
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクト直下の `data/stop_requested.flag` を検知して行う。
  - 監視プロセスは KABUSYS_ENV にかかわらず本番用の `sqlite_path` を利用する仕様になっている。
- run_execution エントリーポイントを追加
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と完全分離。
  - ブローカークライアント生成を `BrokerClientFactory` に委譲。
  - `ExecutionEngine` をスレッドで起動し、停止フラグ検知で Graceful stop を行う。
- Settings / 環境変数管理の強化
  - プロジェクトルート（.git もしくは pyproject.toml）を自動検出して `.env` / `.env.local` を自動ロード。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` パーサを改善（`export KEY=...`、クォート内のバックスラッシュ解釈、コメントの扱いなどをサポート）。
  - 必須環境変数取得関数 `_require()` を提供し、未設定時に明確なエラーを送出。
  - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の入力検証を追加。
- ポートフォリオ構築モジュール（kabusys.portfolio）を追加
  - 候補選定: `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は equal にフォールバック）
  - リスク調整: `apply_sector_cap`（セクター集中上限の適用）、`calc_regime_multiplier`（market regime に応じた乗数）
  - ポジションサイズ決定: `calc_position_sizes`
    - `risk_based` / `equal` / `score` の割当方式をサポート
    - 単元株（lot）丸め、1 銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）を実装
    - コストバッファ（手数料・スリッページ想定）を考慮した保守的見積りと残差処理の分配ロジックを実装
- 研究用モジュール（kabusys.research）を追加
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`（DuckDB の prices_daily / raw_financials を使用）
  - 特徴量探索: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
  - 外部ライブラリ非依存で DuckDB を使った SQL + Python 実装
- AI ニュース NLP モジュール（kabusys.ai.news_nlp）を追加（部分実装）
  - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメントスコアリング設計を実装
  - バッチ（最大 20 銘柄）送信、JSON レスポンス検証、スコアクリッピング ±1.0、リトライ（429/5xx/タイムアウト）を想定
  - 対象ニュースの時間ウィンドウ計算 (`calc_news_window`) を実装（JST ベース → UTC 変換）
- ツール: `paper_verification_report` を追加
  - Paper Trading の検証レポートを生成する CLI（期間指定オプション、DB のパス指定オプションをサポート）
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標と閾値を定義（デフォルト閾値を内蔵）
- Utilities
  - `utils.process_priority` を追加
    - Windows / POSIX を吸収して `set_process_priority(level)` を提供（"high" / "normal" / "low"）
    - `set_cpu_affinity(cpu_count)` を追加し、最初の N コアにピン留め可能（権限等で失敗した場合は警告でフォールバック）
  - DuckDB/SQLite 接続の初期化ユーティリティ（監視用テーブル確保）を呼び出す仕組みを各起動スクリプトに導入

### Changed
- 監視モジュールの挙動調整
  - `run_monitoring` は例外をキャッチしてログ出力し、次のポーリングまで待機するフェイルセーフ実装を採用。
  - `MONITOR_POLL_INTERVAL` の不正値（0 以下や非整数）を検出した場合にデフォルトへフォールバックし警告ログを出す。
- Execution の動作
  - エンジンはデーモンスレッドで実行され、メインスレッドは停止フラグ監視とジョインタイムアウトで安定的に終了するよう変更。
  - 監視テーブル初期化 (`init_monitoring_db`) を起動時に冪等に呼び出して存在保証。

### Fixed
- 環境変数ロード時の上書きロジックを改善
  - `.env.local` は `.env` より優先して上書きする一方、既存 OS 環境変数は保護する挙動を明確化。
- 一部の計算でのデータ不足・ゼロ割りの扱いを明確化・保護
  - factor / momentum / volatility / value 等の関数は必要な行数が不足した場合に None を返すようにして安全に動作するようになった。
  - `calc_score_weights` は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。

0.1.0 - 2026-04-16
-------------------
初回公開リリース。主な内容は以下。

### Added
- 基本アプリケーション構成
  - パッケージメタ: `kabusys.__version__ = "0.1.0"`
  - モジュール群を収録: data / strategy / execution / monitoring 相当のコア機能群
- 実行スクリプト
  - `run_monitoring`（システム監視ポーリングループ）
  - `run_execution`（ExecutionEngine 起動・管理）
- 設定管理
  - `kabusys.config.Settings` による環境変数ベースの設定取得
  - デフォルト値・検証ロジック・`.env` 自動ロードを実装
- Execution サブシステム
  - ブローカー抽象化（BrokerClientFactory）
  - `OrderRepository`, `OrderManager`, `RiskManager`, `Reconciler`, `ExecutionEngine` の組み立てと起動フロー
  - デフォルトリスク設定（max_position_pct, max_utilization, rate_limit など）を提供
- 監視サブシステム
  - 監視用 DB 初期化ユーティリティ（`init_monitoring_db`）を導入
  - 監視ループの停止フラグ・PID 管理を実装
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数
  - 単元株丸め・aggregate cap・スケールダウンロジックを含む堅牢なサイズ計算
- 研究機能（DuckDB ベース）
  - モメンタム・ボラティリティ・バリューのファクター計算
  - 将来リターン計算、IC（Spearman ランク相関）、統計サマリ等
- AI / ニュース分析（設計と一部実装）
  - OpenAI を用いた銘柄別ニューススコアリング設計（バッチ、リトライ、JSON 検証、スコアクリップ）
  - ニュースの時間ウィンドウ算出ユーティリティ
- ツール
  - `paper_verification_report`（Paper Trading 検証用 CLI）を追加
- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ（psutil ベース）

### Changed
- 起動フローの安定化
  - プロセス優先度設定を起動直後に実行してリソース優先度を確保。
  - DB 接続は起動時に確立し、終了時に確実にクローズする。
- Paper Trading の分離
  - paper_trading 環境は専用 SQLite を使用し、本番 DB と完全に分離。

### Fixed
- 各モジュールで例外やデータ不足が発生した場合にフェイルセーフで継続するよう改善（監視ループ、レポート生成、AI スコア処理設計等）。

Notes / 補足
----------------
- 本 CHANGELOG はコードベースの実装から推測して作成しています。実際のコミット履歴や issue トラッキングに基づくものではありません。
- ai.news_nlp モジュールは設計と主要なユーティリティ（ウィンドウ計算、API 呼び出し設計など）が実装されていますが、ファイル末尾で切れているため一部未完成の箇所が存在する可能性があります。運用時は OpenAI API キーの取り扱い（環境変数 `OPENAI_API_KEY`）やレート制御に注意してください。