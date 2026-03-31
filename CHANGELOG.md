# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
安定版リリース前の初期バージョンとして、主に機能追加を行ったリリースです。

## [Unreleased]

## [0.1.0] - 2026-03-31

### Added
- パッケージの初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ初期公開の主要コンポーネントを追加:
  - 環境設定
    - 環境変数読み込み・管理モジュール (kabusys.config)
      - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env / .env.local を読み込む仕組み。
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - .env のパースはシェル風の `export KEY=val`、クォート、インラインコメント等に対応。
      - 必須環境変数取得用ヘルパー `_require` と Settings クラスにより、設定値をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
      - デフォルトの DB パス: DUCKDB_PATH=`data/kabusys.duckdb`, SQLITE_PATH=`data/monitoring.db`。
      - 環境 `KABUSYS_ENV` に対するバリデーション（development/paper_trading/live）とログレベル検証。
  - AI（自然言語処理）モジュール
    - ニュース NLP スコアリング (kabusys.ai.news_nlp)
      - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）に送信、センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
      - バッチ処理（チャンクサイズ最大 20 銘柄）、1 銘柄あたり最大記事数・文字数制限、リトライ（429/接続/タイムアウト/5xx に対する指数バックオフ）を実装。
      - レスポンス検証ロジック（JSON 抽出、results 配列・code/score の検証、スコアのクリップ）。
      - テスト容易性のため OpenAI 呼び出し関数を patch で差し替え可能（_call_openai_api をモック）。
    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
      - LLM 呼び出し失敗時は macro_sentiment=0.0 で継続するフォールバックを採用。
      - OpenAI API 呼び出しは独立実装でモジュール結合を避ける設計（news_nlp と共有しない）。
  - Data（データ基盤・ETL）
    - ETL インターフェース公開 (kabusys.data.etl -> ETLResult)
    - ETL パイプライン (kabusys.data.pipeline)
      - 差分取得、バックフィル、品質チェックのための ETLResult（品質問題の集計、エラー管理）を実装。
    - マーケットカレンダー管理 (kabusys.data.calendar_management)
      - market_calendar 更新ジョブ（J-Quants からの差分取得・バックフィル・健全性チェック）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - DB にデータがない場合は曜日ベース（土日非営業日）でのフォールバックロジックを提供。
  - Research（リサーチ用ファクター計算）
    - factor_research モジュール
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算。
      - データ不足時や条件未充足時は None を返す設計。
    - feature_exploration モジュール
      - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク関数を実装。
      - pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB で実装。
  - パッケージ初期 API エクスポート
    - kabusys.__all__ に data, strategy, execution, monitoring を想定した公開領域を定義（各サブパッケージは一部実装済み）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数や API キー（OpenAI, J-Quants, KabuStation, Slack 等）を使用するため、.env ファイルや環境変数の管理には注意が必要。Settings は必須環境変数未設定時に ValueError を投げる。
- .env 自動読み込みはプロジェクトルートを基準に行うが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止:
  - AI モジュール（news_nlp, regime_detector）およびリサーチ系関数では datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す方式を採用。
  - prices_daily 等の DB クエリは target_date 未満 / 指定範囲の排他条件を守るように実装。
- DB 書き込みは冪等性と部分失敗耐性を考慮:
  - market_regime / ai_scores 等へは DELETE → INSERT の形で置換を行い、部分失敗時に既存データを不必要に消さない配慮をしている（DuckDB の executemany に関する注意点を考慮）。
- OpenAI とのやり取り:
  - 使用モデル: gpt-4o-mini（JSON mode を利用する想定）。
  - リトライとバックオフ: 429 / 接続断 / タイムアウト / 5xx に対し指数バックオフでリトライ、最終フォールバックはスコア 0.0 またはスキップ（例外は上げない設計）。
  - テスト時は内部の _call_openai_api を patch して API 呼び出しを差し替え可能。
- 依存:
  - duckdb、openai SDK を利用する前提。その他は標準ライブラリで実装。
- デフォルトのファイル / テーブル:
  - DuckDB: data/kabusys.duckdb（DUCKDB_PATH 環境変数で変更可能）
  - SQLite (monitoring): data/monitoring.db（SQLITE_PATH 環境変数で変更可能）
- 制限・既知の未実装点:
  - Research の Value ファクターで PBR・配当利回りは未実装。
  - strategy / execution / monitoring パッケージは __all__ に含まれているものの、この差分では一部機能の実装が初期段階に留まる可能性がある（以降のリリースで拡張予定）。

### Migration / Upgrade Notes
- 既存の .env フォーマットはシェル風（export 対応、クォート対応、インラインコメント処理）を前提としています。特殊な .env 形式を使用している場合は挙動を確認してください。
- DuckDB のバージョン互換性に関して、executemany に空リストを渡すとエラーとなる（0.10 系）ため、空チェックを行っている。DuckDB のメジャーアップデート時は該当箇所に注意してください。

---

今後のリリースでは以下を予定:
- strategy / execution の注文ロジック（kabuステーション API 連携）実装強化
- モデル改善（プロンプトチューニング、バッチ処理改善）
- テストカバレッジと CI の整備
- ドキュメント（使用例、運用手順、DB スキーマ）の拡充

もし特定機能や変更点の詳細（例: 各関数の使用例、環境変数テンプレート、DB スキーマ推奨 など）をCHANGELOGに追加したい場合は、どの項目を優先するか教えてください。