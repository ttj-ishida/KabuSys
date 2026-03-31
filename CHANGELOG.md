CHANGELOG
=========

全般
-----
この CHANGELOG は「Keep a Changelog」方式に準拠しています。  
リリースノートは、コードベースから実装内容・設計方針を推測して作成しています。

フォーマット:
- Unreleased: 開発中の変更（現時点では空）
- 各リリースは日付付きで記述

Unreleased
----------
（なし）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ基盤
  - パッケージ名 kabusys を初期実装。バージョン __version__ = "0.1.0" を定義。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 環境・設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート探索は __file__ から親ディレクトリを上向きに探索し .git または pyproject.toml を基準に特定（CWD に依存しない挙動）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いを考慮。
  - Settings クラスを提供し、以下の設定値をプロパティで取得・検証:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（許容値: development, paper_trading, live。検証あり）
    - LOG_LEVEL（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL。検証あり）
  - 必須環境変数未設定時は ValueError を送出する _require 関数を提供。

- データ / ETL 基盤 (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを実装（ETL 実行結果の構造・シリアライズ用 to_dict を含む）。
  - テーブル存在チェック、最大日付取得などのユーティリティを実装。
  - ETL の設計方針・ロジック（差分更新、バックフィル、品質チェック方針）をコード内ドキュメントで明示。
  - ETLResult を kabusys.data.etl で再エクスポート。

- カレンダー管理 (kabusys.data.calendar_management)
  - JPX 市場カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar テーブルが存在しない場合は曜日ベース（土日休）でフォールバックする一貫した挙動。
    - 最大探索範囲を設定して infinite loop を防止。
  - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新するバッチ処理を実装。
    - バックフィル期間、先読み日数、健全性チェック（将来日付の異常検出）を備える。
  - jquants_client（外部モジュール）経由での取得・保存処理を想定（fetch_market_calendar / save_market_calendar を呼び出す）。

- AI 系機能 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込む。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST を採用（UTC 変換済み）。
    - 銘柄ごとに最新記事を最大 _MAX_ARTICLES_PER_STOCK 件、文字数でトリムしてプロンプトに含める。
    - バッチサイズ（1 API 呼び出しで最大銘柄数）= 20。
    - API 呼び出しは JSON mode を利用し、429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密バリデーションを実装（results 配列、code と score の型チェック、未知コードの無視、数値型の検証、±1.0 のクリップ）。
    - DuckDB の executemany の制約を考慮し、部分成功時に既存スコアを保護するためコードで絞って DELETE → INSERT を行う。
    - API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。
    - 外部へのテスト容易性を考え、OpenAI 呼び出し関数はモジュール内で差し替え可能（ユニットテスト用に patch できる）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の market_regime テーブルへ冪等書き込みを行う。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド回避）。データ不足時は中立値 1.0 を使用。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウを計算し、raw_news からキーワードに合致するタイトル（最大 20 件）を取得して LLM に投げる。
    - OpenAI 呼び出しはリトライと例外ハンドリングを実装し、API 失敗時は macro_sentiment=0.0 でフォールバック（例外は投げない）。
    - 最終的な regime_score を閾値で判定して regime_label を決定（'bull' / 'neutral' / 'bear'）し、market_regime に INSERT（冪等処理）する。
    - API キーの注入可能性・未設定時のエラー挙動は news_nlp と同様。

- リサーチモジュール (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility(conn, target_date): 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。部分窓での算出ルール、NULL 伝播制御を実装。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER（EPS 有効時）と ROE を計算。target_date 以前の最新報告データを取得する実装。
    - すべて DuckDB の SQL を活用して計算し、(date, code) ベースの dict リストで結果を返す。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 任意ホライズンの将来リターンを一括で取得するためのクエリ生成を実装（horizons は 1..252 で検証）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank(values): 平均ランク（同順位は平均ランク）を返すユーティリティ（丸め誤差対策あり）。
    - factor_summary(records, columns): 各カラムの count/mean/std/min/max/median を計算する統計サマリー機能。
  - zscore_normalize は kabusys.data.stats から再エクスポートされることを想定（__init__ に記載）。

Design / Safety / テスト配慮
- ルックアヘッドバイアス防止のため、どのモジュールも datetime.today()/date.today() を内部で参照しないことを明記（target_date を呼び出し側が指定する設計）。
- OpenAI 呼び出しはリトライ & フェイルセーフ（多くのケースで 0.0 や空スコアで続行）を実装し、外部フォールバックで全体処理を停止させない方針。
- DuckDB のバージョン差異（executemany の空リスト制約、配列バインドの不安定さ等）に配慮した実装を行っている。
- 単体テスト容易性のため、OpenAI 呼び出しや時間依存処理の差し替えが可能な設計（関数をモジュールスコープで定義して patch 可能）。

Notes / Requirements / TODO（リリースノートに明示）
- OpenAI API（gpt-4o-mini）を利用する機能（score_news, score_regime）は API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を投げる。
- J-Quants 関連クライアント（jquants_client）は外部モジュールとして参照されているため、実際の運用には該当クライアント実装が必要。
- strategy, execution, monitoring モジュールは __all__ に含まれているが、本リリースに該当コードが含まれていないか（または別ファイルに実装予定）ため、これらを結合する追加実装やドキュメント整備が今後の作業になる可能性がある。
- 本 CHANGELOG はコードベースからの推測に基づくため、実際の設計意図・外部依存のバージョン等に差異がある場合があります。

転載は禁止事項
- このリリースは初期実装のため、エッジケースや大規模データでのパフォーマンスチューニング、運用監視（監査ログ・メトリクス・アラート）などは別途整備が必要です。