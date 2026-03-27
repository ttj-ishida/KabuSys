# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

継続的インテグレーション／リリースノートは主にコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回公開リリース。日本株自動売買システムのコアライブラリ群を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys/__init__.py、__version__ = "0.1.0"）。
  - モジュール構成: data, research, ai, execution, strategy, monitoring（公開APIとして __all__ を定義）。

- 設定・環境変数管理（kabusys.config）
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - .env/.env.local の読み込み順序と上書きルール（OS環境変数保護）を実装。
  - .env パーサは export プレフィックス、クォート、エスケープ、行末コメント等に対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス 等の設定アクセスを型付きプロパティで提供。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
  - 必須環境変数未設定時に明示的な ValueError を送出する _require を実装。

- ニュースNLP / AI（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存する score_news を実装。
  - ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST 相当）を計算する calc_news_window を実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、記事トリミング、最大記事数制限などトークン肥大化対策を実装。
  - API 失敗（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフリトライを実装。
  - レスポンスの検証ロジック（JSON 抽出、results 構造検証、コード整合性、数値検証、±1.0 クリップ）を実装。
  - テスト支援のため _call_openai_api を patch で差し替え可能に設計。
  - フェイルセーフ: API 呼び出し失敗時は対象銘柄をスキップし、処理継続。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせ、日次で市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
  - マクロキーワードで raw_news を抽出し、OpenAI に JSON 出力を求めて macro_sentiment を取得。
  - OpenAI 呼び出しのリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
  - レジームスコア合成、閾値によるラベリング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - ルックアヘッドバイアス対策（datetime.today()/date.today() 参照回避、DB クエリに date < target_date を用いる設計）。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を計算（最新財務レコードを参照）。
    - DuckDB 上で SQL とウィンドウ関数を使って効率的に実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクで処理するランク関数を実装（round による安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを実装。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（土日休場）を使用。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する calendar_update_job を実装（バックフィル・健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加（取得数、保存数、品質問題、エラー集約などを保持）。
    - 差分取得、backfill、品質チェック（quality モジュールとの連携）、jquants_client 経由での冪等保存を想定した設計。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
  - etl モジュールは ETLResult をエクスポート。

- ロバスト性・運用性
  - DuckDB 互換性考慮（executemany に空リストを渡さない等のワークアラウンド）。
  - 各所にログ出力（info/warning/debug）を配置し運用時のトラブルシュートを支援。
  - API キーは引数で注入可能（テスト容易化）。OpenAI 呼び出しは明示的に api_key を受け取るか環境変数 OPENAI_API_KEY を利用。
  - 外部 API 失敗時はフェイルセーフ（スコア=0、処理スキップ）で上位例外を極力防ぐ設計。

### Changed
- 初回リリースのため該当なし（新規実装）。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI や外部 API キーの扱いは環境変数から読み込む設計で、コードに埋め込まない方針を明記。
- .env ファイル読み込み時に OS 環境変数を保護する仕組みを実装（既存の env を上書かない/protected set）。

### Known limitations / Notes
- OpenAI の利用には有効な API キー（引数または OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
- news_nlp / regime_detector は gpt-4o-mini の JSON モードに依存している。API の挙動変更があった場合の互換性は要確認。
- 一部の外部依存（jquants_client, quality モジュール等）はインターフェース想定での実装。実際の API 呼び出し実装は別モジュールに委譲される。
- execution / strategy / monitoring の詳細は本リリースでは最小限の公開のみ。取引実行やストラテジ実装は別途拡張を想定。
- DuckDB バージョン差分による SQL バインドの挙動に注意（コメントにある通り互換性ワークアラウンドを実装済み）。

---

（補足）本 CHANGELOG は提供されたソースコードから機能と設計意図を推測して作成しています。実際のリリースノートとして利用する場合は、実装過程のコミット履歴・変更差分・運用要件に基づいて調整してください。