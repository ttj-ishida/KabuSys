# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

現在のバージョン: 0.1.0 — 2026-03-29

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下は主な追加点・設計方針・注意点の要約です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ に主要サブパッケージ（data, research, ai, execution, monitoring, strategy 等を想定）をエクスポートする仕組みを追加。
  - バージョン情報: __version__ = "0.1.0" を設定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env パーサー: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの解析に対応。
  - 自動ロード抑止用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の環境変数をプロパティ経由で取得。
  - バリデーション: KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL の検証、未設定必須変数は ValueError を送出する _require() を実装。
  - デフォルト DB パス: duckdb -> data/kabusys.duckdb, sqlite -> data/monitoring.db を採用。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を用いた銘柄別ニュース集約。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ保存する処理を実装。
    - バッチ送信（_BATCH_SIZE=20）、1銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化を抑止。
    - 再試行ロジック（429, ネットワーク断, タイムアウト, 5xx に対して指数バックオフ）を実装。
    - レスポンス検証機能を実装し、未知の銘柄コードや不正なスコアを無視するフェイルセーフを備える。
    - 書き込みは部分失敗を考慮し、取得スコアがあるコードのみ DELETE → INSERT（冪等）で置換。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、calc_news_window 経由でニュースウィンドウを決定。
    - OpenAI 呼び出しのリトライ・フォールバック（API失敗時は macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キーは関数引数または環境変数 OPENAI_API_KEY で注入可能。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を使った営業日判定・次/前営業日検索・期間内営業日列挙・SQ日判定を実装。
    - market_calendar の未取得時は曜日ベース（土日休）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得→保存（バックフィル・健全性チェック含む）。
    - 最大探索範囲やバックフィル、先読み日数の定数を定義して安全策を導入。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー）を収集可能に。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント抽象化を使用）。
    - テーブル存在チェックや最大日付取得などのユーティリティを実装。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB 上で SQL ウィンドウ関数を活用し営業日ベースの計算を行う。
    - データ不足時の None 処理やロギングを実装。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（任意ホライズン対応）を実装。
    - IC（Spearman ρ）を計算する calc_ic、rank、factor_summary（基本統計）を実装。
    - pandas 非依存（標準ライブラリのみ）で実装。

- テスト性・注入ポイント
  - OpenAI 呼び出しは内部で _call_openai_api を経由しており、ユニットテスト時に patch して差し替え可能（news_nlp と regime_detector で独立実装）。

### 変更 (Changed)
- 設計方針の徹底
  - ルックアヘッドバイアス防止のため、各処理は datetime.today() / date.today() を積極的に参照しない設計（target_date を明示的に受け取る）。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 相当）して部分失敗時のデータ保護を優先。

### 修正 (Fixed)
- フォールバックとフェイルセーフの追加
  - OpenAI API 呼び出しの失敗時に例外を暴露しない箇所を明確化し、サービス全体の継続性を確保（macro_sentiment / news scoring が失敗しても 0 にフォールバック）。
  - DuckDB executemany の空リスト制約へ対処（空の場合は呼ばないよう保護）。

### 注意 (Notes)
- 外部依存
  - OpenAI SDK（chat completions API）や DuckDB, J-Quants クライアント、kabuステーション API など外部コンポーネントが前提です。環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を正しく設定してください。
- データベーススキーマ
  - 本コードは prices_daily、raw_news、news_symbols、ai_scores、market_regime、market_calendar、raw_financials 等のテーブル存在を前提としています。初期ロードやスキーマ準備を行ってください。
- セキュリティ
  - .env の自動読み込みはデフォルトで有効です。CI/テスト環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 互換性
  - DuckDB バージョンによるバインド挙動（ANY / executemany 空リスト）に配慮した実装を行っていますが、実運用時は利用する DuckDB のバージョンでの動作確認を推奨します。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使う場合は、変更点や既知の問題・リスク等をプロジェクトの実際の運用チームと合わせて調整してください。