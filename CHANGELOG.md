KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に従います。
このプロジェクトは SemVer を使います。

Unreleased
----------
（なし）

0.1.0 - 2026-04-04
-----------------
初回リリース。以下の主要機能・モジュールを実装しています。

Added
- 基本パッケージ構成
  - パッケージバージョン: 0.1.0
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を設定。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export プレフィックス、クォートおよびエスケープ、インラインコメントの扱いに対応）。
  - 必須環境変数取得ヘルパ _require と Settings クラスを提供。主な設定:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（development/paper_trading/live の検証）と LOG_LEVEL 検証
    - is_live / is_paper / is_dev プロパティ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を基に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
  - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（内部は UTC naive datetime で扱う）。
  - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最新 10 記事・最大 3000 文字でトリム。
  - リトライ: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフ（最大リトライ回数・待機ロジック実装）。
  - レスポンス検証: JSON 抽出、"results" の構造検証、未知コードは無視、スコアを ±1.0 にクリップ。
  - DuckDB への書き込みは部分置換（該当コードのみ DELETE → INSERT）で冪等性を確保。DuckDB 0.10 の executemany 空リスト制約を考慮。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組合せて日次レジーム（bull/neutral/bear）を算出。
  - LLM は gpt-4o-mini を使用、JSON 入出力を期待。
  - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。
  - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試行。
  - OpenAI 呼び出しはモジュール独自実装で、テスト用に差し替え可能（patch しやすい設計）。

- 研究・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 0/欠損時は None）。
    - 設計方針として DuckDB の SQL + Python で完結し、本番の発注 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証あり。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクで扱う実装。丸め対策あり。
    - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を基に is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索範囲を設けて無限ループ回避。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェック実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約と to_dict 変換）。
    - ETL モジュールは差分取得、保存（idempotent）、品質チェック（quality モジュール）を想定。バックフィル、calendar lookahead などのパラメタを採用。

- DuckDB とテーブル連携
  - 多数の機能が DuckDB 接続を受け取り、prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを参照/更新する API を提供。

- ロギングと設計方針
  - 主要処理で詳細な logger 出力を実装（info/debug/warning/exception）。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（target_date 引数ベース）。
  - API 呼び出しは失敗してもシステム全体を停止させないフェイルセーフ設計（失敗時はスキップ or 中立値で継続）。
  - テスト容易性: OpenAI 呼び出し部分はモックで差し替え可能なよう設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 注意事項
- OpenAI API の利用には OPENAI_API_KEY が必要（各 score_* 関数は引数 api_key によりオーバーライド可能）。
- DuckDB のバージョン差異（例: executemany の空リストバインド）を考慮した実装上の注意あり。
- .env パースは多くのケース（クォート、エスケープ、コメント）に対応するが、極端に非標準な書式には未対応の場合があります。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡張（現状は公開インターフェースのみ）。
- より詳細なドキュメントとサンプル ETL / research ワークフローを追加。

--- End of changelog ---