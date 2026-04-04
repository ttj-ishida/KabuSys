# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

全般
- 初期リリース 0.1.0。パッケージは日本株のデータ取得・ETL、研究（ファクター解析）、AI を用いたニュースセンチメント判定、及び実行／監視関連の基盤機能を提供します。
- 依存主要コンポーネント: DuckDB（データ格納・問い合わせ）、OpenAI（gpt-4o-mini を利用する JSON Mode 呼び出し）。

[0.1.0] - 2026-04-04
Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。
- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export プレフィックス、クォート内のエスケープ、行内コメント処理などに対応）。
  - 環境変数保護機能（OS 環境変数を protected として .env.local による上書きを制御）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取り出せるようにした（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、データベースパス、監視設定、閾値、実行環境判定など）。
  - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）および LOG_LEVEL の検証を実装。
  - 必須環境変数未設定時に _require が ValueError を送出。
- AI: ニュースNLP (kabusys.ai.news_nlp)
  - score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols テーブルから前日15:00 JST〜当日08:30 JST に相当する記事を銘柄毎に集約し、OpenAI の gpt-4o-mini JSON モードでセンチメントスコアを取得。
    - バッチ処理（最大 20 銘柄／コール）、1銘柄あたり記事数・文字数のトリム制御（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションとスコアクリッピング（±1.0）。不正レスポンスは無害化して次へ進める。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易化のため _call_openai_api を patch 可能に実装。
  - calc_news_window(target_date): JST→UTC のウィンドウ計算ユーティリティを公開。
- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の直近200日移動平均乖離（ma200_ratio）と、マクロニュースの LLM センチメントを重み付け（70% / 30%）して日次の市場レジームスコアを算出（clip と閾値判定で bull / neutral / bear を決定）。
    - raw_news からマクロキーワードで抽出したタイトルを gpt-4o-mini に送り JSON パースして macro_sentiment を取得。記事が無ければ LLM 呼び出しをスキップして 0.0 を採用。
    - API 呼び出しのリトライ・エラーハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError の 5xx 判定）とフェイルセーフ（失敗時は 0.0）。
    - market_regime テーブルへの冪等書き込みを実装（BEGIN / DELETE / INSERT / COMMIT、エラー時に ROLLBACK を試行）。
    - LLM 呼び出し関数は news_nlp とは独立した実装でモジュール結合を避ける。
- データ: カレンダー管理 (kabusys.data.calendar_management)
  - JPX 市場カレンダー操作ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - market_calendar が未整備の場合は曜日ベース（土日除外）のフォールバックを採用し、一貫した結果を返す設計。
  - calendar_update_job(conn, lookahead_days=90)
    - J-Quants クライアント経由で差分取得 → 保存（fetch / save）する夜間ジョブを実装。
    - バックフィル（直近 _BACKFILL_DAYS の再取得）、健全性チェック（極端に未来の日付はスキップ）を実装。
- データ: ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult dataclass を公開（取得数・保存数・品質問題・エラーの集約、has_errors / has_quality_errors / to_dict）。
  - 差分更新・バックフィル・品質チェックの方針を反映した ETL の土台を実装（jquants_client と quality モジュール経由での取得・保存・検査を想定）。
  - テーブル存在チェック・最大日付取得ユーティリティなど内部ユーティリティを実装。
- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200_dev（200日MA乖離）を計算。
    - calc_volatility(conn, target_date): 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせ PER / ROE を計算（EPSが0/欠損時は None）。
    - いずれも DuckDB SQL を多数使いデータ窓をスキャンする実装。データ不足時は None を返す設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト: 1,5,21 営業日）を計算。horizons のバリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank(values): 同順位は平均ランクに変換するユーティリティ（丸めで ties の検出精度向上）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリ。

Changed
- （該当なし）初回リリースのため既存振る舞いの「変更」はなし。

Fixed
- （該当なし）初回リリース。

Security
- OpenAI API キーは api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照する。必須未設定の場合は ValueError を送出することで誤操作を防止。

Notes / 設計方針のハイライト
- ルックアヘッドバイアス防止: 全ての処理で datetime.today() / date.today() を直接参照せず、target_date ベースで処理するよう設計。
- フェイルセーフ: OpenAI 等外部APIの障害時に処理を中断させず、合理的なデフォルト（例: macro_sentiment=0.0）で継続する方針。
- DB 書き込みは冪等化や部分失敗時の保護（対象コードに限定した DELETE → INSERT）に配慮。
- テスト容易性: OpenAI 呼び出し箇所を patch 可能な関数として抽象化。
- 外部依存は最小限（標準ライブラリ + duckdb + openai）を想定。

Breaking Changes
- （該当なし）初回リリース。

Future / TODO（非網羅）
- PBR・配当利回りなど Value ファクター拡張
- strategy / execution / monitoring サブパッケージの具体的実装とドキュメント拡充
- より詳細な品質チェックルールの追加
- OpenAI 呼び出しのトークン使用量制御やコスト最適化

--- 
開発者向け補足:
- 主要な公開 API:
  - kabusys.config.settings
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime
  - kabusys.data.pipeline.ETLResult
  - kabusys.data.calendar_management.{is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job}
  - kabusys.research.{calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank}
- 本 CHANGELOG はコードベースの現状（ソース解析に基づく）を要約したものであり、リリースパッケージ化時に正式なリリースノートとして補足することを推奨します。