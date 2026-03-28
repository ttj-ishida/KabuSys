Keep a Changelog
=================

すべての注意すべき変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

注: リリース日や説明はソースコードから推測して作成しています。

[Unreleased]

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートの探索は __file__ を基準に .git または pyproject.toml により決定（CWDに依存しない）。
  - .env パーサ (_parse_env_line) は次をサポート:
    - 空行・コメント行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート、エスケープシーケンスの解釈
    - インラインコメントの取り扱い（クォートの有無に応じた挙動）
  - .env 読み込み時の上書き制御（override）と保護キー (protected) のサポート。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得するプロパティ。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG..CRITICAL）の検証。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - is_live / is_paper / is_dev 判定ユーティリティ。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュース・NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント(ai_score)を算出。
    - 対象時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 換算で前日 06:00 ～ 23:30）。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄（_BATCH_SIZE）を処理。
    - 1銘柄あたりの最大記事数・文字数制限でトークン肥大化を防止（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。その他エラーはスキップして継続。
    - OpenAI レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは冪等処理（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - テストフック: _call_openai_api を patch して置換可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードでニュースを抽出し OpenAI（gpt-4o-mini）で macro_sentiment を取得。
    - 失敗フェイルセーフ: LLM 呼び出し失敗時は macro_sentiment=0.0 として継続。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。
    - 最大リトライ等のパラメータと内部設計（ルックアヘッドバイアス回避のための date 未満クエリ等）が明示。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーの扱い（market_calendar テーブル）と夜間バッチ更新のための calendar_update_job を提供。
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 非存在時は曜日ベースのフォールバック（土日を休場扱い）。
    - 最大探索範囲など安全策の導入（_MAX_SEARCH_DAYS など）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラス（target_date、取得/保存件数、品質問題、エラー一覧等）を実装。
    - 差分更新・バックフィル・品質チェックを念頭に置いた設計。
    - jquants_client および quality モジュールとの連携想定（fetch/save、品質検査の集約）。
  - etl モジュールは ETLResult を再エクスポート (kabusys.data.etl)。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 約1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - Volatility/Liquidity: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
    - Value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から取得）
    - DuckDB 上で SQL を利用して計算。外部 API にはアクセスしない設計。
    - 関数: calc_momentum, calc_volatility, calc_value
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns（デフォルト horizons=[1,5,21]）
    - IC 計算（Spearman の ρ）: calc_ic（rank を内部実装）
    - 統計サマリー: factor_summary
    - ランク変換ユーティリティ: rank
  - 研究用モジュールは data.stats の zscore_normalize を再利用して公開（kabusys.research.__init__ のエクスポートあり）。

- 基盤
  - DuckDB を前提としたデータアクセス（関数群は DuckDB 接続を受け取る）。
  - OpenAI Python SDK（OpenAI クライアント）を利用して LLM 呼び出しを行う実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種トークンは環境変数で管理する設計。Settings は必須環境変数未設定時に ValueError を送出して明示的に失敗させる。

Notes / 実装上の重要メモ
- LLM 関連:
  - モデル: gpt-4o-mini を想定（code 中の定数参照）。
  - レスポンスは JSON Mode を利用し厳密な JSON を期待するが、JSON パース失敗時の復元処理（最外の {} を抽出）を行う。
  - テスト容易性のため、内部の _call_openai_api はテスト時に patch して差し替え可能。
- ルックアヘッドバイアス対策:
  - news_nlp / regime_detector 等は datetime.today() を参照せず、呼び出し元から target_date を明示的に渡すことで将来情報の参照を防止。
- フェイルセーフ:
  - LLM API の失敗時は例外をそのまま投げず、ロギングのうえ 0 相当の中立スコアで継続する設計箇所がある（ニュース/レジーム評価など）。
- DB 書き込み:
  - ai_scores / market_regime 等への書き込みは部分失敗により既存データを消さないよう配慮（DELETE 対象を絞る、begin/commit/rollback 管理）。

必要な環境変数（主なもの）
- OPENAI_API_KEY : OpenAI 呼び出しに必須（ai.score_news / ai.score_regime 等）。
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（Settings.jquants_refresh_token）。
- KABU_API_PASSWORD, KABU_API_BASE_URL : kabu ステーション API 関連。
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知関連（設定プロパティとして必須扱い）。
- DUCKDB_PATH, SQLITE_PATH : デフォルト DB パスの上書きに使用可能。

互換性 / マイグレーション
- 初回リリースのため互換性注記はありません。

既知の制約 / 今後の改善候補
- OpenAI レスポンスの厳密性に依存するため、LLM の挙動変化に対する保護ロジック（さらなる検証・フォールバック）の強化が検討事項。
- DuckDB executemany に空リストが使えない点へのワークアラウンドが実装されている（空パラメータ回避）。
- ローカル開発時の .env 自動ロードは便利だが、CI/CD やテストでの明示的制御（KABUSYS_DISABLE_AUTO_ENV_LOAD）の周知が必要。

---

以上。ソースコードの内容から可能な限り詳細に機能と設計意図をまとめました。必要であればリリースノートの英語版・短縮版や、セクションの追記（API 例、環境変数サンプル等）を作成します。