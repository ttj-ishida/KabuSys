# Changelog

すべての顕著な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このファイルは、コードベースの内容からの推測に基づいて作成しています。

ドキュメント日付: 2026-03-29

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-29

Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0
  - パッケージ公開インターフェース: kabusys.__init__ にて ["data", "strategy", "execution", "monitoring"] をエクスポート。

- 設定管理（kabusys.config）
  - .env / .env.local または環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない探索を実施。
    - 自動読み込みを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env ファイルの堅牢なパーサ実装（コメント・export キーワード・シングル/ダブルクォート・エスケープ処理対応、インラインコメント処理のルール適用）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティ（必須値は _require でチェックして ValueError を送出）。
    - env 値の検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
    - duckdb/sqlite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）を提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のウィンドウで raw_news を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON モードへバッチ送信（バッチサイズ 20）。
    - 1 銘柄あたりの最大記事数・文字数制限を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフリトライ。非再試行対象エラーはスキップして継続。
    - レスポンスの厳密バリデーションとパース復元ロジック（JSON の前後ノイズ除去）を実装し、安全にスコアを抽出。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへは部分置換（対象コードのみ DELETE → INSERT）を行い、部分失敗時に既存データを保護する設計。
    - API 呼び出し箇所（_call_openai_api）はテスト時に差し替え可能（unittest.mock.patch を想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）を計算し（look-ahead を避けるため target_date 未満のデータのみ使用）、マクロニュースの LLM センチメントと重み合成して市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、最大記事数制限、LLM 呼び出し（gpt-4o-mini）、JSON パースによる macro_sentiment 抽出。
    - LLM エラー時は macro_sentiment=0.0 のフォールバックを採用（フェイルセーフ）。
    - 最終結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時は ROLLBACK を試みた上で例外を上位に伝播。
    - news_nlp とは別実装の _call_openai_api を持ち、モジュール間でプライベート関数を共有しないことで結合度を下げる設計。

- データプラットフォーム（kabusys.data.*）
  - calendar_management
    - JPX カレンダーを扱うユーティリティを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定関数。
      - market_calendar テーブルを優先し、未登録日は曜日ベース（平日）でフォールバックする一貫した挙動。
      - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設け、無限ループを防止。
      - calendar_update_job により J-Quants API（jquants_client 経由）から差分取得・バックフィル・保存（ON CONFLICT 型の冪等保存）を行う。取得失敗や異常時は 0 を返して安全にスキップ。
  - pipeline / etl
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を実装し、取得／保存件数・品質チェック結果・エラー一覧を集約して to_dict で変換可能。
    - 差分更新、バックフィル、品質チェック（quality モジュールを参照）を想定した設計。ID トークンなどテスト用依存注入を考慮。
    - DuckDB のテーブル存在チェック・最大日付取得などユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート（kabusys.data.etl.ETLResult）。

- リサーチ / ファクター計算（kabusys.research.*）
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金（avg_turnover）・出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から直近財務データを取得して PER と ROE を計算（EPS 欠損や 0 の場合は PER を None）。
    - 全関数は DuckDB 接続を受け取り、外部 API に依存しない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンを一度のクエリで取得。ホライズンチェック（1〜252 日）あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。3 レコード未満で計算不能なら None。
    - rank / factor_summary: 平均・分散・中央値等の統計サマリとランク付けロジックを標準ライブラリのみで実装（pandas 等に非依存）。

- ロギング・堅牢化
  - 多くの箇所で詳細な logger 出力（info / warning / debug / exception）を行い、エラー時に安全にフォールバックする設計を採用。
  - DuckDB の executemany に対する互換性（空リスト禁止）への対処が実装されている箇所あり（ai.score_news など）。
  - 日時の取り扱いで look-ahead バイアスを排除（関数は datetime.today() / date.today() を直接参照しない設計が意図されている箇所多数、calendar_update_job のみ内部で today を使用している点に注意）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数未設定時は明示的に ValueError を送出する箇所があるため、運用時に必要なシークレット（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を適切に管理すること。

Notes / 実装上の注意（推測）
- OpenAI API 呼び出しは gpt-4o-mini と JSON Mode を使用する想定で実装されているため、利用時は対応する API キー／料金・利用制限を考慮してください。
- 多数の関数は testability を意識して設計されている（_call_openai_api を差し替え可能／API キー注入可能／DB は DuckDB 接続を注入）。
- カレンダー・ETL のジョブは J-Quants クライアント（kabusys.data.jquants_client）を利用するため、実行には該当クライアント実装と API 資格情報が必要。
- package.__all__ に含まれる "strategy", "execution", "monitoring" は __all__ で公開されているが、この差分で提供される実装は部分的である可能性がある（コードベース全体は継続的に拡張を想定）。

参考
- バージョン番号は kabusys.__version__ = "0.1.0" に基づく初期公開リリースの想定。