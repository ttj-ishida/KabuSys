# Changelog

すべての重要な変更点はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従います。

注意: 以下はコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。システム全体の基盤機能（設定管理、データ ETL、マーケットカレンダー、研究用ファクター計算、AI ベースのニュースセンチメント評価など）を実装。

### Added
- パッケージ初期化
  - kabusys パッケージを導入。公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。
  - バージョン情報: `__version__ = "0.1.0"`。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、アプリケーションが必要とする設定値をプロパティ経由で取得可能に:
    - J-Quants / kabuAPI / Slack / データベースパス（DuckDB/SQLite） / 環境（development/paper_trading/live） / ログレベル検証 等。
  - 必須環境変数未設定時は明確な例外（ValueError）を出す `_require` 実装。

- AI モジュール（ニュース NLP / 市場レジーム判定）
  - `kabusys.ai.news_nlp`
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを生成。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、バッチ（最大 20 銘柄/チャンク）でセンチメントを取得。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx）とエクスポネンシャルバックオフを実装。
    - レスポンス検証（JSON 抽出、results 配列・code/score 検証、数値変換、±1.0 クリップ）。
    - ai_scores テーブルへの冪等的書き換え（該当 date/code を DELETE → INSERT）を実装。
    - `score_news(conn, target_date, api_key=None)`：スコア算出・書き込みの公開 API。
    - `calc_news_window(target_date)`：ニュース集計ウィンドウ（JST 基準）計算ユーティリティを実装。
  - `kabusys.ai.regime_detector`
    - ETF 1321 (日経225 連動) の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を組み合わせて市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを用いてルックアヘッドを防止。
    - OpenAI 呼び出し用クライアントを内部で生成、リトライとフォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK 処理）。
    - `score_regime(conn, target_date, api_key=None)`：公開 API。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`
    - モメンタムファクター（1M/3M/6M リターン、200日 MA 乖離）を計算する `calc_momentum` を実装。
    - ボラティリティ / 流動性（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）を計算する `calc_volatility` を実装。
    - バリューファクター（PER、ROE）を計算する `calc_value` を実装（raw_financials から最新レコード取得）。
    - いずれも DuckDB に対する SQL ベースで実装し、外部 API 呼び出しは行わない設計。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、ホライズン検証あり）。
    - IC（Information Coefficient、Spearman ρ）計算 `calc_ic`、およびランク変換ユーティリティ `rank`。
    - ファクター統計要約 `factor_summary`（count/mean/std/min/max/median）。
  - `kabusys.research.__init__` に主要ユーティリティをエクスポート（zscore_normalize を含む）。

- データプラットフォーム / ETL
  - `kabusys.data.calendar_management`
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 営業日判定ユーティリティ群を実装: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。DB 登録値優先で未登録日は曜日ベースでフォールバック。
    - 最大探索日数やバックフィル期間などの安全策を導入。
  - `kabusys.data.pipeline`
    - ETL 実行結果を表すデータクラス `ETLResult` を実装（取得件数、保存件数、品質問題、エラー等を保持）。
    - 差分取得、バックフィル、品質チェック（`kabusys.data.quality` と連携）を想定した設計（実装の補助関数を含む）。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- その他
  - DuckDB を主要なデータ格納・照会エンジンとして使用するための SQL 実装パターンを採用。
  - OpenAI SDK 呼び出しはテスト時に差し替え可能な形（内部 _call_openai_api 関数）で実装。

### Changed
- 初期リリースのため該当なし（今後のリリースで差分を記載）。

### Fixed
- 初期リリースのため該当なし（バグ修正は次版で記載）。

### Removed
- 初期リリースのため該当なし。

### Security
- OpenAI API キーや各種トークンは Settings を通じて環境変数から取得し、コードベースにハードコーディングしない設計。
- .env 読み込みで OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Design decisions
- ルックアヘッドバイアス回避のため、すべての「日付に基づく」処理は内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- Research モジュールは外部 API を呼ばず、DuckDB のクエリと純粋な Python ロジックのみで完結する方針。
- AI 関連処理は堅牢性を重視し、API 失敗時は例外を投げるのではなくフェイルセーフ（0.0 やスキップ）で継続する実装が多い。
- DuckDB の executemany の制約（空リスト不可）に対する回避処理を導入。

### Known issues / TODO
- 一部の機能（例: Strategy / Execution / Monitoring パッケージ中の実装）はこのリリースで公開 API の骨格のみか、まだ実装が必要な箇所がある可能性がある（コードベース全体の統合テストを推奨）。
- 外部依存（OpenAI、J-Quants クライアント）の実稼働環境での検証とエラーハンドリングの追加チューニングが今後必要。
- duckdb テーブルスキーマや jquants_client、quality モジュールの具体的実装との整合性確認（マイグレーション・初期テーブル作成スクリプトの整備）。

---

（この CHANGELOG はコードから推測して作成しています。実際のリリースノートとして使用する際は、実際の変更履歴・リリース日・責任者情報などを追記してください。）