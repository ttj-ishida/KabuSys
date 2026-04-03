Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ の形式に準拠して記載しています。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 初回公開リリース: KabuSys v0.1.0
  - パッケージの概要: 日本株自動売買システムの基盤ライブラリ群を提供。
    - パッケージエントリポイント: kabusys（__all__ に data, strategy, execution, monitoring を公開）。
- 環境設定管理 (kabusys.config)
  - Settings クラスを追加。環境変数から各種設定を取得するプロパティを提供（J-Quants トークン、kabu API パスワード、LINE トークン、データベースパス、監視設定、しきい値、実行環境判定など）。
  - .env 自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサを実装。export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - 必須キー未設定時に ValueError を投げる _require ユーティリティ。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許可値チェック）と便宜プロパティ is_live / is_paper / is_dev。
- AI 関連 (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news の記事を集約して OpenAI（gpt-4o-mini, JSON Mode）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当）を calc_news_window で提供。
    - 銘柄ごとに記事を最新順で集約、記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチ処理（_BATCH_SIZE=20）、429/ネットワーク/タイムアウト/5xx を対象に指数バックオフによるリトライ実装。API失敗時はそのチャンクをスキップして継続（フェイルセーフ）。
    - OpenAI レスポンスの堅牢なバリデーション（JSON 抽出、results キー・型・スコア型チェック、未知コードは無視、スコアを ±1.0 へクリップ）。
    - DuckDB への書き込みは部分失敗に配慮し、対象コードのみ DELETE → INSERT（executemany）で置換。DuckDB の executemany 空リスト制約への対応あり。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルへ書き込む。
    - ma200_ratio 計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。データ不足時は中立（1.0）にフォールバックして警告ログ出力。
    - マクロニュースは raw_news からマクロキーワードで抽出し、LLM（gpt-4o-mini）で JSON 出力を期待して macro_sentiment を取得。APIエラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - レジームスコア合成後、閾値により 'bull' / 'neutral' / 'bear' を判定。DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理、失敗時は ROLLBACK。
    - OpenAI 呼び出しはリトライ・エラーハンドリング（RateLimitError 等）を備える。
- Data / ETL / カレンダー (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題やエラーの保持、to_dict メソッド等）。
    - 差分取得・保存・品質チェックを行う想定の設計（J-Quants クライアントを介した取得、backfill、部分失敗時の保護など）。
    - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティを含む（拡張ポイント）。
  - calendar_management
    - JPX マーケットカレンダーの夜間更新ロジック（calendar_update_job）を実装。J-Quants API から差分取得し market_calendar を冪等保存する。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。market_calendar が未取得でも曜日ベースのフォールバックを行い一貫性を保持。
    - lookahead・backfill・健全性チェックの実装（_CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
- Research (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。すべて DuckDB 上で SQL による計算を行い、(date, code) 単位の結果リストを返す。設計上、本番注文系 API へはアクセスしない。
    - Momentum: mom_1m / mom_3m / mom_6m, ma200_dev（データ不足時は None）。
    - Volatility / Liquidity: atr_20 / atr_pct / avg_turnover / volume_ratio（必要なデータが不足する場合は None）。
    - Value: PER, ROE を raw_financials の最新レコードから算出（EPS が 0/欠損の場合は None）。PBR / 配当利回りは未実装。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターンを計算）、calc_ic（スピアマンランク相関による IC 計算）、factor_summary（統計量算出）、rank（同順位平均ランク計算）を実装。pandas 等に依存せず標準ライブラリ+DuckDB で完結。
- モジュール再エクスポート
  - kabusys.data.etl が ETLResult を再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI / J-Quants の API キーは環境変数に依存。Settings が未設定の場合は ValueError を投げるため、秘密情報の取り扱いは利用者側で管理すること。

設計上の注意点・既知の制約
- ルックアヘッドバイアス回避: AI モジュール・リサーチモジュールは内部で datetime.today() / date.today() を参照せず、必ず引数で target_date を受ける設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は可能な限り処理を継続する（デフォルトスコア 0 やチャンクスキップ等）ことでパイプライン全体が停止しないよう設計。
- DuckDB 互換性: executemany に空リストを渡せないバージョンに対する保護ロジックを含む。
- 未実装点: 一部ファクター（PBR・配当利回り）や strategy / execution / monitoring の詳細実装は本バージョンでは含まれていない、あるいは public surface のみ（今後追加予定）。
- テスト容易性: OpenAI 呼び出し点は _call_openai_api のパッチ差し替えによりユニットテストでモック可能。

導入上のチェックリスト（利用前）
- 必要な環境変数を設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（または api_key 引数経由）、必要に応じて DB パスや LINE トークン等。
- プロジェクトルートに .env / .env.local を配置する場合は自動ロードの挙動を確認。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB に必要なスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を準備すること。

お問い合わせ・貢献
- バグ報告や機能要望はリポジトリの Issue にて受け付けてください。今後のバージョンで機能追加・改善を行う予定です。