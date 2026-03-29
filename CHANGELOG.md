# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの実装内容から推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ初期化
  - kabusys パッケージを作成。__version__ = 0.1.0、主要サブパッケージを公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を追加。
  - OS 環境変数を保護する protected モード、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - .env パースで export プレフィックス、クォート文字列、エスケープ、インラインコメント等に対応する堅牢なパーサを実装。
  - 必須環境変数取得ヘルパ（_require）、env/log_level 等の値検証（許容値チェック）を提供。
  - データベースパスの既定値（DuckDB/SQLite）や Slack / Kabu / J-Quants 関連設定プロパティを実装。

- データプラットフォーム（data）
  - calendar_management: JPX カレンダー管理・営業日判定ロジックを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のユーティリティ。
    - market_calendar が未取得のときは曜日ベースでフォールバックする堅牢な挙動。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）。
  - pipeline: ETL パイプラインの基礎実装（差分取得・保存・品質チェック統合を想定）。
  - etl: ETLResult を公開するインターフェース（ETL 実行結果の構造体を提供）。
  - DuckDB を前提としたテーブル存在チェックや最大日付取得などのユーティリティを実装。

- 研究モジュール（research）
  - factor_research: ファクター計算（モメンタム / バリュー / ボラティリティ）を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_value: raw_financials から EPS / ROE を取得して PER / ROE を計算（未定義時の扱いを明示）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
  - feature_exploration: 将来リターン計算・IC（スピアマンランク相関）・統計サマリー等を実装。
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得する実装。
    - calc_ic: factor と forward return を code で結合してスピアマン ρ を算出（有効レコード閾値あり）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）・基本統計量集計の実装。
  - research パッケージのユーティリティをエクスポート（zscore_normalize など外部モジュールとの連携想定）。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュースを銘柄毎に集約して OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）。
    - 1 銘柄あたり記事数・文字数の上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) によるトリム。
    - バッチ処理（最大 _BATCH_SIZE 銘柄/リクエスト）、JSON Mode を使ったレスポンス検証。
    - 429 / ネットワーク断 / timeout / 5xx に対する指数バックオフによるリトライ。
    - レスポンス検証で未知コードの無視、数値変換、クリップ（±1.0）など堅牢なバリデーション。
    - DuckDB の executemany における空リスト制約を回避するための保護ロジック。
    - API 呼び出し部はモックしやすい設計（_call_openai_api を patch 可能）。
  - regime_detector: ETF(1321) の 200 日 MA 乖離 (70%) とマクロセンチメント (30%) を合成して日次市場レジーム判定（bull/neutral/bear）を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッド防止）。
    - マクロキーワードで raw_news をフィルタして LLM でセンチメント算出。
    - LLM 呼び出しは独立実装でモジュール結合を避ける設計。
    - API 障害時は macro_sentiment=0.0 にフォールバックし処理を継続（フェイルセーフ）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

### Changed
- 設計上の方針を明文化（コード内ドキュメント）
  - すべての「日付基準処理」は datetime.today()/date.today() を直接参照しない設計でルックアヘッドバイアスを回避。
  - DuckDB を前提とする SQL 実装で互換性・堅牢性を考慮した実装（ROW_NUMBER, ウィンドウ関数活用）。

### Fixed / Robustness
- 環境変数読み込みの堅牢化
  - .env のパースで引用符・エスケープ・コメント処理の不整合を防止。
  - .env.local を .env より優先して上書き（ただし OS 環境変数は保護）。
- OpenAI API 呼び出し周りの堅牢化
  - リトライ/バックオフ、5xx 判定、非致命的失敗のログ化とフェイルセーフ（ゼロスコア）を導入。
  - JSON レスポンスの「余分なテキスト」対策として最外の {} を抽出して再パースを試行。

### Security
- 秘密情報の直接露出防止
  - Settings は環境変数経由で API キー等を取得する設計。必須変数未設定時は明確なエラーメッセージを投げる。

### Notes / Implementation details
- DuckDB を主要な分析 DB として使用。各分析・ETL コンポーネントは DuckDB 接続を受け取る設計。
- ai モジュールは JSON Mode を利用して構造化レスポンスを期待するが、レスポンス不整合に備えた堅牢なサニタイズ/検証処理を行う。
- テスト容易性を考慮し、外部 API 呼び出し部（_call_openai_api 等）をパッチ差し替えできるようにしている。
- ETL の結果表現（ETLResult）を提供し、品質チェック結果（quality.QualityIssue 相当）を含めて監査可能な形で保持。

---

今後の想定追加項目（例）
- ai スコアリングの多言語対応やモデル切替オプション
- ETL の差分・並列化最適化、より詳細な品質チェックルール
- モニタリング／アラート統合（Slack 通知等）の具体化

（この CHANGELOG はコード内容からの推測に基づくため、実際のリリースノートと差異がある可能性があります。）