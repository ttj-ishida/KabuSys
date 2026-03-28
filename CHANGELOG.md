# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース。モジュール群を実装し、日本株のデータ取得・ETL・リサーチ・AIベースのニュース解析・市場レジーム判定を提供。
- kabusys パッケージのバージョン管理を追加（__version__ = "0.1.0"）。
- 環境変数・設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロードする仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（export 形式、クォート、エスケープ、インラインコメント等に対応）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）やログレベル検証等の取得を提供。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require を実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）を用いてセンチメントを -1.0〜1.0 にスコア化し ai_scores に書き込む処理を実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数と文字数のトリム制御、JSON mode のレスポンス検証と復元ロジックを備える。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフ対応、フェイルセーフ（API 失敗時は該当チャンクをスキップし続行）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出、market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュース抽出（キーワードリスト）、OpenAI 呼び出し（gpt-4o-mini）、リトライ・フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - Look-ahead バイアス防止設計（内部で datetime.today()/date.today() を参照しない、DB クエリは target_date 未満などの排他条件を利用）。
- Research モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を使用）。
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日ATR、相対ATR、流動性指標）、バリュー（PER, ROE）を計算。
    - データ不足時の None ハンドリング、DuckDB ベースの SQL 実装。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - 将来リターンの計算（任意ホライズン）、Spearman（ランク）ベースの IC 計算、統計サマリー等を提供。
    - pandas 等に依存しない純 Python / DuckDB 実装。
- Data モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック、最大探索日数による安全措置を実装。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存）。
  - pipeline: ETLResult データクラスを実装し ETL の実行結果（取得数・保存数・品質問題・エラー等）を集約。kabusys.data.etl で ETLResult を再エクスポート。
  - ETL パイプライン基盤を実装（差分取得、保存、品質チェック方針の設計を反映）。
- 一般的な実装方針・堅牢化
  - DuckDB を主要なローカル分析 DB として使用。
  - DB 書き込みは冪等性（DELETE→INSERT または ON CONFLICT）や BEGIN/COMMIT/ROLLBACK の適切な取り扱いを重視。
  - API 呼び出しに対するリトライ、5xx の挙動考慮、レスポンスのバリデーションとフェイルセーフ設計を組み込み。
  - テストのために内部の API 呼び出しラッパーをモック可能に設計（例: _call_openai_api の patch）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env の自動ロード時、既存の OS 環境変数は保護（protected set）され、.env.local は override=True でも OS 環境変数を上書きしない仕組みを実装。
- OpenAI API キーや各種トークンは必須環境変数として設計され、未設定時は明示的な例外で検出される（安全な fail-fast）。

---

注意・利用上のポイント
- OpenAI API を利用する機能（score_news / score_regime）は OPENAI_API_KEY の設定が必須です。api_key 引数で明示的にキーを渡すことも可能です。
- 自動で .env を読み込む挙動は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途など）。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提になります。初期データロード・マイグレーションは別途実行してください。
- 各種外部 API（J-Quants, kabuステーション, OpenAI）呼び出し部分はエラー時にフェイルセーフ化されていますが、APIキーやネットワーク状態に注意して運用してください。

今後の予定（例）
- 監視・モニタリング機能の実装（monitoring パッケージは __all__ に含め済み、実装が追加される予定）。
- 追加のファクター・ファインチューニング・ETL の自動化強化。