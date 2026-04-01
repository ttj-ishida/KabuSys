# CHANGELOG

すべての重要な変更は Keep a Changelog の形式で記録します。  
初期リリースの内容はソースコードから推測して記載しています。

全般的なバージョニングは SemVer に従います。

## [Unreleased]
- 今後の変更予定や未確定の改善点を記載します。

## [0.1.0] - 2026-04-01
初回公開リリース。パッケージ名: kabusys（バージョン 0.1.0）。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - public API に data, strategy, execution, monitoring を想定したエクスポートを定義。

- 設定管理
  - 環境変数／.env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で探索して .env と .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export 形式、クォートやエスケープ、行末コメントなどに対応した .env パーサ実装。
    - 環境変数必須チェック用の _require() と Settings クラスを提供。
    - 設定項目（例）:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - PID_FILE_PATH（デフォルト: data/execution.pid）
      - CPU / Memory / Disk のしきい値（デフォルト値あり）
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データプラットフォーム（DuckDB ベース）
  - カレンダー管理モジュールを実装（src/kabusys/data/calendar_management.py）。
    - JPX カレンダーを保持する market_calendar テーブルを前提とした営業日判定 API を提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB データが不足する場合は曜日ベースのフォールバック（週末: 非営業）を採用。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存する夜間バッチ処理。
    - バックフィル、健全性チェック（将来日付の異常検出）などを実装。
  - ETL パイプラインのインターフェース（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分取得、保存（idempotent）、品質チェックを行う設計方針を反映。
    - jquants_client と quality モジュールを想定した連携ポイントを実装（呼び出し箇所、エラーハンドリングを含む）。
  - ETL 実装上の互換性配慮（DuckDB の executemany の空リスト制約等）を組み込み。

- AI（ニュースNLP・レジーム検出）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（内部は UTC naive datetime を使用）。
    - バッチ処理（最大 20 銘柄）、1 銘柄あたり記事数・文字数上限、JSON mode レスポンスのバリデーションなどを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。フェイルセーフで失敗時はスキップして継続。
    - レスポンス検証で不正な JSON や余計なテキストを復元・抽出するロジックを含む。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュースは raw_news からキーワードでフィルタし、OpenAI を用いて JSON 出力（{"macro_sentiment": ...}）で受け取る。
    - API リトライ、エラー時は macro_sentiment=0.0 のフォールバックを採用。
    - ルックアヘッドバイアス防止のため、当日データ参照を避ける設計（date 未満などの排他条件）。
  - AI モジュールはテスト容易性のため _call_openai_api を patch できる設計。

- リサーチ（因子・特徴量解析）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Value（PER/ROE）、Volatility（20日 ATR）および流動性指標の計算関数を実装。
    - DuckDB 内の prices_daily / raw_financials のみ参照する実装で外部発注なし。
    - データ不足時の None 扱い、戻り値は (date, code) を含む dict のリスト。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク化ユーティリティ（rank）、ファクターサマリ（factor_summary）を実装。
    - Spearman（ランク相関）を手動で算出する実装（外部ライブラリに依存しない）。
    - 入力検証（horizons の制約等）や欠損扱いを明示。

- 研究向けユーティリティの再エクスポート（src/kabusys/research/__init__.py）
  - 代表的な関数群を __all__ で公開。

- ロギング・互換性
  - 各モジュールで詳細なログ出力箇所を設置し、リトライやフォールバック時にログが残るように実装。
  - DuckDB の返り値処理（date 型など）に安全策を導入。

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー・その他機密情報は環境変数で管理する設計。
- .env 読み込みでは OS 環境変数を保護する protected ロジックを導入（.env.local の上書き制御含む）。
- 必須環境変数未設定時は明示的にエラーを発生させる（Settings._require）。

### Notes / 注意事項
- OpenAI 連携機能（news_nlp, regime_detector）は実行に OpenAI の API キー（OPENAI_API_KEY または関数引数）が必要です。未設定時は ValueError が発生します。
- J-Quants 連携は外部クライアント（jquants_client）が想定されています。実運用には当該クライアントの実装および有効な J-Quants トークンが必要です（JQUANTS_REFRESH_TOKEN）。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提です。データベースとテーブルが存在しない場合、多くの関数は None や空を返すか例外を投げます。
- 一部モジュール（例: src/kabusys/data/__init__.py が空）や、strategy / execution / monitoring の実装がパッケージエクスポートに含まれているものの本実装はこのリリース内に含まれていない可能性があります。実行前に各モジュールの存在と機能を確認してください。
- ルックアヘッドバイアス回避を目的に、日付参照は直接の現在時刻参照を避ける設計です（target_date を明示的に渡す設計）。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring の実装拡充（自動売買ロジック、発注ラッパ、監視ジョブ）。
- テスト・CI の追加、型注釈の完全化、パフォーマンス最適化。
- jquants_client 実装や DB スキーマ定義の付属ドキュメント化。

もし CHANGELOG の記載内容や形式で補足してほしい点があれば教えてください。