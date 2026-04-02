# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

全般ルール:
- セマンティクスに基づく分類（Added / Changed / Fixed / Deprecated / Removed / Security）を使用します。
- 日付はリリース日を示します。

## [Unreleased]
- （現在のコードベースでは未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初期リリース。以下の主要機能・モジュールを実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。__version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。.env.local は .env を上書き。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ（export 形式、クォートやエスケープ、インラインコメント処理に対応）。
  - OS 環境変数を保護する protected 機能（自動ロード時の上書き抑止）。
  - Settings クラスを公開（settings）。J-Quants / kabu / Slack / DB パス / 監視しきい値 / ログレベル / env 等のプロパティを提供。
  - 必須設定未定義時は _require が ValueError を送出。

- AI（自然言語処理）機能（src/kabusys/ai）
  - ニュースセンチメント（news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）の JSON mode を利用して各銘柄のセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチ処理（_BATCH_SIZE=20）、記事/文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、チャンク毎の再試行（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）。API 失敗時はそのチャンクをスキップし他チャンクは継続するフェイルセーフ設計。
    - calc_news_window(target_date) により JST の「前日15:00〜当日08:30」ウィンドウを UTC naive datetime で計算（ルックアヘッドバイアス回避）。
  - 市場レジーム判定（regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等的に書き込み。
    - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、リトライ（429/ネットワーク/タイムアウト/5xx）およびフォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避に配慮（内部で datetime.today() を参照しない、prices_daily は target_date 未満のみ参照）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダーに基づく営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新するジョブを実装（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを追加（取得件数・保存件数・品質チェック結果・エラー等を保持）。to_dict により品質問題を辞書化可能。
    - 差分取得、backfill、品質チェック（quality モジュール使用）を想定した設計。jquants_client（jq）経由での取得/保存フローを想定。
    - etl モジュールから ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクターを実装。DuckDB を利用した SQL ベースの集計を行い、(date, code) ごとの dict リストを返す設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
  - research パッケージの __init__ で必要関数をエクスポート。
  - data.stats から zscore_normalize を再エクスポート。

### Changed
- （初期リリースのため変更履歴はありません）

### Fixed
- （初期リリースのため修正履歴はありません）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- 環境変数自動ロード時に OS 環境変数を保護する仕組みを導入（protected set）。自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加し、テスト時の誤動作リスクを低減。

### Notes / Known issues
- pipeline.py の内部関数 _get_max_date の末尾が不完全（コード断片が見られる）ため、その部分は実装ミス・未完成の可能性があります。リリース前に該当箇所の修正を推奨します。
- OpenAI SDK の例外取り扱いは将来の SDK 変更に備え getattr を使用する等の互換性配慮を行っていますが、外部 API の挙動やモデル仕様の変更により追加調整が必要になる可能性があります。
- DuckDB 向けの executemany/リストバインドはバージョン差異に依存するため、互換性のために個別 DELETE → INSERT のフローを採用しています。環境に応じてテストを行ってください。

――――――
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして利用する際は、コミット履歴やリリース方針に基づいて修正・追記してください。