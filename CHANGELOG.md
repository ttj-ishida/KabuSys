# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトは安定版へ向けた初期リリースとして記録しています。

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py（__all__ に data, strategy, execution, monitoring を公開）

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は `.git` または `pyproject.toml` を探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化対応（テスト用）。
    - .env パーサーは export 構文・クォート・エスケープ・インラインコメントを考慮。
    - .env 読み込み時に OS 環境変数を保護する protected 値の概念を持つ。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得可能。
    - J-Quants / kabu / LINE / DB パス（DuckDB/SQLite）/監視設定/しきい値/環境種別（development/paper_trading/live）/ログレベル等を取得。
    - 必須変数未設定時に明示的なエラー（ValueError）を投げる `_require` を実装。
    - env/log level のバリデーション（許容値セット）を実装。

- AI: ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news と news_symbols を用い、銘柄毎にニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出し `ai_scores` テーブルへ書き込む。
  - 主な仕様:
    - スコアリング対象ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換した半開区間を使用）。
    - 1 銘柄あたり最大 10 記事、文字数トリム（3000 文字）でプロンプト肥大化を制御。
    - バッチ処理（1 回あたり最大 20 銘柄）で API 呼び出しを行う。
    - リトライ戦略: 429 / ネットワーク / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、各要素の code/score 検証、数値かつ有限値、既知コードフィルタ）。
    - スコアは ±1.0 にクリップ。
    - 書き込みは冪等に行い（DELETE→INSERT）、部分失敗時に既存スコアを保護するロジックを採用。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部 `_call_openai_api` を patch 可能）。

  - 公開 API:
    - score_news(conn: duckdb.Connection, target_date: date, api_key: str | None) -> int

- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - 主な仕様:
    - MA200 乖離は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp のウィンドウ計算を利用してタイトルを抽出（マクロキーワードでフィルタ）。
    - OpenAI（gpt-4o-mini）を用いてマクロセンチメントを -1.0〜1.0 で算出。API エラー時はフォールバックで 0.0 を使用。
    - レジームスコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
    - レジームラベル判定閾値を定義（bull / bear の閾値あり）。
    - market_regime テーブルへの書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等化。失敗時は ROLLBACK を試みる。
    - OpenAI 呼び出し部分は news_nlp とは独立して実装（モジュール結合を避ける）。
  - 公開 API:
    - score_regime(conn: duckdb.Connection, target_date: date, api_key: str | None) -> int

- Data: マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー（祝日・半日取引・SQ日）を管理・判定するユーティリティを実装。
  - 提供機能:
    - is_trading_day(conn, d): 営業日判定（market_calendar があれば優先、未登録日は曜ベースでフォールバック）
    - next_trading_day / prev_trading_day: 前後の営業日を探索（最大探索上限で無限ループ防止）
    - get_trading_days(start, end): 期間内の営業日リストを返す（DB 値優先、未登録は曜ベースで補完）
    - is_sq_day: SQ 日判定（DB に依存、未登録時は False）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新。バックフィルと健全性チェックを実装。
  - 設計上の注意:
    - market_calendar 未取得時は曜日ベースのフォールバックを使用。
    - DB に一部データしかない場合でも next/prev/get_trading_day と一貫した結果を返す。
    - 最大探索日数（_MAX_SEARCH_DAYS）で探索停止し明示的エラーを投げる。

- Data: ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを導入し、ETL 実行結果（取得数、保存数、品質チェック、エラーなど）を構造化して返却。
  - ETL 設計:
    - 差分更新（最終取得日から未取得分のみ取得）、backfill による再取得、品質チェック結果の収集を想定。
    - jquants_client を使った idempotent 保存（ON CONFLICT DO UPDATE）を前提。
    - 品質チェックで重大度の高い問題があっても処理を継続し、呼び出し元で判断できる設計。
  - etl モジュールは ETLResult を再エクスポート。

- Research: ファクター計算 & 特徴量探索 (kabusys.research)
  - ファクター計算モジュール（factor_research）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m/ma200_dev を計算（データ不足時は None）
    - calc_volatility(conn, target_date): ATR(20)/相対ATR/平均売買代金/出来高比率を計算
    - calc_value(conn, target_date): PER（EPS 条件付き）と ROE を raw_financials と組み合わせて算出
    - DuckDB SQL を用いた実装で、prices_daily / raw_financials のみ参照（発注 API など本番系へのアクセスなし）
  - 特徴量探索モジュール（feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（LEAD を使用）を計算（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク相関）ベースの IC 計算（有効レコード < 3 なら None）
    - rank(values): 同順位は平均ランクで扱うランク関数（丸めで ties の検出漏れを防止）
    - factor_summary(records, columns): count/mean/std/min/max/median を算出
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

### Changed
- (初回リリースのため該当なし)

### Fixed
- (初回リリースのため該当なし)

### Security
- (初回リリースのため該当なし)

---

注記（設計上の重要点）
- ルックアヘッドバイアス対策: AI モジュール・ETL・研究モジュールともに内部で date.today() 等を無条件に参照しない設計。すべて呼び出し側が target_date を与えることで再現性を確保。
- OpenAI 利用部分はレスポンスの堅牢な検証・エラーハンドリング（リトライとフォールバック）を備えており、API 障害時に例外をそのまま上位に伝搬させない箇所がある（フェイルセーフ）。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT / ON CONFLICT）しており、部分失敗時に既存データを不必要に消さない工夫がある。
- テスト容易性: OpenAI 呼び出し箇所や .env 自動ロードを無効化するフラグ等、単体テストで差し替え・制御しやすい設計。

もしリリースノートに追加してほしい技術的な詳細（例: 各関数の戻り値サンプル、例外仕様、公開 API の一覧など）があれば教えてください。必要に応じて追補します。