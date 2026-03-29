CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is released under Semantic Versioning.

[Unreleased]
------------

0.1.0 - 2026-03-29
------------------
Added
- 初回公開: kabusys パッケージのコア機能を実装。
  - パッケージメタ情報
    - __version__ = "0.1.0" を設定。
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義（監視モジュール等は将来追加想定）。
  - 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
      - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
      - 読み込み優先順: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
      - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
      - .env の読み込みで失敗した場合は警告（warnings.warn）を出力してスキップ。
    - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（J-Quants、kabu API、Slack、DB パス等）。
    - env / log_level の検証と is_live / is_paper / is_dev のユーティリティを提供。
  - AI モジュール (kabusys.ai)
    - ニュース NLP (kabusys.ai.news_nlp)
      - raw_news + news_symbols を集約して銘柄ごとにテキストを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得。
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
      - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大 10 記事・3000 文字にトリム。
      - 再試行/エラーハンドリング: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。その他エラーは安全にスキップ（フェイルセーフ）。
      - レスポンスの厳密なバリデーション実装（JSON 抽出、results 配列、code/score 検証、スコアの ±1.0 クリップ）。
      - 成功したスコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗で既存スコア保護）。
      - テスト差し替え用に _call_openai_api をモジュール内で分離。
    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）の合成で日次レジーム判定（bull/neutral/bear）。
      - prices_daily と raw_news を参照して ma200_ratio とマクロ記事タイトルを取得。
      - マクロキーワードによるフィルタリング（日本・米国等のキーワードリスト）。
      - OpenAI 呼び出しは gpt-4o-mini、JSON 出力を想定。API エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
      - レジームスコアは clip(-1..1) ししきい値でラベル付け。market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - API 呼び出し用関数をニュース NLP 実装と分離してモジュール結合を避ける設計。
  - データプラットフォーム (kabusys.data)
    - カレンダー管理 (kabusys.data.calendar_management)
      - JPX カレンダー取得・保存処理の支援関数と営業日判定ロジックを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - market_calendar が未取得の場合は曜日（平日）ベースでフォールバック。DB 登録値が存在する場合は DB 値優先。
      - next/prev_trading_day は最大探索範囲を制限（_MAX_SEARCH_DAYS = 60）して無限ループ回避。
      - 夜間更新ジョブ calendar_update_job 実装: J-Quants から差分取得し保存、バックフィルと健全性チェックを含む。
    - ETL パイプライン (kabusys.data.pipeline)
      - ETLResult dataclass を導入（取得件数、保存件数、品質チェック結果、エラー一覧などを格納）。
      - 差分更新ロジック、バックフィル、品質チェック方針を定義（実装のためのユーティリティ関数を提供）。
      - DuckDB 互換性を意識した実装（executemany の空リスト回避、日付型の扱い等）。
    - etl の公開インターフェース (kabusys.data.etl) で ETLResult を再エクスポート。
  - リサーチ (kabusys.research)
    - factor_research
      - Momentum / Volatility / Value / Liquidity 等のファクター計算を実装。
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。必要な行数未満は None を返す。
      - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算。EPS が 0 や欠損の場合は None。
      - 全関数は prices_daily / raw_financials のみ参照、外部 API にアクセスしない設計。
    - feature_exploration
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで計算（LEAD を使用）。
      - calc_ic: スピアマンのランク相関（IC）を実装。有効レコードが 3 未満の場合は None を返す。
      - factor_summary: count/mean/std/min/max/median を計算する統計ユーティリティ。
      - rank: 同順位は平均ランクを返す実装（丸めで ties 検出の安定化）。
  - 実装/設計上の注意点（共通）
    - ルックアヘッドバイアス防止: datetime.today()/date.today() をスコア計算ロジック内で直接参照しない設計（関数呼び出し側で target_date を与える）。
    - DuckDB をデータ層に採用。日付の変換ユーティリティや executemany の注意点を考慮した実装。
    - OpenAI 呼び出しのフェイルセーフ設計: API エラー時に処理を継続し安全側のデフォルト値（0.0）にフォールバック。
    - テスト容易性を考慮して、外部 API 呼び出しポイントを明示的に差し替え可能（_call_openai_api の patch 等）。
    - ロギングを多用し警告・情報・デバッグを出力。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを実装（.env の上書きを制御）。
- OpenAI API キーは引数で注入可能。未設定時は ValueError を送出して明示的に扱う。

Notes / 運用上の補足
- OpenAI モデル: gpt-4o-mini（JSON mode）を想定。API レスポンスの形式に依存するため、実運用では返信形式の監視が必要です。
- DuckDB を前提としているため、ETL や解析処理は DuckDB のテーブル構成（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime 等）に依存します。
- .env パーサは柔軟に実装しているが、特殊ケースのパース挙動（コメントの判定ルール等）に注意してください。

今後の予定（例）
- monitoring / execution / strategy モジュールの実装と統合テスト。
- ai モジュールのカバレッジ向上・モデル切替対応・レート制限対策強化。
- ETL のスケジューリング・監査ログ機能・品質チェックの詳細実装と UI/ダッシュボード連携。