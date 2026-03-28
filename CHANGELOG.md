# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（src/kabusys）から推測して作成したリリース履歴です。

## [Unreleased]
- なし（初回リリース準備）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。バージョンは 0.1.0。
  - 公開モジュール: data, research, ai, execution, strategy, monitoring（__all__ に一部記載）。
- 設定管理
  - 環境変数/.env ロードユーティリティ（kabusys.config）。
    - プロジェクトルート決定ロジック（.git または pyproject.toml を探索）。
    - .env と .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
    - .env 行パーサは export 形式、クォート、エスケープ、インラインコメント対応。
  - Settings クラスで主要な設定値をプロパティ経由で提供。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABUSYS_ENV=development、KABU_API_BASE_URL=http://localhost:18080/kabusapi、DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db
    - env / log_level 値検証（許容値のチェック）および is_live / is_paper / is_dev 補助プロパティ。
- データプラットフォーム（data）
  - ETL 基盤（kabusys.data.pipeline）
    - 差分フェッチ、保存（idempotent）、品質チェックを考慮した ETLResult データクラスの実装。
    - DuckDB を想定したユーティリティ（テーブル存在チェック、最大日付取得）。
    - バックフィル・カレンダー先読みなど ETL 実行ロジックの設計に準拠した定数設定。
  - calendar_management モジュール
    - JPX カレンダー管理、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルの有無による DB 優先ロジックと曜日ベースのフォールバック実装。
    - calendar_update_job による J-Quants からの差分取得/保存フロー（バックフィル、健全性チェック）。
  - ETL の公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
- リサーチ（research）
  - factor_research: ファクター計算機能を実装
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials と prices_daily を組み合わせ）
    - DuckDB を用いた SQL ベースの実装。外部ネットワーク呼び出しなし。
  - feature_exploration: 研究用解析ユーティリティ
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（コード結合・欠損除外）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返すランク化ユーティリティ
  - research パッケージから主要関数を再エクスポート（使いやすさ向上）。
- AI / NLP（ai）
  - news_nlp: ニュース記事のセンチメントスコアリング（score_news）
    - 前日15:00 JST ～ 当日08:30 JST のタイムウィンドウで raw_news / news_symbols を集約。
    - 銘柄ごとに最大記事数・最大文字数でトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - JSON mode を前提としたレスポンス検証・復元ロジック（余分なテキストが混入する場合の {} 抽出対応）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理。
    - スコアは ±1.0 でクリップして ai_scores テーブルへ冪等的に（DELETE→INSERT）保存。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector: 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み70%）と news_nlp のマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、OpenAI によるマクロセンチメント評価（gpt-4o-mini、JSON mode）。
    - API エラー時は macro_sentiment=0.0 とするフェイルセーフ、リトライ/バックオフ実装。
    - DuckDB に対する冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
- 仕様・設計上の配慮（全体）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照しない設計（target_date を外から与える）。
  - DuckDB をデータレイヤに利用（SQL と Python の組み合わせで各種処理を実装）。
  - DB 書き込みはトランザクションで冪等性を確保（DELETE→INSERT 等）。
  - OpenAI 呼び出しは JSON Mode を想定、厳密な JSON 出力を期待するプロンプト設計。
  - ロギング・警告の充実（API エラー・データ不足・ROLLBACK 失敗などで警告/例外処理）。
  - テストを考慮した設計（API 呼び出しの差し替えポイントを用意）。

### 変更 (Changed)
- 初回リリースのため変更履歴なし（このバージョンでの初実装内容を記載）。

### 修正 (Fixed)
- 初回リリースのため修正履歴なし（実装段階でのフェイルセーフ・ログを含む）。

### 注意事項 (Notes)
- OpenAI API の利用
  - AI 機能（score_news, score_regime）を利用するには OPENAI_API_KEY の設定が必要（api_key 引数でも指定可）。
  - API の失敗時は基本的に例外を投げずフェイルセーフでスコアを 0 とする設計だが、キー未設定時は ValueError を送出する。
- 環境変数
  - 主要な必須環境変数は Settings クラスのプロパティで取得される。README / .env.example に基づき設定すること。
- データベース
  - デフォルトの DuckDB パス: data/kabusys.duckdb。必要に応じて DUCKDB_PATH 環境変数で変更可能。
- 互換性
  - DuckDB のバージョン差異（executemany の空リスト制約など）を考慮して実装しているため、DuckDB の特定バージョンに依存する箇所がある点に注意。

---

今後の予定（想定）
- モデル/プロンプトのチューニング、AI スコアの追加メトリクス、実取引連携（execution モジュール）や監視（monitoring）の実装拡充。