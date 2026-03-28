# Changelog

すべての変更は Keep a Changelog の形式に従い、重大度ごとに分類しています。  
このファイルではパッケージの初回公開バージョン 0.1.0 の機能仕様と実装上の注意点をまとめています。

今後のリリースでは Unreleased セクションに差分を追加してください。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース — 日本株自動売買 / 研究 / データ基盤の最小実装を提供。

### Added
- パッケージ全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API モジュール群: data, research, ai, execution, strategy, monitoring（__all__ にて一部公開）。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - 読込順序: OS 環境変数 > .env.local > .env（.env.local は既存環境変数を上書き可能）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応）。
  - Settings クラスを提供し、下記の設定を環境変数から取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のみを許可）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみを許可）
  - 必須環境変数未設定時は ValueError を送出する明示的なチェックを実装。

- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp.score_news）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出し ai_scores テーブルへ書き込む。
    - バッチ処理: 最大 20 銘柄／リクエスト、1銘柄あたり最大 10 件の記事・3000 文字にトリム。
    - JSON mode を使用し、レスポンスの厳格なバリデーション（results キー・code/score 検証）を実装。
    - 再試行ロジック: 429（RateLimit）、ネットワーク、タイムアウト、5xx をエクスポネンシャルバックオフでリトライ。
    - フェイルセーフ: API やパース失敗時は該当チャンクをスキップし、他の銘柄スコアを保護する（部分書換えロジック）。
    - DuckDB の executemany の挙動差異に配慮（空リストでの executemany 回避）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書込み銘柄数を返す。

  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロセンチメントは raw_news からマクロキーワードでフィルタした記事タイトルを OpenAI（gpt-4o-mini）へ投げ、JSON レスポンスから macro_sentiment を抽出。
    - ルール:
      - MA スコアは最新終値 / MA200、データ不足時は中立（1.0）を使用。
      - 合成スコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
      - DB へは冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。書込失敗時は ROLLBACK を試み例外を伝播。
    - 再試行や API エラーへのフォールバック（API失敗時の macro_sentiment=0.0）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- 研究（kabusys.research）
  - ファクター計算（research.factor_research）
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）を計算。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio などのボラティリティ / 流動性指標を計算。
    - calc_value(conn, target_date): per, roe を raw_financials と prices_daily から計算（EPS が 0 の場合は None）。
    - DuckDB SQL ベースの実装で、過去スキャン範囲や欠損取扱いに注意。
  - 特徴探索（research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装（LEAD を使用）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）による IC を計算（有効レコード < 3 の場合は None）。
    - rank(values): 同順位は平均ランクにするランク付けユーティリティを実装（浮動小数の丸めで ties を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median のサマリー統計を計算。
  - research パッケージは上記ユーティリティを re-export して公開。

- データ（kabusys.data）
  - カレンダー管理（data.calendar_management）
    - market_calendar を参照して営業日判定・次/前営業日取得・期間内営業日取得・SQ判定を提供。
    - DB 未取得時のフォールバックは曜日ベース（土日を非営業日扱い）。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン（data.pipeline）
    - ETLResult dataclass を実装（取得件数/保存件数/品質問題/エラーを格納）。to_dict() により品質問題はサマリ化して返す。
    - 差分更新、backfill、品質チェック（quality モジュール連携）を想定した設計。
  - data.etl は pipeline.ETLResult を再エクスポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Implementation details / 注意事項
- OpenAI API
  - news_nlp / regime_detector ともに OpenAI の Chat Completions（モデル gpt-4o-mini）を使用する想定。API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得される。
  - レスポンスは JSON mode（response_format={"type":"json_object"}）を期待するが、パース失敗時の復元ロジックや堅牢なバリデーションを備える。
  - API エラーやパース失敗は基本的に例外を上位へ投げずフォールバックして処理を継続（運用上の安全性重視）。ただし DB 書込み失敗時は例外を上位へ伝播。

- DuckDB 特有の互換性注意
  - executemany に空リストを渡すとエラーとなるバージョンがあるため、空パラメータを明示的に回避する実装を行っている。
  - 日付型の取り扱いで安定性を確保するため、DuckDB からの値を date へ変換するユーティリティを実装。

- ルックアヘッドバイアス対策
  - AI スコアリング / レジーム判定 / ファクター計算のすべてで datetime.today() や date.today() を内部参照しない設計。外部から target_date を与えて determinisitc に動作するようにしている。

- .env のパース仕様
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い（非クォート状態での '#' は直前が空白/タブであればコメント）は実装済み。複雑なケースの再現に注意。

### Required environment variables（運用前に設定が必須なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 機能を利用する場合）

デフォルトや代替:
- KABUSYS_ENV: デフォルト "development"（許容値: development, paper_trading, live）
- LOG_LEVEL: デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化

### Known issues / Limitations
- news_nlp / regime_detector は OpenAI を前提としており、ネットワーク障害や API 変更時に動作が制限される可能性がある（フォールバックはあるが機能低下は発生）。
- 一部 SQL クエリは DuckDB のウィンドウ関数に依存しており、非常に古いバージョンの DuckDB では動作に問題が生じる可能性がある。
- PBR・配当利回りなど一部のバリューファクターは未実装（calc_value では per と roe のみ）。

### Development / Testing notes
- AI 呼び出し箇所は内部で _call_openai_api を使用しており、ユニットテスト時は unittest.mock.patch で差し替え可能。
- 環境変数の自動ロードを無効にしてテスト環境を分離するには KABUSYS_DISABLE_AUTO_ENV_LOAD を使用。

---

この CHANGELOG はソースコードの現在の実装を元に推測して作成しています。実運用・正式リリース前に運用手順、権限管理、秘匿情報取り扱い（API キー・パスワード）について必ずレビューしてください。