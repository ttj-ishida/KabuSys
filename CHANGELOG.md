# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

- 今後の改善予定（例）
  - OpenAI 呼び出しのテスト用モック抽象化の強化
  - jquants_client のエラーハンドリング強化
  - execution / monitoring モジュールの公開 API ドキュメント整備

---

## [0.1.0] - 2026-04-02

Initial release — KabuSys の最初の公開バージョン。日本株自動売買システムを構成するコア機能群を実装しました。主な追加点は以下のとおりです。

### Added

- パッケージ基盤
  - パッケージ version を `0.1.0` として公開（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, research, ai, monitoring, execution, strategy（__all__ で定義）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git もしくは pyproject.toml を基準に探索）。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - .env.local が .env を上書き（override）する読み込み順を採用。OS 環境変数は保護され、上書きされない。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - Settings クラスを提供し、主要設定値をプロパティで取得（J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 環境モード / ログレベル等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須キー取得ヘルパ `_require`。

- AI（自然言語処理）機能（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価。
    - タイムウィンドウ計算（JST ベース → DB 比較は UTC naive datetime）を提供する calc_news_window。
    - API バッチ処理（1 回あたり最大 20 銘柄）・記事/文字数トリム（最大記事数／最大文字数制限）。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、5xx とそれ以外の扱いの分離。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト・code/score 検証、スコアの有限性チェック、±1.0 クリップ）。
    - DuckDB への書き込みは部分置換（DELETE → INSERT）で冪等性を確保。DuckDB executemany の空リスト制約に配慮。
    - テスト容易性のため OpenAI 呼び出し箇所は patch で差し替え可能（内部関数 _call_openai_api を想定）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満データのみ使用）。データ不足時は中立値を採用。
    - マクロニュース抽出（キーワードベース）と LLM スコア化（gpt-4o-mini、JSON mode）。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコア合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI API 呼び出しは再試行・エラーハンドリングを備える。テスト用に差し替え可能に設計。

- データプラットフォーム / ETL（src/kabusys/data）
  - pipeline モジュール（src/kabusys/data/pipeline.py）
    - ETL 処理の骨格を実装。差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュール）を想定。
    - ETLResult データクラスを公開（src/kabusys/data/etl.py から再エクスポート）。品質問題・エラーの集約、has_errors / has_quality_errors プロパティを提供。
    - DuckDB 接続の存在チェックや最大日付取得等のユーティリティを実装（DuckDB の互換性に配慮）。
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - JPX 市場カレンダー管理（market_calendar テーブル）を実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新。バックフィル・先読みの考慮、健全性チェック（将来日付の異常検知）あり。
    - DB にデータがない場合の曜日ベースフォールバックを提供し、DB がまばらな場合でも一貫した判定を行う設計。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）等のファクター計算を実装。
    - DuckDB SQL を用いた集計実装。データ不足時は None を返す等の堅牢設計。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで実装。ランクは同順位の平均ランク処理、スピアマン ρ（ランクの Pearson）算出を実装。
  - data.stats の zscore_normalize を再エクスポートする仕組みを追加。

### Changed

- 設計方針・安全対策（各モジュール内に明示）
  - ルックアヘッドバイアスを避けるため、datetime.today() / date.today() を判定ロジックの中心に用いない実装方針を採用（target_date を明示的に受け取る）。
  - OpenAI 呼び出しの失敗はフェイルセーフ（0.0 などの中立値）で継続するように実装し、例外により全体が停止しない設計。
  - DuckDB の実装差異（executemany の空配列禁止など）に配慮した実装。

### Fixed

- 初期実装の安定化に向けた注意点の対策
  - .env パーサ: export プレフィックス・クォート中のバックスラッシュエスケープ・コメントの扱いなど様々な .env 書式に対応。
  - OpenAI レスポンスの JSON 抽出ロバスト化（JSON 部分抽出 / パース失敗時のログ出力とスキップ）。

### Security

- 現バージョンでは外部機密情報（API キー等）は環境変数に依存。
  - OpenAI API の利用: 関数に api_key を注入可能（テスト/運用の両対応）。環境変数名: OPENAI_API_KEY。
  - 設定取得時に未設定の必須キーは明示的な ValueError を上げるため、運用時の見落としを早期に検出可能。

### Known limitations / Notes

- AI 機能は OpenAI SDK（gpt-4o-mini）への依存があるため、利用には OPENAI_API_KEY の設定が必要。未設定時は ValueError を送出。
- jquants_client（DataPlatform の API クライアント）は参照されるが、この CHANGELOG 対象コードに同モジュールの詳細実装は含まれていない可能性があります（外部依存）。
- execution / monitoring / strategy モジュールの具体的な発注ロジック・運用監視ルーチンは本バージョンのコードベースでのインターフェース実装に留まる場合があります（実際の発注は安全対策が必要）。
- タイムゾーンは設計上 UTC naive datetime を DB 比較に使用（calc_news_window 等）。運用時は DB に格納される日時の扱いに注意してください。
- DuckDB に関するバージョン差異に注意（executemany 空配列の扱い等）。本実装は互換性を考慮した保護を追加。

### Migration / Upgrade notes

- 既存環境から導入する場合は以下の環境変数を確認してください（主要な必須項目）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI 機能を使う場合）
  - DUCKDB_PATH / SQLITE_PATH（デフォルトが data/ 以下に設定されています）
- 自動 .env 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

---

今後のリリースでは、テストカバレッジの拡充、モデル選択の抽象化、外部クライアント（jquants / kabu）の堅牢化を優先していく予定です。ご要望や不具合報告は issue を通じてお知らせください。