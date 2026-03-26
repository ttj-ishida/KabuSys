# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に従います。

フォーマット:
- 変更はバージョンごとにまとめ、カテゴリは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。
- 参考: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-26

概要: 初期リリース。日本株自動売買システム「KabuSys」のコア機能群（設定管理、データETL・カレンダー管理、リサーチ用ファクター計算、ニュースNLP と市場レジーム判定、パッケージ公開エントリポイントなど）を実装。

### Added
- パッケージ初期公開
  - src/kabusys/__init__.py に主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。
  - バージョン定義: __version__ = "0.1.0"。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env と .env.local の読み込み順序を導入 (.env.local が上書き)。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理をサポート。
  - 必須設定取得用 _require と Settings クラスを提供（J-Quants / kabuステーション / Slack / DBパス / 環境種別/ログレベル等）。
  - 環境変数のバリデーション: KABUSYS_ENV は development/paper_trading/live のいずれか、LOG_LEVEL は標準ログレベルのいずれかでないと例外。

- AI（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を利用して銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini / JSON Mode）でセンチメント評価を行い ai_scores テーブルへ書き込む機能を実装。
    - 処理のポイント:
      - JST基準のニュースウィンドウ計算（前日15:00 ～ 当日08:30 JST）を calc_news_window で提供。
      - 1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でプロンプト肥大化を抑制。
      - 最大バッチ処理数（_BATCH_SIZE）でバッチ送信、最大20銘柄/回。
      - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
      - レスポンス検証（JSON パース補正、results キー・型検査、未知コードの無視、スコア数値バリデーション）。
      - スコアを ±1.0 にクリップし、ai_scores テーブルへは対象コードのみ置換（DELETE→INSERT）して部分失敗時の既存データ保護。
      - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch 推奨）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースLLMセンチメント（重み30%）を合成し、日次で market_regime テーブルへ冪等書き込みする機能を実装。
    - 処理のポイント:
      - ma200_ratio を DuckDB の prices_daily から計算（target_date 未満のデータのみを使用しルックアヘッド回避）。
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出、OpenAI に投げて macro_sentiment を取得（記事なしなら LLM 呼び出しを省略）。
      - API エラー時は macro_sentiment=0.0 のフェイルセーフ動作を採用。
      - レジームスコアは clip して所定閾値から bull/neutral/bear を決定し market_regime テーブルへ（BEGIN/DELETE/INSERT/COMMIT）で冪等に保存。
      - OpenAI 呼び出しは独立実装でモジュール間結合を低く保つ。リトライロジックと 5xx 判定を実装。

- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティ群を実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - カレンダーの夜間バッチ更新 job（calendar_update_job）を実装（J-Quants API 経由の差分取得、バックフィル、健全性チェックを含む）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル日数設定を導入。

  - ETL パイプライン（pipeline）
    - ETL 実行結果を表現する ETLResult dataclass を追加（取得件数／保存件数／品質問題／エラーの集約）。
    - 差分更新・バックフィル・品質チェックのためのユーティリティ（_get_max_date 等）を追加。
    - jquants_client および quality モジュールとの連携設計を想定。

  - ETL の公開インターフェース（etl）
    - pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR/相対ATR、20日平均売買代金、出来高比率、財務ベースの PER / ROE を DuckDB 上で計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 処理やウィンドウバッファ設計（スキャン日数のバッファ）を考慮。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの将来終値を LEAD で取得しリターンを計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。3件未満は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めで ties を検出。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）を再エクスポート。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Deprecated
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Security
- OpenAI API キーは引数(api_key)でも注入可能で、環境変数 OPENAI_API_KEY を使う場合も明示的にチェックしていない場合は例外を投げる設計とすることで、キー未設定のままの誤動作を防止。

### Notes / 設計上の重要ポイント（実装ポリシー）
- ルックアヘッドバイアス回避:
  - 各 AI/研究モジュールは datetime.today() / date.today() を内部で参照せず、必ず target_date を外部から注入して動作する設計。
  - DB クエリは target_date 未満／以前等の明示的条件で未来データ参照を防止。
- フェイルセーフ:
  - OpenAI 呼び出し失敗や予期しないレスポンスは基本的に例外で停止させず、フォールバック（0.0 やスキップ）して処理を継続する方針（運用上の安全性重視）。
- DuckDB 互換性考慮:
  - executemany に空リストが渡せない等の DuckDB のバージョン差異を吸収する実装上の配慮あり。
- テスト容易性:
  - OpenAI 呼び出しヘルパー（各モジュール内の _call_openai_api）をテストで差し替え可能にしている。

---

今後のリリースで追加する予定:
- strategy / execution / monitoring の具体的なトレード実行ロジック（現在はパッケージ構造のみエクスポート）
- jquants_client の具体的実装と ETL のフルパイプライン完成
- 追加の品質チェックルール、モニタリング・アラート連携（Slack通知など）の実装

もし CHANGELOG に特定の変更点（例えばコミットやPRベースの追記）を追加したい場合は、対象ファイルや差分の情報を提供してください。