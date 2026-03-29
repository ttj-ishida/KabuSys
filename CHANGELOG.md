# CHANGELOG

すべての著作物は Keep a Changelog のフォーマットに従います。  
このファイルはコードベースから推測される初期リリース内容と注意点を整理したものです。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初回公開リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。主要サブパッケージとして data, research, ai, （将来的に strategy, execution, monitoring を想定）を公開するエントリポイントを設定。
  - バージョン情報: __version__ = "0.1.0"

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - 環境変数自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 必須環境変数の検証メソッドを提供（未設定時は ValueError）。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI (gpt-4o-mini) に送信しセンチメントスコアを ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事数上限、文字数トリム(_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) を導入しトークン肥大化を抑制。
    - JSON Mode を期待したレスポンスパースとバリデーション、スコアの ±1 クリップ。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実装。部分失敗でも他コードの既存スコアを保護するため DELETE → INSERT をコード絞りで行う。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする score_regime を提供。
    - ma200_ratio 計算、マクロ記事の抽出、OpenAI 呼び出し、スコア合成、閾値判定を実装。
    - API 失敗時のフェイルセーフ（macro_sentiment = 0.0）、最大リトライ、ログ出力を実装。
    - テスト容易性のため _call_openai_api の差し替えを想定。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research):
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200乖離）を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - 各関数は DuckDB 接続を受け取り SQL と Python で実行。データ不足時は None を返す設計。
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマン ランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク変換。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - zscore_normalize を含む data.stats からの再エクスポートを提供。

- Data プラットフォーム (kabusys.data)
  - カレンダー管理 (data.calendar_management)
    - JPX カレンダー用 market_calendar テーブルを扱うユーティリティ群を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録ありの場合は DB の値を優先し、未登録日は曜日ベースのフォールバック（土日非営業）で整合性を保つ設計。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）を実装（jquants_client を利用）。
  - ETL / パイプライン (data.pipeline, data.etl)
    - ETLResult データクラスを実装し、取得件数・保存件数・品質問題・エラー一覧を集約できるようにした。
    - 差分取得、backfill、品質チェック（quality モジュール呼び出し）等に対応する設計方針を明記。
    - data.etl は ETLResult を再エクスポート。

### Fixed
- 例外処理と堅牢性
  - OpenAI 呼び出しに対してリトライやフォールバック（macro_sentiment=0.0、スキップして継続）を追加し、API 部分の障害がパイプライン全体を停止させないよう設計。
  - DuckDB の executemany に関する制約（空リスト不可）を考慮して条件チェックを実装。
  - DB 書き込みは冪等性を考慮（DELETE → INSERT, トランザクション BEGIN/COMMIT/ROLLBACK）で実装。

### Security
- 秘密管理の注意
  - OpenAI API キー（OPENAI_API_KEY）、J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）、Kabu API パスワード（KABU_API_PASSWORD）などは必須・機密情報として扱う必要あり。
  - .env 自動読み込みを行うが、OS 環境変数は保護され上書きされない。テスト時や CI で自動読み込みを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

### Known limitations / Notes
- OpenAI SDK と gpt-4o-mini モデルを想定しているため、実行環境に openai SDK が必要。
- news_nlp / regime_detector は JSON Mode の厳密な出力を前提としている。LLM の出力が期待通りでない場合はパース失敗でスキップ・フォールバックする設計。
- 各モジュールは DuckDB 上の前提テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在することを期待する。未作成の場合は一部機能が動作しない。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar に依存。API レスポンスや保存処理の実装により挙動が変わる。
- calc_news_window / 各種日付ロジックは timezone-naive な UTC で DB と比較する実装（JST ⇄ UTC の変換を内部で扱っている点に注意）。

### Migration / Configuration
- 必要な環境変数（抜粋）:
  - OPENAI_API_KEY (AI 機能利用時)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH, SQLITE_PATH （デフォルトがあるため未設定時は data 以下に配置される）
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- .env の自動読み込みはプロジェクトルート（.git or pyproject.toml）を基準に行われます。パッケージ配布後も正しく動作するように設計されていますが、意図しない環境変数の読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Contributors
- 初回実装: コードベースから推測してパッケージ設計者

---

注: 本 CHANGELOG は与えられたソースコードから推測して作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴・プロジェクト管理ドキュメントに基づいて更新してください。