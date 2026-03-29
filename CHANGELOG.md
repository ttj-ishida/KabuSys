# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣例に従って記載しています。

最新の変更は Unreleased に記載します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初回リリース。以下の機能と実装方針をコードベースから推測してまとめます。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ による公開モジュール: data, strategy, execution, monitoring（パッケージ境界のエクスポート）

- 環境変数 / 設定管理 (`kabusys.config`)
  - .env ファイル（プロジェクトルートの .env / .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどを考慮。
  - OS 環境変数を保護するための protected 上書き制御や .env.local による上書き優先度を実装。
  - Settings クラスを提供し、必須変数のチェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）、デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH）、検証（KABUSYS_ENV、LOG_LEVEL）と便利プロパティ（is_live/is_paper/is_dev）を実装。

- ニュースNLP（AI） (`kabusys.ai.news_nlp`)
  - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行う calc_news_window を提供。
  - バッチ処理（1回の API コールあたり最大 20 銘柄）、1銘柄あたりの最大記事数・文字数制限（記事トリム）を実装。
  - OpenAI 呼び出しは JSON Mode を使い、応答のバリデーション（JSON パース、results の構造チェック、未知コード無視、数値チェック）を厳密に行う。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装し、API 失敗時はそのチャンクをスキップして他の処理を継続（フェイルセーフ）。
  - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

- 市場レジーム判定（AI） (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存する score_regime を実装。
  - prices_daily からの MA200 乖離計算、raw_news からマクロキーワードフィルタ、OpenAI への問い合わせ、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
  - API エラーやパース失敗時は macro_sentiment を 0.0 にフォールバックする設計（サービス継続性の確保）。
  - OpenAI 呼び出しは news_nlp とは独立した実装とし、モジュール結合を避ける設計。

- リサーチ（因子計算・特徴探索） (`kabusys.research`)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を prices_daily から計算。
    - calc_volatility: 20 日 ATR, ATR の相対値（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の最新財務情報と prices_daily を組み合わせて PER・ROE を算出。
    - DuckDB のウィンドウ関数を活用した実装で、データ不足時の None ハンドリングを行う。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を実装（最低 3 レコード要件）。
    - rank, factor_summary: ランキングと統計サマリーを純粋 Python（外部依存なし）で提供。
  - research パッケージは便利関数を再エクスポート（zscore_normalize 等）。

- データプラットフォーム用ユーティリティ (`kabusys.data`)
  - calendar_management:
    - market_calendar を参照して営業日判定（is_trading_day/is_sq_day）、前後営業日の検索（next_trading_day/prev_trading_day）、期間内営業日列挙（get_trading_days）を提供。
    - DB に情報が無い場合は曜日ベース（土日非営業日）でフォールバックする一貫した動作仕様。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィル・健全性チェックを実装。
  - pipeline:
    - ETLResult dataclass を導入し、ETL のフェッチ/保存/品質チェックの結果とエラー情報を構造化して返却。
    - 差分更新、backfill、品質チェック（quality モジュール）連携、ID トークン注入でのテスト容易性など ETL 設計方針を反映。
  - etl: pipeline.ETLResult を再エクスポート。

- DuckDB を中心に DB 操作を実装
  - 全モジュールで DuckDB 接続（DuckDBPyConnection）を引数に取り、安全な SQL と Python 処理を組み合わせる設計。
  - executemany の空パラメータ回避など DuckDB バージョン固有の注意点に配慮した実装。

### Changed
- N/A（初回リリースのため既存からの変更はありません。ただし各モジュールに設計上の注意点・フェイルセーフを多数導入しています。）

### Fixed
- N/A（初回リリース）

### Security
- API キーは引数注入か環境変数（OPENAI_API_KEY）で解決。未設定時は ValueError を送出し明示的に扱うように実装。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（.env ファイルによる意図しない上書きを防止）。

### Implementation / Design Notes（実装上の重要ポイント）
- ルックアヘッドバイアス防止: 全ての時間関連処理（ニュースウィンドウ、MA 計算、ETL ターゲット日）は datetime.today()/date.today() に依存せず、明示的な target_date を受け取る設計。
- 冪等性: DB 書き込みは DELETE→INSERT や ON CONFLICT（jquants_client 側）等で冪等となるよう配慮。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時に処理全体が停止しないよう、フォールバック値（0.0）やチャンクスキップ等で継続する設計。
- テスト容易性: OpenAI 呼び出し箇所（各モジュールの _call_openai_api）を patch で差し替えられるように実装。
- ロギング: 重要な経過や警告（データ不足、API 再試行、ロールバック失敗等）は logger を通じて出力される。
- DuckDB の互換性配慮: executemany に空リストを渡さない、日付型変換ユーティリティを設置する等の実装上の細かい互換性対応を行っている。

---

（注）
- 本 CHANGELOG は提示されたソースコードの内容から推測してまとめたもので、実際のリリースノートや履歴を置換するものではありません。具体的な変更日付や担当者、チケット番号などのメタ情報はソース管理履歴（Git）に基づいて追記してください。