# Changelog

すべての注目に値する変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース: 0.1.0 - 2026-03-27

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パッケージの公開 API: data, strategy, execution, monitoring（__all__）。
- 環境設定管理:
  - .env / .env.local の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env の行パースは export 形式対応、引用符付き値のエスケープ処理、インラインコメントの扱いなど多様なケースに対応。
    - 既存 OS 環境変数を保護する protected ロジックを導入し、.env.local は上書き（override=True）される。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得可能:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション API: KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）検証機能、is_live/is_paper/is_dev ヘルパー
- AI モジュール（kabusys.ai）:
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ保存する処理を実装。
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたりの最大記事数・文字数制限、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を備える。
    - レスポンスのバリデーション（results 配列フォーマット、コード照合、数値チェック）とスコアクリップを実装。
    - 時間ウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う（calc_news_window）。
    - OpenAI 呼び出しはテスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込み。
    - マクロキーワードフィルタリング、OpenAI 呼び出し（gpt-4o-mini）、リトライ（指数バックオフ）、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみ利用し、datetime.today() を参照しない実装方針。
- Data モジュール（kabusys.data）:
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・次/前営業日の取得・期間内営業日取得・SQ日の判定ロジックを実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。最大探索日数による無限ループ防止、バックフィル・健全性チェック付きの calendar_update_job を提供。
    - J-Quants クライアント経由での差分取得 → 保存処理を実装（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）、J-Quants クライアント経由の保存処理のインターフェースを実装。
    - ETLResult の to_dict により品質問題をシリアライズ可能。
- Research モジュール（kabusys.research）:
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ/流動性（20 日 ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を使って計算する関数を実装。
    - 入力データ不足時の None ハンドリングやログ出力、ルックアヘッドバイアス防止が考慮されている。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（horizons デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。入力検証（horizons 範囲チェック）あり。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーを直接コードに埋め込まず、api_key 引数または環境変数 OPENAI_API_KEY から取得する設計とした。キー未設定時は ValueError を送出して明示的に扱う。

### Notes / 設計上の留意点
- ルックアヘッドバイアス回避：AI モジュール、研究モジュールはいずれも datetime.today() / date.today() を内部ロジックで参照せず、必ず外部から target_date を与える設計。
- フェイルセーフ：OpenAI API 呼び出しに失敗しても処理を継続する（該当スコアを 0.0 にフォールバック、あるいは当該チャンクをスキップ）。DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を行い失敗時は ROLLBACK を試行。
- テスト容易性：OpenAI 呼び出し箇所は内部関数を patch してモック化できるように実装（_call_openai_api を置換可能）。
- DuckDB 互換性：executemany に空リストを渡さない等、DuckDB の仕様差分に配慮した実装（特に ai_scores 書き込みロジック）。
- .env パーサーは多くの実運用ケース（export 形式、引用符、エスケープ、インラインコメント）を想定して実装されているが、稀な形式は想定外の挙動をする可能性があるため .env.example に従うことを推奨。

上記は現行ソースコードから推測される変更点・機能一覧です。実際のリリースノート作成時は、コミット履歴や PR 説明に基づく精査を行ってください。