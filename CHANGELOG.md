# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。
Semantic Versioning（https://semver.org/）に従ってバージョン管理を行ってください。

## [Unreleased]
- 今後のリリースに向けた追加事項や修正予定をここに記載します。

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを実装しました。以下はコードベースから推測できる主要な機能、設計方針、重要な挙動のまとめです。

### Added
- パッケージ全体
  - kabusys パッケージ初期版を追加。公開モジュール: data, research, ai, config, など。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは export 句、クォート文字列、エスケープ、インラインコメントを適切に処理。
  - Settings クラスを提供し、必須環境変数の検証・取得を簡易化（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - DB パス既定値（DUCKDB_PATH, SQLITE_PATH）や環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）のバリデーションを実装。

- データプラットフォーム / ETL (kabusys.data.pipeline, etl, calendar_management, jquants_client 依存想定)
  - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーメッセージを集約可能）。
  - 差分取得・バックフィル・品質チェックを想定した ETL パイプライン基盤を実装（jquants_client, quality モジュールとの連携想定）。
  - market_calendar を扱うマーケットカレンダー管理機能を実装:
    - 営業日判定: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル、健全性チェック、冪等保存（ON CONFLICT ロジックを想定）。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバックする堅牢な設計。

- 研究（Research）機能 (kabusys.research)
  - ファクター計算モジュール（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離などを計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials を用いた PER, ROE 計算（target_date 以前の最新財務データを使用）。
    - DuckDB を用いた SQL 中心の実装で、外部 API 呼び出しは行わない設計。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（デフォルト: 1,5,21）。
    - calc_ic: スピアマンのランク相関（IC）を計算し、データ不足時は None を返す。
    - factor_summary / rank: 各ファクターの統計要約・ランク変換を実装。
    - 外部ライブラリに依存しない（標準ライブラリ + DuckDB）実装。

- AI 支援（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を基に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で一括スコアリング。
    - バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密な JSON バリデーション（results リスト、code/score 検証）とスコアの ±1.0 クリップ。
    - DuckDB への書き込みは部分置換（DELETE -> INSERT）で冪等性を確保。executemany 空リストの扱いに対する互換性配慮あり。
    - calc_news_window: JST の時間ウィンドウを UTC naive datetime に変換するユーティリティを提供（ルックアヘッド回避）。
  - レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは専用関数で行い、API エラー時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ設計。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。
    - モデルは gpt-4o-mini を指定、JSON Mode を利用して厳密な JSON レスポンスを期待。

### Changed
- （初版のため「Changed」はなし。将来的なマイグレーションや API 変更はここに記載する想定）

### Fixed
- （初版のため「Fixed」はなし）

### Security
- API キーは明示的に要求される:
  - OpenAI API: score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とし、未設定時は ValueError を送出する。
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を Settings が検証。未設定時は ValueError。
- .env 読み込み時に OS 環境変数は保護（protected set）され、.env.local による上書きは許可されるが OS 環境は上書きされないよう配慮。

### Notes / Design decisions（重要事項）
- ルックアヘッドバイアス回避:
  - 多くの分析/スコアリング関数（news のウィンドウ計算、regime 判定、factor 計算等）が内部で datetime.today() / date.today() を参照せず、関数呼び出し側で target_date を渡すことで未来データ参照を回避している。
- DuckDB を主要なオンディスク DB として使用。SQL とウィンドウ関数を多用した実装。
- API 呼び出しはリトライ・フォールバック設計で堅牢化。LLM のパース失敗や API エラーは例外を投げずフォールバック（多くはスコア = 0.0 やスキップ）して処理継続する。
- テスト容易性を考慮して、OpenAI 呼び出しをラップした内部関数は unittest.mock.patch で差し替え可能な設計。
- DB 書き込みは可能な限り冪等性を確保（DELETE → INSERT、ON CONFLICT 想定）。DuckDB の executemany の仕様（空リスト不可）にも対処。

### Known issues / Limitations
- J-Quants / kabu API クライアントの実装（jquants_client, kabu ステーションクライアント等）は本スナップショットからは省略されているが、pipeline/calendar_update_job 等は外部クライアントに依存する。
- 一部の計算（例: PBR、配当利回り）は未実装（calc_value に明記）。
- News NLP の出力が LLM に依存するため、応答フォーマットの逸脱時にスコアが取得できない場合がある（その場合は対象銘柄をスキップ）。
- DuckDB のバインド/型差異に起因する互換性問題に注意（空の executemany 回避ロジックを追加済み）。

---

過去のリリースや細かなコミット単位の履歴は本ファイルに含めていません。リリースごとの詳細な変更・マイグレーション手順はバージョンアップ時にここへ追記してください。