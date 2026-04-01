# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リンク、Issue 番号等がないため、変更点はコードベースの実装内容から推測して記載しています。

最新の変更は一番上に記載します。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-01
初回公開リリース。以下の主要機能と設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0 に設定。
  - パッケージ公開インターフェース: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - export KEY=val 形式やクォート・エスケープ、インラインコメント処理に対応した .env パーサ実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視/システム設定等のプロパティを環境変数から取得。
  - 環境変数の必須チェック（_require）と有効値チェック（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄 / バッチ）、記事数上限・文字数トリム、JSON Mode レスポンス検証、スコアの ±1.0 クリップなどを実装。
    - レート制限・タイムアウト・ネットワーク断・5xx を対象とした指数バックオフによるリトライ、およびフェイルセーフ（エラー時はスキップして他銘柄処理継続）。
    - レスポンス検証ロジック（JSON 抽出、results 構造検証、スコア数値検証、未知コード無視）。
    - テスト用フック: _call_openai_api を patch してモック可能。
    - 最終結果を ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込み。
    - prices_daily の過去データのみを使用することでルックアヘッドバイアスを排除。
    - OpenAI API 呼び出しは独立実装（news_nlp と private 関数共有しない）でテスト差し替え可能。
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（土日休み）でフォールバックする設計。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等保存、バックフィル・健全性チェックを実装。
  - ETL / パイプライン (pipeline / etl)
    - ETLResult データクラスを導入し、ETL の取得件数・保存件数・品質チェック結果・エラーを集約して返却可能に。
    - 差分更新・バックフィル・品質チェックを行うパイプライン設計方針をコードで反映（jquants_client, quality モジュールとの連携想定）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ機能 (kabusys.research)
  - factor_research: モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（不足時は None）。
    - ボラティリティ: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足時は None）。
    - バリュー: raw_financials から最新財務データを取得して PER/ROE を計算（EPS=0/欠損では None）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）に対応し、入力チェック（horizons の妥当性）を導入。
    - calc_ic はスピアマン（ランク）相関を計算し、サンプル不足時に None を返す。
    - factor_summary は count/mean/std/min/max/median を計算。

### Changed
- （初回リリースのため、過去からの変更はなし）

### Fixed
- 各モジュールで API エラー / レスポンスパース失敗時に例外を投げずフォールバックする実装を導入（AI モジュールの堅牢化）。
- .env 読み込みでファイル読み込み失敗時に警告を出して続行するように変更（環境依存の堅牢化）。

### Security
- OpenAI API キーや各種トークンは Settings を通じて環境変数で管理。必須項目未設定時は明示的に ValueError を送出して安全性を確保。

### Notes / Known limitations
- 一部機能が未実装・明示的に保留されている点：
  - calc_value の PBR / 配当利回りは未実装（コメントで明示）。
  - news_nlp, regime_detector は gpt-4o-mini を使用する設計。将来的なモデル交換に対応する余地あり。
- ETL パイプラインの pipeline._get_max_date 関数実装にファイル末尾で切れている（現状の配布コード断片では実装が不完全に見える）。実動環境へデプロイする前に当該箇所の実装確認・修正が必要。
- DuckDB の executemany で空リストを禁止する制約に配慮した実装がある（互換性対策）。
- すべての日付処理でルックアヘッドバイアスを防ぐため datetime.today()/date.today() を直接参照しない設計が意図的に採用されている（target_date を明示的に渡す方式）。

---

履歴はコード実装を元に推測して作成しています。実際のリリースノート作成時はコミットログや Issue、Pull Request の情報を参照して正確な記述に更新してください。