# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]

### Added
- なし（初期リリース後の変更はここに記載します）

### Changed
- なし

### Fixed
- なし

### Security
- なし

---

## [0.1.0] - 2026-03-27

初期リリース。日本株自動売買システムのコアライブラリを提供します。主な機能、設計方針、既知の注意点を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージを公開（__version__ = 0.1.0）。
  - パブリック API エクスポート: data, strategy, execution, monitoring（将来的な拡張を想定）。

- 設定・環境変数管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート自動検出して読み込むロジックを追加。
    - 自動ロード優先度: OS 環境変数 > .env.local > .env。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env パーサ実装
    - export KEY=val 形式、クォート内のエスケープ、インラインコメント処理、無効行スキップなどに対応。
  - Settings クラス
    - J-Quants、kabuステーション、Slack、データベースパス、環境名・ログレベル等のプロパティを提供。
    - 必須環境変数チェック（未設定時は ValueError）。
    - デフォルトパス: DUCKDB_PATH = data/kabusys.duckdb、SQLITE_PATH = data/monitoring.db
    - 有効な環境値とログレベルを制約（開発/paper_trading/live 等）。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) を用いてセンチメントスコアを生成。
    - バッチ処理 (最大 20 銘柄/回)、1 銘柄あたりの記事数・文字数のトリム、JSON Mode の結果検証を実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、失敗時はスキップして継続するフェイルセーフ。
    - レスポンス検証: JSON パース、"results" リスト、既知コードフィルタ、数値変換、±1.0 クリップ。
    - スコアは ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時の既存データ保護）。
    - calc_news_window: JST ベースのニュース集計ウィンドウを UTC naive datetime で返す（ルックアヘッド防止）。
    - テスト容易性のため内部の OpenAI 呼出しを patch 可能に設計。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を算出・保存。
    - マクロニュース抽出はマクロキーワードリストに基づくタイトル検索。
    - OpenAI 呼出しは gpt-4o-mini を用い、JSON 出力で macro_sentiment を取得。
    - 再試行、5xx 判定、JSON パース失敗時には macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時は ROLLBACK を試み例外を上位へ伝播。

- データ関連 (kabusys.data)
  - ETL パイプラインインターフェース (pipeline.ETLResult)
    - ETL 実行結果を表す dataclass を公開。取得数・保存数・品質問題・エラーの集約、辞書化ユーティリティを提供。
  - ETL 実装方針
    - 差分取得、backfill、品質チェック（quality モジュール利用）、jquants_client 経由の冪等保存を想定。
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定・探索ユーティリティ。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB 未登録日は曜日ベースでフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・保存。健全性チェック（過度に未来の last_date はスキップ）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - 関数は date オブジェクトを一貫して扱う（タイムゾーン混入防止）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高指標）、Value（PER, ROE）を DuckDB 上で計算する関数を提供。
    - データ不足時の None 返却、営業日ベースでのラグ/リード処理。
    - SQL ウィンドウ関数を活用し効率的に算出。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic、Spearman ランク相関）、rank、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリで完結。
  - zscore_normalize は kabusys.data.stats から再利用可能に設計。

### Changed
- （初版のためなし）

### Fixed
- （初版のためなし）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API の利用:
  - news_nlp / regime_detector は OpenAI API キー（引数 or 環境変数 OPENAI_API_KEY）を必要とする。未設定時は ValueError を投げる。
  - デフォルトモデルは gpt-4o-mini を使用。
- 環境変数の取り扱い:
  - .env の内容は明示的にパースされ、OS 環境変数は既定で保護される（.env ファイルが既存 OS 変数を上書きしない）。
  - 機密情報（トークン・パスワード）は環境変数経由で提供する前提。

### Notes / 設計上の重要な注意点
- ルックアヘッドバイアス防止:
  - AI / リサーチ処理の各関数は date.today()/datetime.today() を内部参照せず、必ず外部から target_date を受け取る設計になっている。
  - DB クエリでも target_date 未満条件やウィンドウ境界を明確にして将来情報の混入を排除。
- フェイルセーフ:
  - OpenAI API の失敗（ネットワーク・レート制限・5xx 等）は再試行やスコアのフォールバック（0.0）を行い、例外で全処理を止めない設計。
- DuckDB 前提:
  - 多くの処理は DuckDB 接続を前提とし、SQL と Python を併用して計算する。
  - DuckDB の executemany に関する挙動に注意（空リストバインド回避のためのチェックあり）。
- テスト性:
  - OpenAI 呼出しやスリープ関数などは patch 可能に実装しておりユニットテストが容易。

### Known Limitations / 今後の改善候補
- monitoring モジュールはエクスポート対象に含まれるが（__all__）実装の有無や機能拡張は今後の課題。
- 一部機能（PBR・配当利回りなどのバリューファクター）は未実装。
- AI のプロンプト・モデル選定は今後アップデートの余地あり（モデル変更に伴う出力形式の互換性に注意）。
- calendar_update_job の J-Quants クライアント実装（jq.fetch_market_calendar / jq.save_market_calendar）に依存するため、外部 API の変更に注意が必要。

---

（注）この CHANGELOG は提供されたコードベースの内容・ドキュメント文字列から推測して作成しています。実際のリリース履歴や追加の変更がある場合は適宜更新してください。