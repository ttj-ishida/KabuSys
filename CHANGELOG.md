# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
現在のリリース: 0.1.0

## [0.1.0] - 2026-04-04

### 追加
- パッケージ初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
  - src/kabusys/__init__.py
    - パッケージメタ情報を公開（__version__ = 0.1.0）。
    - 公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定 / ロード機能
  - src/kabusys/config.py
    - .env/.env.local または OS 環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルートを .git または pyproject.toml を基準に探索（カレントワーキングディレクトリに依存しない）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
      - .env のパースは export 形式、クォートやエスケープ、インラインコメント等に対応。
      - 読み込み失敗は警告（warnings.warn）で処理を継続。
    - Settings クラスを提供（settings でインスタンスを公開）。
      - J-Quants / kabu / LINE / DB / 監視 / システム設定のプロパティを実装。
      - 必須変数は _require により未設定時に ValueError を投げる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
      - 環境値の妥当性検証（KABUSYS_ENV、LOG_LEVEL の許容値検査）。
      - DB パスや PID/KILL フラグ、閾値などにデフォルト値を設定。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB クエリ）。
    - 銘柄ごとに最新 N 記事を集約し、1 銘柄 1 スコアを返す設計（トリミングでトークン肥大を回避）。
    - バッチ送信（デフォルト: 最大 20 銘柄/コール）・チャンク処理実装。
    - 再試行（429・接続断・タイムアウト・5xx）を指数バックオフで実装。失敗時は当該チャンクをスキップ（フェイルセーフ）。
    - JSON モードのレスポンス検証と復元処理（前後に余計なテキストが混ざる場合の {} 抽出）。
    - スコアを ±1.0 にクリップ。
    - テストしやすさを考慮して _call_openai_api を差し替え可能（ユニットテストでの patch を想定）。
    - score_news API を公開（DuckDB 接続、target_date、api_key を受け取り書き込み件数を返す）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照し、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT を利用）。
    - LLM 呼び出しは独自実装（news_nlp とプライベート関数を共有しない設計）。
    - API 失敗時のフォールバック（macro_sentiment = 0.0）やリトライ/バックオフ、JSON パース保護を実装。
    - レジームスコア合成ロジック、閾値（BULL_THRESHOLD, BEAR_THRESHOLD）を実装。
    - score_regime API を公開（DuckDB 接続、target_date、api_key を受け取り成功時に 1 を返す）。

- データプラットフォーム（Data）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベース（土日除外）でフォールバックする一貫したロジックを実装。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル、健全性チェックあり）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの実装（差分取得、保存、品質チェックの呼び出しを想定）。
    - ETLResult データクラスを定義（target_date, 取得件数/保存件数, quality_issues, errors 等）および to_dict メソッド。
    - デフォルトのバックフィル・カレンダー先読みなどを定義。
    - jquants_client や quality モジュールとの連携点を定義（実体は別モジュールに委譲）。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB 前提）。

- 研究用ユーティリティ（Research）
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum, Value, Volatility, Liquidity）の実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日 MA 乖離）
      - calc_volatility: 20日 ATR（atr_20/atr_pct）、avg_turnover、volume_ratio
      - calc_value: per（株価/EPS）, roe（raw_financials からの最新値）
    - DuckDB を用いた SQL+Python 混合の実装。外部 API を呼ばない設計。
  - src/kabusys/research/feature_exploration.py
    - 研究用解析機能:
      - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）。
      - calc_ic: スピアマンのランク相関（Information Coefficient）計算（結合・欠損除外・3 銘柄未満で None を返す）。
      - rank: 同順位は平均ランクへ（丸めで ties の検出安定化）。
      - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）。
    - pandas 等に依存せず標準ライブラリのみで実装。

- パッケージ構造のエクスポート調整
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py, src/kabusys/data/__init__.py, src/kabusys/data/etl.py などで必要な API を再エクスポートして利用しやすく整理。

### 変更
- 初回リリースのため、過去バージョンからの変更項目は無し。

### 修正
- 初回リリースのため、過去バージョンからの修正項目は無し。

### 注意事項 / 既知の制約
- 多くの機能は DuckDB 上の特定テーブル（例: prices_daily, raw_news, market_regime, ai_scores, news_symbols, raw_financials, market_calendar 等）を前提としている。実行前にスキーマとデータが整備されている必要がある。
- AI（news_nlp, regime_detector）は OpenAI API（gpt-4o-mini）への接続を前提とし、API キー（OPENAI_API_KEY）を指定するか、score_* 関数に api_key を渡す必要がある。未設定時は ValueError を送出する。
- AI モジュールはネットワーク/API エラー時に部分的にフォールバック（0.0 やスキップ）するが、完全な成功を保証するものではない。
- 一部関数は副作用（DB 書き込み）を伴うため、テスト時はモックや一時 DB を利用することを推奨。
- タイムゾーン混入を避ける設計（すべて date を naive に扱う箇所や UTC 前提の保存を仮定している箇所あり）。運用時は DB の日時保存方針に注意。

### セキュリティ
- 機密情報（API キー、パスワード等）は環境変数経由で扱う設計。.env の自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

今後の予定（例）
- strategy / execution / monitoring パッケージの実装と連携テストの追加。
- 単体テスト・統合テストの充実、CI パイプラインの整備。
- パフォーマンス改善（DuckDB クエリ最適化、バッチ処理の並列化等）。