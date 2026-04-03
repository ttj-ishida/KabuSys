# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
本ファイルはコードベースの現在の状態（version 0.1.0）から推測して作成しています。

## [Unreleased]
- 今後の変更・既知の改善案をここに記載します（現時点では特に未リリースの変更はなし）。

## [0.1.0] - 2026-04-03
初期リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群を含む一式を実装。

### Added
- パッケージ基盤
  - kabusys パッケージエントリを追加（version = 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 / ロード
  - 環境変数読み込みユーティリティを実装（kabusys.config）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を検出）から自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式やクォート・エスケープ・インラインコメントに対応したパーサ実装。
    - override / protected オプションにより OS 環境変数保護や上書き制御をサポート。
  - Settings クラスを提供し、主要な設定をプロパティで公開。
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須環境変数チェック。
    - データベースパス(DUCKDB_PATH / SQLITE_PATH)、監視設定（PID ファイル / KILL フラグ）、閾値（CPU/MEM/DISK）等。
    - 環境（development / paper_trading / live）とログレベルの検証ロジック。
    - is_live / is_paper / is_dev といったユーティリティプロパティ。

- AI（NLP）関連
  - kabusys.ai.news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む機能を実装。
    - ニュース集計ウィンドウ（前日15:00 JST～当日08:30 JST）計算機能。
    - 銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - バッチ（最大 20 銘柄）での API 呼び出し、JSON mode を用いた厳密なレスポンス検証。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - レスポンス検証とスコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する置換（DELETE → INSERT）戦略。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - kabusys.ai.regime_detector: ETF(1321)の200日MA乖離（70%）とマクロニュースセンチメント（30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily から MA200 乖離を計算（ルックアヘッドバイアス回避のため target_date 未満のみ使用）。
    - raw_news からマクロキーワードでフィルタしてタイトルを抽出。
    - OpenAI 呼び出し（gpt-4o-mini）で宏観センチメントを JSON 出力で受け取りパース。
    - API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - 結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK）。

- データ基盤（Data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未登録の場合は土日フォールバックを利用し一貫性を維持。
    - 夜間の calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の各種カウント・品質問題・エラーの集約）。
    - 差分更新・バックフィル・品質チェックを想定した ETL パイプライン設計（jquants_client 経由での保存／品質チェックの収集を想定）。
    - DuckDB をベースにしたテーブル存在チェックや最大日付取得等のユーティリティを実装。
  - etl 周辺の設計方針として、API 後出し修正吸収のためのバックフィルや部分失敗からのデータ保護を導入。

- 研究（Research）
  - factor_research:
    - モメンタム（1M/3M/6M、200日MA乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB ベースで計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時は None を返す設計、SQL ウィンドウ関数を活用した実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、安全チェックあり）。
    - IC（Information Coefficient）計算（スピアマンρ）と rank ユーティリティ（同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）算出。
    - pandas 等に依存せず標準ライブラリのみで実装。

- 共通実装上の注意点 / 設計決定
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部ロジックで参照しない方針（target_date を明示的に渡す設計）。
  - DuckDB を主要なローカル分析 DB として使用。多くの書き込みは冪等（DELETE→INSERT）または ON CONFLICT 想定。
  - OpenAI API 呼び出しは各モジュールで独自に実装し、モジュール間でプライベート関数を共有しない設計（テスト性向上）。
  - 外部 API（OpenAI / J-Quants）への依存点では、API エラー時にフェイルセーフ（スコア 0.0、処理スキップ）で継続する設計を採用。
  - バッチサイズや上限（_BATCH_SIZE=20, _MAX_CHARS_PER_STOCK=3000 等）を設定し、トークン肥大化対策を実施。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （既知の認証情報は環境変数経由で取得する設計。敏感情報は .env/.env.local を利用してローカルで管理する想定）

## 既知の制限・注意事項（コードからの推測）
- OpenAI API キー（OPENAI_API_KEY）や J-Quants のリフレッシュトークン等は必須。Settings._require により未設定時は例外になる箇所あり。
- news_nlp の出力は厳密な JSON を期待するが、万一の余計なテキスト混入に備えた復元ロジックを入れているものの完全な安全は保証されない。
- calc_value では現時点で PBR や配当利回りは未実装。
- DuckDB の executemany に空リストを渡せない（0.10 系）ことを考慮したガードがあるため、異なる DuckDB バージョンでの動作差異に注意。
- calendar_update_job の fetch/save は外部 jquants_client の実装に依存。API エラー時は 0 を返して終了する。

---
（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートやユーザー向け変更点はプロジェクトの公式ドキュメント／リリースプロセスに従って調整してください。