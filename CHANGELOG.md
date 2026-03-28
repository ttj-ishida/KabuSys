# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※ バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]

## [0.1.0] - 2026-03-28

初回公開リリース。

### Added
- 基本パッケージ構成を追加。
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 環境・設定管理モジュール (kabusys.config) を追加。
  - .env / .env.local ファイルと OS 環境変数から設定を読み込む自動ローダーを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索し、CWD に依存しない実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export KEY=val, シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 既存 OS 環境変数を保護する protected set の仕組みを実装（.env.local は override=True により上書き）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別 / ログレベル等のプロパティを取得。入力値検証（KABUSYS_ENV と LOG_LEVEL の許容値チェック）を実装。

- AI 関連モジュールを追加 (kabusys.ai)。
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ（最大20銘柄）処理、文字数・記事数トリム、JSON Mode レスポンスのバリデーション、クリップ（±1.0）、エクスポネンシャルバックオフのリトライ等を実装。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - DuckDB の executemany に対する互換性（空リストの扱い）を考慮して安全に書き込みを行う。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照せず、target_date ベースのウィンドウ計算を採用。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは内部で独立実装し、API 呼び出し失敗時には macro_sentiment=0.0 で継続するフェイルセーフを実装。
    - LLM 呼び出しはリトライ戦略（指数バックオフ、5xx の扱い）を導入。

- Research / ファクター関連モジュールを追加 (kabusys.research)。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS 不在・ゼロは None）。
    - DuckDB を用いた SQL ベースの実装。結果は (date, code) をキーとする辞書リストで返却。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーション（正の整数かつ <= 252）を実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。必要最小サンプル数チェックを実装。
    - rank: 同順位は平均ランクにするランク化実装（丸めによる ties 回避）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - 外部依存を持たない（pandas 等を使わず標準ライブラリ＋duckdb）。

- Data / ETL / カレンダー関連モジュールを追加 (kabusys.data)。
  - calendar_management:
    - market_calendar を基に営業日判定、次/前営業日の検索、期間内営業日取得、SQ 日判定等のユーティリティを提供。
    - DB にデータが無い場合は曜日ベース（土日除外）でフォールバックする一貫した挙動を実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィル・健全性チェックを実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新するバッチ処理を実装（fetch/save のエラーハンドリングあり）。
  - pipeline / etl:
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプライン (kabusys.data.pipeline) にて差分取得、保存（jquants_client 経由で idempotent 保存）、品質チェック（quality モジュール）連携のためのユーティリティ実装。
    - ETLResult は品質問題・エラーメッセージを収集し、辞書化メソッドを持つ（監査ログ用）。

- 各所でのロギングとエラーハンドリングの整備。
  - DB 操作での BEGIN/COMMIT/ROLLBACK の採用、ROLLBACK 失敗時の警告ログなど堅牢性を考慮。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。API キー未設定時は ValueError を発生させて誤使用を防止。

---

注記（実装上の重要ポイント／設計判断、ドキュメント的メモ）
- ルックアヘッドバイアス防止: AI モジュール・研究モジュールともに内部で date.today()/datetime.today() を参照せず、明示的な target_date を必須にしている。
- OpenAI 呼び出しはテスト時に差し替え可能なよう設計（unit test 用の patch ポイントを用意）。
- DuckDB のバージョン互換性（executemany に空リストを渡せない等）を意識した実装が各所にある。
- .env パーサは POSIX 系の細かなケース（export プレフィックス、クォート内エスケープ、インラインコメント条件）に対応している。

もしリリースノートに追記してほしい箇所（例: 実際の API 結合テスト結果や既知の制約、互換性情報など）があれば、その情報を提供してください。補足して更新します。