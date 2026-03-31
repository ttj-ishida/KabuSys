CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に従います。
このプロジェクトはセマンティック バージョニングを採用しています。

Unreleased
----------

（現在の開発中の変更はここに記載してください）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ: src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ エクスポートを追加。

- 環境変数・設定管理
  - kabusys.config に Settings クラスを実装。
    - .env ファイル（プロジェクトルートの .env および .env.local）を自動読み込み（OS 環境変数優先、.env.local は上書き）。
    - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルのパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントルールをサポートする堅牢な実装。
    - 環境変数の保護（既存 OS 環境変数を protected として上書き防止）を実装。
    - 必須変数取得時に _require による明示的な ValueError を送出。
    - 設定項目:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（許容: development, paper_trading, live、検証あり）
      - LOG_LEVEL（許容: DEBUG, INFO, WARNING, ERROR, CRITICAL、検証あり）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- AI 関連（自然言語処理）
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を基に銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ保存する機能を実装。
    - 処理のポイント:
      - ニュース収集ウィンドウの計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window として提供。
      - 1 銘柄あたり最大記事数 (_MAX_ARTICLES_PER_STOCK = 10) と文字数上限 (_MAX_CHARS_PER_STOCK = 3000) を設けてトークン肥大化を抑制。
      - バッチ処理（_BATCH_SIZE = 20 銘柄）で OpenAI JSON mode を利用。
      - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ（最大リトライ回数 _MAX_RETRIES）。
      - レスポンスのバリデーションを厳密に実施（JSON 抽出、"results" 配列、code と score 検証、数値性チェック、既知コードのみ採用、スコアを ±1.0 にクリップ）。
      - 書き込みは冪等に行う（対象コードのみ DELETE → INSERT）。DuckDB の executemany の制約を考慮して空リストチェックを行う。
      - API キーの注入（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
      - テスト用に OpenAI 呼び出しは _call_openai_api を通す設計（patch 可能）。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する機能を実装。
    - 処理のポイント:
      - _calc_ma200_ratio: target_date 未満のみを使いルックアヘッドを防止。データ不足時は中立（1.0）を返す。
      - マクロニュースは kabusys.ai.news_nlp.calc_news_window を用いてウィンドウ抽出し、マクロキーワードでフィルタしたタイトルを最大 _MAX_MACRO_ARTICLES 件取得。
      - OpenAI 呼び出しは独立実装（news_nlp と共有しない）で、JSON mode を利用しリトライ/フェイルセーフ（API 失敗時に macro_sentiment = 0.0）を行う。
      - レジームスコアは clip して閾値でラベル付けし、DB への書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作で保存。失敗時は ROLLBACK を保証しエラーを伝播。

- Research（ファクター計算・特徴量探索）
  - kabusys.research パッケージに以下を提供:
    - factor_research.calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - factor_research.calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - factor_research.calc_value: raw_financials から最新財務を参照して PER、ROE を計算（EPS が欠損/0 の場合は None）。
    - feature_exploration.calc_forward_returns: 将来リターン（デフォルト: 1, 5, 21 営業日）を計算。horizons の検証（正整数かつ <= 252）。
    - feature_exploration.calc_ic: スピアマンのランク相関（IC）を実装。有効レコードが 3 未満の場合は None。
    - feature_exploration.rank: 平均ランク付け（同順位は平均ランク）を実装（浮動小数の丸めで ties の扱い安定化）。
    - feature_exploration.factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - 設計方針: DuckDB を用いた SQL 組合せ実装。外部ライブラリ依存を避ける。

- Data（データプラットフォーム）
  - kabusys.data.calendar_management
    - JPX カレンダー管理と営業日判定ユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar テーブルが存在しない場合は曜日ベースのフォールバック（平日を営業日）で一貫した判定を行う。
      - 最大探索範囲 _MAX_SEARCH_DAYS を設定し無限ループを回避。
      - calendar_update_job: jquants_client を使って差分取得→保存（バックフィル・健全性チェックを含む）するバッチロジックを実装。
      - DB の値優先、未登録日は曜日フォールバックという方針で実装。

  - kabusys.data.pipeline / kabusys.data.etl
    - ETLResult データクラスを定義（target_date, fetched/saved counts, quality_issues, errors を含む）。
      - has_errors / has_quality_errors プロパティを提供。
      - to_dict で quality_issues をシリアライズしてログや監査に利用可能。
    - ETL ヘルパー関数:
      - _table_exists / _get_max_date: DuckDB 上のテーブル存在・最大日付取得ユーティリティを実装。
    - pipeline モジュールは差分更新・保存（jq.save_*）・品質チェック（quality モジュール連携）を想定した設計を反映。

- その他
  - OpenAI SDK の呼び出しはすべて JSON mode（response_format={"type": "json_object"}）を想定。
  - DuckDB をデータストアとして使用する設計で SQL と Python を組み合わせた実装。
  - テスト容易性のため、API 呼び出し箇所はモック差替え可能（内部関数を patch する想定）。
  - パッケージ内の公開 API を __all__ などで明示（research, ai など）。

Fixed
- 初リリースのため該当なし

Changed
- 初リリースのため該当なし

Deprecated
- 初リリースのため該当なし

Removed
- 初リリースのため該当なし

Security
- 初リリースのため該当なし

注記
- 多くの機能は外部 API（OpenAI / J-Quants）や DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）に依存します。実運用前に必要なテーブル定義・API キー・接続設定を用意してください。
- OpenAI の API キーは環境変数 OPENAI_API_KEY、もしくは関数引数で注入する設計です。テスト環境では _call_openai_api をモックして副作用を抑えてください。