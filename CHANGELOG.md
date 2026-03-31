# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

タグ付けの方針:
- これはリポジトリ初回リリース（0.1.0）に相当する変更点一覧です。

## [0.1.0] - 2026-03-31

### Added
- パッケージ基礎
  - kabusys パッケージの初期実装。バージョンは 0.1.0。
  - パッケージ公開 API（__all__）として data, strategy, execution, monitoring を宣言。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数を扱う設定ローダーを実装。
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。
    - export プレフィックスやクォート、インラインコメント等を考慮した .env パース処理を実装。
    - .env.local は既存 OS 環境変数を保護しつつ上書き可能（override=True, protected set）。
  - Settings クラスを提供し、環境変数の必須チェック（_require）や型変換を encapsulate。
    - 主な設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）。
    - KABUSYS_ENV の許容値検証（development/paper_trading/live）や LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- データ層（kabusys.data）
  - ETL 用インターフェースの公開（ETLResult の再エクスポート）。
  - ETL パイプライン基盤（kabusys.data.pipeline）を実装。
    - ETLResult dataclass（処理統計・品質問題・エラー集約、辞書変換 to_dict）。
    - 差分取得のための最終日取得ユーティリティ、テーブル存在確認。
    - backfill・カレンダー先読み・品質チェック連携の設計を組み込んだ基盤実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ロジック群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録あり → DB 優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新するバッチ処理（バックフィル、健全性チェックを実装）。
    - 最大探索範囲（_MAX_SEARCH_DAYS）、先読み日数、バックフィル日数などの安全パラメータを定義。

- 研究（research）モジュール（kabusys.research）
  - ファクター計算・特徴量探索の初期機能を実装・公開:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials から直近財務を取得して PER/ROE を計算（EPS=0/欠損 は None）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）計算。データ不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めによる ties の安定化）。
  - 実装上の配慮: DuckDB を用いた SQL と純標準ライブラリのみで実装。外部 I/O（API・発注）にはアクセスしない。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - calc_news_window: ニュース収集ウィンドウ（JST基準の前日15:00〜当日08:30）を UTC naive datetime で計算。
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得、ai_scores テーブルへ書き込み。
      - 1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - バッチサイズ (_BATCH_SIZE=20)、JSON Mode を利用した厳密な JSON 出力要求（レスポンスバリデーションあり）。
      - リトライ戦略: 429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフで再試行。
      - レスポンス検証: JSON パース、results 配列の検査、コードの正規化、数値チェック、スコアの ±1.0 クリップ。
      - DB 書き込みは冪等的に実施（対象コードのみ DELETE → INSERT）し、部分失敗時に他コードの既存スコアを保護。
      - テストしやすさのため _call_openai_api を patch 可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - score_regime: ma200_ratio 計算、マクロニュース抽出（キーワードフィルタ）、OpenAI で macro_sentiment を算出、合成スコアを market_regime テーブルへ冪等書き込み。
    - 設計上の配慮:
      - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない。prices_daily のクエリは target_date 未満のみを使用。
      - OpenAI 呼び出し失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
      - API 呼び出し用のリトライ処理と 5xx の扱いを実装。
    - プロンプトは JSON のみを出力するよう設計（_SYSTEM_PROMPT）。

- 例外処理・ログ・堅牢性
  - DuckDB の executemany での空リスト問題を意識した実装。
  - 各種関数で安全なフォールバック（データ不足時の中立値、API 失敗時の 0.0、NULL 値警告ログ等）を導入。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で行い、例外時は ROLLBACK を試行してから例外を再送出。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes
- OpenAI SDK 依存:
  - gpt-4o-mini を想定した Chat Completions（JSON Mode）での利用を前提としているため、実際の SDK バージョンや API 仕様差異により調整が必要な箇所がある点に留意してください。
- DB スキーマ:
  - 本コードは prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等のテーブル構造存在を前提としています。実行前にスキーマ整備が必要です。
- テスト容易性:
  - OpenAI コール部分は内部で _call_openai_api を経由するため、ユニットテスト時に patch して外部依存を切り離せます。
- セキュリティ／運用:
  - 自動で .env を読み込む処理が入るため、本番デプロイ時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用するか、環境設定に注意してください。

---

保守的な設計（フェイルセーフ、ルックアヘッドバイアス回避、冪等書き込み、詳細なログ出力）を優先して実装した初期版です。今後のリリースではテストカバレッジの拡充、API 互換性レイヤー、schema migration ユーティリティ、パフォーマンス最適化等を追加予定です。