# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは Keep a Changelog 準拠の形式で作成しています。

現在日付: 2026-04-16

## [Unreleased]
### Added
- リリース準備中の注記を追加（本CHANGELOGはコードベースから推測して作成）。
- 一部モジュールに対するドキュメント内の TODO / 注意点を明示。

### Known issues
- `kabusys.ai.news_nlp` モジュールのソースが途中で切れている（スニペットが不完全）。OpenAI 呼び出し・記事集約後の処理が途中で終わっている箇所があるため、実行前に完全実装を確認してください。

---

## [0.1.0] - 2026-04-16
初回公開とみなされる主要機能群を追加。

### Added
- 基本情報
  - パッケージ定義: `kabusys.__version__` を "0.1.0" に設定。

- 設定管理
  - `kabusys.config`:
    - .env 自動読み込み機構（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env/.env.local の読み込み順序と上書きルール（OS 環境変数の保護機構を実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - 高度な .env パーサ実装: `export` プレフィックス対応、クォート文字列内のバックスラッシュエスケープ、インラインコメントの扱い等。
    - 環境変数必須チェック用ユーティリティ `_require`。
    - `Settings` クラスを提供し、各種設定（J-Quants, kabu API, LINE, DB パス, paper trading 関連, 監視閾値, 環境種別・ログレベル判定など）をプロパティ経由で取得可能に。
    - `PAPER_FILL_MODE` のバリデーション（有効値: "instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` の有効値チェック（development / paper_trading / live）。

- 実行・監視スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。
    - paper_trading 環境時は専用の paper DB を使用（`PAPER_TRADING_SQLITE_PATH` 経由、または Settings の `paper_sqlite_path`）。
    - ブローカークライアントの抽象化（`BrokerClientFactory` を利用）。
    - 注文管理／リスク管理／照合（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立てて `ExecutionEngine` をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知によるグレースフルシャットダウン処理、実行時 PID ファイル管理（data/execution.pid）。
    - `RiskManager` 初期設定のデフォルト値（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）。初期資金はブローカーから取得。

  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、負の値等はフォールバックして警告）。
    - 監視は環境に関係なく本番の sqlite_path を参照する設計（意図的に本番 DB を使用する仕様）。
    - 停止フラグ検知によるループ終了、例外発生時のロギングと継続。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`:
    - クロスプラットフォームでのプロセス優先度設定 `set_process_priority(level)`（Windows の優先度クラスと POSIX の nice 値を吸収）。
    - CPU affinity 設定 `set_cpu_affinity(cpu_count)`（利用可能コア数を超えた指定や権限不足に対する安全なハンドリング）。
    - 権限不足・未対応 OS での警告出力によりフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（score 降順、同点は signal_rank の昇順でタイブレーク）。
    - 配分計算 `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合に等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター露出を計算し上限超過セクターの新規候補を除外。unknown セクターは制限対象外）。
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear にマッピング、未知レジームは警告を出して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数算出 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）で丸め、ポジション上限 per-stock / aggregate cap の適用、cost_buffer を用いた保守的コスト見積り、スケールダウン時の残差配分ロジックを実装。
    - 設計上の注意点（将来的な銘柄別 lot_size の導入や価格フォールバックの TODO コメントあり）。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB 経由で計算する関数を実装。
    - データ不足時の None 扱い、DuckDB SQL によるウィンドウ集計を利用。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン対応、入力検証あり）。
    - IC（Spearman の ρ）計算 `calc_ic`、ランク関数 `rank`、統計サマリー `factor_summary` を実装。
  - `kabusys.research.__init__` で主要関数をエクスポート。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp`:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコア（-1.0〜1.0）を生成する仕組みを実装。
    - バッチサイズ、最大リトライ、指数バックオフ、レスポンスの検証、スコアのクリップ（±1.0）、部分失敗時の DB 書き込み保護（対象コードのみ置換）など、実運用を想定した堅牢化設計。
    - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）のユーティリティ `calc_news_window` を提供。
    - 注意: スニペット中に処理途中で切れている箇所が存在するため、実行前に完全実装を確認する必要あり。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 算出、日付フィルタ（--from/--to）、DB パスオーバーライド（--db / 環境変数）対応。
    - 合格基準（しきい値）を定義し PASS/FAIL 判定を出力。

### Changed
- DuckDB をデータ解析系（research, ai）で積極利用する設計に統一。
- DB 初期化（監視用テーブル）を冪等に保証するユーティリティ `init_monitoring_db` を利用するように run scripts を統一。

### Fixed / Hardened
- 環境変数読み込み:
  - 無効な `MONITOR_POLL_INTERVAL` 値に対して警告を出しデフォルトへフォールバック（`run_monitoring`）。
  - .env の複雑なクォート・エスケープ・コメント処理に対応し、誤解釈を防止。
- プロセス優先度設定:
  - 未対応 OS や権限不足時に例外を投げず警告でスキップするよう改善（`set_process_priority`, `set_cpu_affinity`）。
- ポジション算出:
  - 投下資金が available_cash を越えた場合のスケーリング、端数の公正な再配分ロジックを実装。lot_size による丸めを厳密に適用。

### Security / Validation
- OpenAI API キー未設定時に明確な ValueError を発生させる（`ai.news_nlp.score_news`）。
- `Settings._require` による必須環境変数チェックで早期に誤設定を検出。

### Documentation / Comments
- 各モジュールに詳細な docstring と設計意図・注意点を追加（PortfolioConstruction.md / StrategyModel.md への参照を含む）。
- データ不足や異常ケースへの挙動（None 戻り、ログ出力）を明確化。

### TODO / Notes
- `kabusys.ai.news_nlp` のファイルスニペットは途中で切れているため、記事集約後の API 呼び出しループ以降の実装を要確認・補完。
- `position_sizing` の価格欠損（price == 0.0）に対するフォールバック（前日終値や取得原価の使用）や、銘柄別 lot_size サポートは将来的な拡張として TODO コメントあり。
- DuckDB の `executemany` に関する取り扱い（0.10 の制約）に注意している旨のコメントあり。

---

過去リリースが存在する場合は上の [0.1.0] を適宜移動し、Unreleased に最新の変更を記録してください。必要であれば、各変更点をより細かいコミット単位・モジュール単位で分割して記載することも可能です。どの程度の粒度で詳細化するか指定いただければ、より詳細な CHANGELOG を作成します。