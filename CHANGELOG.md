# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

- リリース日はコードベースから推測した日付を使用しています（2026-03-29）。
- 本リリースは初期バージョン (0.1.0) として機能群を一括で導入しています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定 / 環境変数管理
  - kabusys.config
    - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path 等）。
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
    - .env パーサーは export 形式、クォートやエスケープ、行内コメントを考慮した堅牢な実装。
    - OS 環境変数を保護する protected オプションを導入（.env.local が OS 環境を上書きしないよう制御）。
    - 入力検証: KABUSYS_ENV / LOG_LEVEL 等の有効値チェック（無効時は ValueError）。

- ニュース NLP / AI モジュール
  - kabusys.ai.news_nlp
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約して銘柄ごとに OpenAI (gpt-4o-mini) へ送信し、センチメントスコアを ai_scores テーブルへ書き込み。
      - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
      - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・テキスト長トリム・JSON mode のレスポンスバリデーションを実装。
      - API エラー・レート制限・タイムアウト・5xx に対する指数バックオフリトライ。
      - 失敗時はロギングして該当チャンクをスキップ：フェイルセーフ設計。
      - DuckDB への書き込みは部分置換（DELETE → INSERT）で idempotent に処理。
    - 内部ユーティリティ: _fetch_articles, _score_chunk, _validate_and_extract など（JSON パースやスコアクリップ処理を含む）。

  - kabusys.ai.regime_detector
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
      - _calc_ma200_ratio によりルックアヘッドを防ぎつつ MA200 乖離を算出（データ不足時のフォールバック挙動あり）。
      - マクロキーワードフィルタで raw_news からタイトルを抽出し、OpenAI で macro_sentiment を算出（記事なし時は LLM 呼び出しをスキップして 0.0）。
      - API 呼び出し失敗時はマクロスコアを 0.0 にフォールバック（警告ログ）。
      - OpenAI 呼び出しは再試行（RateLimit/接続/タイムアウト/5xx の取り扱い）を実装。

- データプラットフォーム / ETL
  - kabusys.data.pipeline
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー等を集約可能）。
    - 差分更新やバックフィル方針、品質チェックとの連携を想定した ETL 設計（ドキュメント通りの処理フロー）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等。
  - kabusys.data.etl
    - pipeline.ETLResult を再エクスポート。

- カレンダー管理
  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理（market_calendar テーブル読み書き、祝日/SQ判定、営業日探索ロジック）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等更新するバッチ処理を実装（バックフィル・健全性チェックあり）。
    - DB データがない場合は曜日ベースでフォールバックする一貫した設計。

- リサーチ / ファクター計算
  - kabusys.research
    - factor_research モジュール
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時の None ハンドリング）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials から最新財務を取得して PER, ROE を計算。
    - feature_exploration モジュール
      - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: ランク相関（Spearman）で IC を計算（不足データは None）。
      - rank: 同順位を平均ランクにするランク変換ユーティリティ。
      - factor_summary: 各カラムの count/mean/std/min/max/median を標準ライブラリのみで算出。
    - kabusys.research.__init__ で主要関数を公開。

- その他
  - モジュールの公開制御 (__all__) を整理し、外部 API を明確化。
  - DuckDB を主要なデータ格納・クエリ基盤として想定した実装（DuckDB のバージョン差を考慮した互換性対策あり）。
  - OpenAI クライアント利用箇所でテスト時に差し替えやすいよう内部 _call_openai_api を用意。

### Changed
- 初期リリースのため該当なし（新規導入）。

### Fixed
- 初期リリースのため該当なし（既知のバグ修正履歴はなし）。

### Security
- 環境変数読み込みにおいて OS 環境（既存の環境変数）を protected として扱い、.env/.env.local による上書きを制御（KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能）。
- OpenAI API キー・各種シークレットは Settings 経由で必須チェックを行い、未設定時は明示的に ValueError を送出。

### Notes / Design decisions
- ルックアヘッドバイアス回避: datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- LLM 呼び出しは堅牢性重視（リトライ・タイムアウト・パース検証・フォールバック値）で実装。API 失敗で処理全体が停止しないフェイルセーフを採用。
- DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT を想定）し、部分失敗時に既存データを不必要に削除しない戦略。
- 外部 API との連携点（J-Quants, OpenAI）はクライアント層（kabusys.data.jquants_client 等）を介して切り離す設計を意図。

---

未記載の細かな内部実装やログ出力はソースコードの docstring と実装を参照してください。今後のリリースではバグ修正や API の安定化、パフォーマンス改善（並列処理・より細かい品質チェック等）を予定しています。