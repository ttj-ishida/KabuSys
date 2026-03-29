CHANGELOG
=========

すべての重要な変更点はここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース。パッケージ名: kabusys（__version__ = "0.1.0"）。
- パッケージ構成（主なモジュール）
  - kabusys.config: 環境変数／設定管理
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理等に対応。
    - .env.local は .env の上書き（override=True）を行うが、プロセス起動時の OS 環境変数は保護（protected set）される。
    - Settings クラスを公開（settings）。必須キー取得時は未設定なら ValueError を送出。
      - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - オプション／デフォルト:
        - KABUSYS_ENV (development/paper_trading/live; デフォルト development)
        - LOG_LEVEL (DEBUG/INFO/...; デフォルト INFO)
        - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
        - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
        - SQLITE_PATH (デフォルト: data/monitoring.db)
- kabusys.ai: ニュースNLP と市場レジーム判定
  - news_nlp.score_news
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: JST 基準で「前日 15:00 JST ～ 当日 08:30 JST」を対象（内部では UTC naive datetime を使用）。
    - バッチ処理: 1 API コール当たり最大 20 銘柄（_BATCH_SIZE = 20）。
    - 1銘柄あたり最大記事数 10 件（_MAX_ARTICLES_PER_STOCK）、最大テキスト長 3000 文字（_MAX_CHARS_PER_STOCK）でトリム。
    - レスポンスは JSON mode（response_format={"type":"json_object"}）を想定。厳密な JSON を期待するが、前後に余計なテキストが混入するケースを補正してパースを試みる実装を含む。
    - スコアは ±1.0 にクリップ。API エラー・パース失敗などはフェイルセーフとして該当チャンクをスキップし、例外を投げず処理を継続。
    - OpenAI 呼び出しはリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで行う（初回待機 1s、最大リトライ _MAX_RETRIES = 3）。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（ma200_ratio）とマクロセンチメント（LLM）を重み付け合成して市場レジーム（bull/neutral/bear）を判定。
    - 加重: MA 70%（スケール 10.0）、マクロ 30%（_MA_WEIGHT=0.7, _MACRO_WEIGHT=0.3, _MA_SCALE=10.0）。
    - クリップ範囲: -1.0〜1.0。閾値: bull >= 0.2、bear <= -0.2。
    - マクロニュース抽出はキーワードマッチ（複数キーワード定義）を用い、最大 20 件を LLM に渡す。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックし処理を継続（フェイルセーフ）。
    - DB 書き込みは冪等性を考慮（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）、エラー時は ROLLBACK を試行して上位へ例外を伝播。
- kabusys.data: データ基盤ユーティリティ（DuckDB 前提）
  - calendar_management
    - market_calendar テーブルを使った営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日（土日）ベースのフォールバックを使用。
    - 夜間バッチ update (calendar_update_job): J-Quants API から差分取得して market_calendar に冪等保存。デフォルト先読み 90 日、バックフィル 7 日、健全性チェック（将来日付が過度に先の場合はスキップ）等の保護機構あり。
    - 探索の最大範囲制限（_MAX_SEARCH_DAYS = 60）など無限ループ防止策を実装。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプライン設計: 差分更新、idempotent 保存（ON CONFLICT DO UPDATE を想定）、品質チェックの収集・報告。
    - デフォルトのバックフィルは 3 日、J-Quants の株価データ開始日は 2017-01-01 を想定。
    - テーブル存在確認、最大日付取得などのユーティリティを提供。
    - ETLResult は品質問題・エラーの集合を保持し、has_errors / has_quality_errors / to_dict を提供。
- kabusys.research: ファクター計算・探索
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。十分な履歴がない場合は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得して PER（EPS が 0/欠損なら None）、ROE を計算。
    - すべて DuckDB + SQL で完結（外部 API へはアクセスしない）。
  - feature_exploration
    - calc_forward_returns: デフォルト horizons = [1,5,21]、horizons の妥当性チェック（正の整数かつ <= 252）。同一クエリで複数ホライズンを取得。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクを採る実装（丸めて ties 判定）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出（None 値は除外）。
  - data.stats から zscore_normalize を再エクスポート（kabusys.research.__init__）。
- 共通設計方針（各モジュールで共通）
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接利用しない設計（target_date を明示的に引数として受ける）。
  - DuckDB をデータ格納・分析の前提とする設計。SQL と組み合わせて高速に集約処理を行う。
  - LLM 呼び出しはフェイルセーフで、API の一時的障害を局所的に処理（リトライ・スキップ・デフォルト値）する方針。
  - テスト容易性を考慮して外部呼び出し箇所（OpenAI API 呼び出しなど）は差し替え可能に実装。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種シークレットは環境変数で管理する設計。settings.require で未設定時は明示的にエラーとし、安全な初期動作を促す。

Notes / 注意事項
- OpenAI との通信や J-Quants への問い合わせは実行時にネットワーク接続と有効な API キーが必要です（関数は引数で api_key を受け取ることが可能）。
- DuckDB のバージョン互換性のため、executemany に空リストを渡さない等の実装上の配慮があります。既知の制約により一部処理は空リストチェックを行っています。
- ai モジュールの各 _call_openai_api はテストで差し替えることを想定しており、ユニットテストでのモックが容易です。