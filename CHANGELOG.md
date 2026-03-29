# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-29

Added
- パッケージ基本構成を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ で公開するサブパッケージ候補を定義（data, strategy, execution, monitoring）
- 環境・設定管理
  - 環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - .env / .env.local の読み込み順序と上書きルールを実装（.env.local が優先、OS 環境変数は保護）
  - export KEY=val 形式やクォート・コメント対応の行パーサ実装（エスケープ対応）
  - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供
    - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）
- Data（データ基盤）
  - calendar_management モジュール
    - JPX マーケットカレンダー管理（market_calendar テーブル参照/更新）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ
    - データ未取得時の曜日ベースのフォールバック、DB 値優先の一貫した挙動
    - 夜間バッチ job (calendar_update_job): J-Quants API から差分取得して冪等保存、バックフィル・健全性チェックを実装
  - pipeline モジュール（ETL）
    - ETLResult データクラスを公開（ETL 実行結果の集約）
    - 差分更新・バックフィル・品質チェックの設計に対応するユーティリティを実装
    - DuckDB を用いた最終取得日取得やテーブル存在チェック等のヘルパー
  - etl への公開インターフェース（ETLResult の再エクスポート）
  - jquants_client 経由での取得/保存操作を想定した設計（fetch/save の呼び出し点を確保）
- AI（NLP / LLM）
  - ai.news_nlp モジュール
    - raw_news / news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ保存
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）
    - チャンク処理（最大 20 銘柄／リクエスト）、1銘柄あたりの記事トリム（最大記事数・最大文字数）
    - JSON Mode を用いた厳密な JSON 出力期待、レスポンスのバリデーション実装（results 配列・code/score 検証、数値/有限値チェック）
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）、失敗時はスキップして継続するフェイルセーフ設計
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）
    - score_news(conn, target_date, api_key=None) を公開（書き込み済み銘柄数を返す）
  - ai.regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
    - マクロキーワードで raw_news をフィルタし、OpenAI でマクロセンチメント（-1.0〜1.0）を評価
    - レジームスコアはクリップ処理と閾値判定を実装、結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 呼び出し失敗時のフォールバック（macro_sentiment = 0.0）、リトライ・エラーハンドリングを備える
    - score_regime(conn, target_date, api_key=None) を公開
  - ai パッケージの公開インターフェースに score_news を含める
- Research（リサーチ / ファクター）
  - research パッケージ公開
    - factor_research モジュール
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を計算
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio 等を計算（ATR の NULL 伝播制御あり）
      - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（最新財務レコードの取得ロジックあり）
      - DuckDB 上での SQL + Python での計算、データ不足時は None を返す設計
    - feature_exploration モジュール
      - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得するクエリ実装
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算
      - rank: 同順位を平均ランクとして扱うランク変換ユーティリティ（丸めで ties 対策）
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算
    - data.stats の zscore_normalize を再エクスポートする形で研究ユーティリティを統合
- 実装上の設計・品質配慮
  - DuckDB を主要な分析データベースとして使用（duckdb.DuckDBPyConnection を引数で受け取る設計）
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today()/date.today() の安易な参照を避け、target_date に完全依存する実装
  - DB 書き込みは冪等性を確保（DELETE→INSERT や ON CONFLICT を想定）、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護
  - API 呼び出しは明示的なリトライとログ出力で堅牢化
  - テスト容易性のため内部 API 呼び出しポイントを差し替え可能に設計

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- OpenAI API キーなどの必須シークレットは環境変数経由で供給する設計。必須変数未設定時は明示的なエラーを発生させるヘルパーを提供。

Notes / 注意事項
- DuckDB のバインド挙動（executemany に空リストを渡せない等）への互換性考慮が実装に反映されています。DuckDB のバージョン互換性に注意してください。
- OpenAI SDK のエラー型（APIError の status_code 等）に対して互換的に扱うコードを含んでいますが、将来の SDK 変更では追加対応が必要になる可能性があります。
- 実行に必要な主要環境変数（例）:
  - OPENAI_API_KEY（AI 機能を使用する場合）
  - JQUANTS_REFRESH_TOKEN（データ取得）
  - KABU_API_PASSWORD（取引 API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（モニタリング通知）
- strategy、execution、monitoring パッケージは __all__ に記載されていますが、本リリースで実装済みなのは data / ai / research 周りの機能群です。今後のリリースで取引実行ロジックやモニタリング機能が追加予定です。