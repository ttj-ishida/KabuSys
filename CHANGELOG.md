# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株の自動売買／データ基盤・リサーチ・AI 支援ツール群の基礎機能を実装しました。

### Added
- パッケージ基礎
  - kabusys パッケージ初期バージョンを追加。バージョンは `0.1.0`。
  - パッケージ公開 API（__all__）に data, strategy, execution, monitoring を宣言（実装はサブモジュール単位で提供）。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - .env パーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants / kabu ステーション / Slack / DB パスなど（必須変数は未設定時に ValueError を送出）。
    - `KABUSYS_ENV`（development, paper_trading, live）および `LOG_LEVEL` の検証を実装。
    - duckdb/sqlite のデフォルトパスを提供。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day などの営業日判定ユーティリティを実装。
    - カレンダー未取得時は曜日ベース（平日を営業日）でフォールバックするロジック。
    - calendar_update_job: J-Quants から差分取得して market_calendar テーブルへ冪等的に保存する夜間バッチ処理を実装（バックフィル・健全性チェック含む）。
    - 最大探索範囲やバックフィル日数等の安全対策を実装。
  - etl / pipeline:
    - ETLResult データクラスを追加（ETL 実行結果の集約、品質問題やエラーメッセージ保存、to_dict）。
    - 差分取得・保存・品質チェックのためのユーティリティ（テーブル有無チェック、最大日付取得など）。
    - etl モジュールで ETLResult を再エクスポート。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - score_news(conn, target_date, api_key=None): 指定ウィンドウ（前日15:00 JST～当日08:30 JST）内のニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数・文字数制限、JSON Mode によるバリデーション、レスポンスパースの耐性（前後余計テキストの切り出し）、スコアの ±1 クリップ。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対して指数バックオフでリトライ。非再試行エラー発生時は当該チャンクをスキップして続行。
    - DuckDB の executemany に関する互換性対策（空リストチェック）。

  - regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込む機能を実装。
    - ma200 計算（ルックアヘッド防止のため date < target_date を使用）、マクロ記事抽出、OpenAI 呼び出し、合成スコアの閾値によるラベリング（bull/neutral/bear）。
    - LLM 呼び出しのリトライ/フェイルセーフ（最終的に macro_sentiment=0.0 として継続）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装し、例外時は ROLLBACK を試行。

  - テスト性向上:
    - 各モジュール内部の OpenAI 呼び出し関数（_call_openai_api）はテスト時に patch できるよう分離。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを計算（MA200 乖離、ATR20、avg_turnover、PER/ROE 等）。
    - データ不足時の None 扱い、SQL ウィンドウ関数を多用した実装。
  - feature_exploration:
    - calc_forward_returns: 指定基準日から複数ホライズン先の将来リターンを一括取得（LEAD を使用）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。必要数未満は None を返す。
    - rank / factor_summary: 値のランク化（同順位は平均ランク）・基本統計量集計ユーティリティを実装。
  - すべて DuckDB 接続を受け取り外部 API に依存しない設計。

- その他
  - DuckDB を主要な永続化層として想定した実装と互換性対策（日付変換ユーティリティ等）。
  - 各所でログ出力・警告を充実させ、失敗時のフォールバック（例: LLM 失敗で 0.0）や安全策（健全性チェック、最大探索日数）を適用。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、内部実装で datetime.today() / date.today() を直接参照せず、score 等はすべて引数で target_date を受け取る設計になっています（一部のジョブは今日の日付を使用）。
- LLM / 外部 API 呼び出しは retry・バックオフ・フェイルセーフ（スコア 0.0 やチャンクスキップ）で堅牢化しています。
- DB 書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT 想定、安全な COMMIT/ROLLBACK）。
- DuckDB バージョン差異（executemany の空リスト扱い等）に関する互換性処理を含みます。

---

今後のリリースでは、strategy / execution / monitoring サブパッケージの実装、より詳細なテストカバレッジ、CI・パッケージング周りの整備、ドキュメントおよび例外ハンドリングの拡充を予定しています。