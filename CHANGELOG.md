# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
現在のバージョンは 0.1.0 です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装・公開します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - public API の __all__ を定義して主要モジュール（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env/.env.local の読み込み優先度を実装（OS環境変数保護、.env → .env.local の順で上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト向け）。
  - 強力な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得（必須キー未設定時は ValueError を発生）。
  - 設定の検証：KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェック。
  - データベースパス（DUCKDB_PATH, SQLITE_PATH）や API ベース URL のデフォルト値を提供。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - 指定日の「前日15:00 JST ～ 当日08:30 JST」ウィンドウ（UTC 変換済）に基づく記事集約ロジックを実装。
    - 銘柄ごとに記事を結合・トリム（最大記事数・最大文字数制限）して、OpenAI（gpt-4o-mini）の JSON Mode で一括スコアリング。
    - バッチサイズ、リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出フォールバック、結果キー・型検査、コード照合、数値検証）。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ書き込み（部分失敗時に既存データを守るためコード単位で DELETE → INSERT）。
    - テスト容易性のため API 呼び出し箇所を patch 可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - ma200_ratio 計算は target_date 未満データのみを使用してルックアヘッドバイアスを排除。
    - マクロ記事はキーワードフィルタで抽出、OpenAI（gpt-4o-mini）により JSON 応答で macro_sentiment を取得。
    - API 再試行・フェイルセーフ動作（API 失敗時は macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データ処理（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar が未取得（または該当日が NULL）の場合は「曜日ベース（平日を営業日）」でフォールバック。
    - next/prev_trading_day は DB 登録値を優先しつつ未登録日は曜日フォールバックで一貫した探索を実現。探索上限を設定して無限ループを防止。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得 → 保存（バックフィルや健全性チェックを含む）を実行。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを導入し、ETL 実行のメタ情報（取得/保存レコード数、品質問題、エラー等）を集約。to_dict によりログ保存用の辞書化を提供。
    - 差分取得・バックフィル・品質チェック方針を実装（設計ドキュメントに基づいた骨子）。
    - DuckDB との互換性考慮（テーブル存在チェック、MAX(date) 取得ユーティリティ等）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR20、平均売買代金、出来高比率、PER/ROE 等を DuckDB SQL で算出。
    - データ不足時の None ハンドリング、営業日スキャン範囲のバッファ処理を含む。
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary を実装
    - 将来リターンの一括取得（任意ホライズン）、スピアマン IC（ランク相関）計算、ランク付け（同順位は平均ランク）、基本統計サマリーを標準ライブラリのみで実装。
  - データ処理は外部 API や発注系にアクセスせず、DuckDB のみ参照する安全設計。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: 各 AI / リサーチ処理は内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を与える設計。
- フェイルセーフ: OpenAI など外部 API の失敗は基本的に例外を投げず、デフォルト値（macro_sentiment=0.0 など）へフォールバックして継続する方針。
- テスト容易性: OpenAI 呼び出し箇所を patch できるよう分離し、api_key を引数で注入可能とすることで単体テストが容易。
- DuckDB の互換性: executemany に空リストを渡せないバージョンへの対処（事前に空チェック）などを行い互換性を高めている。
- ロギング: 各モジュールで詳細な info/debug/warning ログを用意して運用時の可観測性を高めている。

### Known limitations
- strategy / execution / monitoring の実装（公開 API には含まれているものの、本リリースでの実装ファイルは一部に限定）。
- AI レイヤーは OpenAI API（gpt-4o-mini）を前提としているため、API 仕様変更・モデル差替え時に調整が必要。
- 一部の外部クライアント（J-Quants / kabuステーション）の振る舞いは jquants_client 等に依存しており、その実装に応じたエラーハンドリングが必要。

---

今後のリリースでは、strategy / execution / monitoring の具現化、性能改善、追加の品質チェック、自動テストカバレッジ拡充などを予定しています。