CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記載します。本フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ外部公開 API の整理（__all__ で data／strategy／execution／monitoring 等を公開）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存でパッケージ配布後も動作）。
  - .env パーサーは以下に対応:
    - 空行／コメント行（#）の無視、export KEY=val 形式の対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント扱い（直前が空白/タブの場合のみ）。
  - 読み込み時の保護機能:
    - override フラグと protected キーセットをサポートし、OS 環境変数の上書きを防止。
    - .env ファイル読み込み失敗時は警告を出力してフォールバック。
  - Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants / kabuステーション / LINE / DB ファイルパス / 監視閾値 等のプロパティを環境変数経由で取得。
    - KABUSYS_ENV の値検証（development / paper_trading / live のみ有効）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のヘルパー。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得。
    - タイムウィンドウ計算（JST ベース → DB は UTC で比較）を calc_news_window で提供。
    - バッチ処理: 1回の API 呼び出しで最大 _BATCH_SIZE（デフォルト 20）銘柄を処理。
    - 1銘柄当たりの最大記事数・最大文字数制限でトークン肥大化を防止（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ処理。
    - レスポンスの堅牢なバリデーションおよび JSON 抽出（異常に余計な前後テキストが混入した場合の復元処理を含む）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込み。
    - DuckDB の executemany に対する既知制約（空リスト不可）を考慮した実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テスト容易性を考慮し、API 呼び出し関数を patch で差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事はニュースからマクロキーワードでフィルタし、OpenAI（gpt-4o-mini, JSON mode）で -1.0〜1.0 に評価。
    - LLM 呼び出しはリトライ・エラー時にフォールバック（macro_sentiment=0.0）して処理継続するフェイルセーフ設計。
    - レジーム判定結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。失敗時は ROLLBACK を試行し例外を上位へ伝播。
    - lookahead バイアス防止: target_date 未満のデータのみを参照し、内部で datetime.today()/date.today() を直接参照しない。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。必要レコード未満は None を返す。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - いずれも DuckDB の prices_daily / raw_financials を参照し、実行時の外部 API へのアクセスは行わない設計。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 与えられた horizons（デフォルト [1,5,21]）について将来リターンを計算。horizons の検証あり。
    - calc_ic: Spearman ランク相関（IC）を計算するユーティリティ。必要件数未満では None を返す。
    - rank: 同順位の平均ランクを採るランク関数（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。

- データプラットフォーム (kabusys.data)
  - calendar_management モジュール:
    - JPX マーケットカレンダーを管理する機能を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未登録のときは曜日ベースのフォールバック（週末を非営業日扱い）。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した挙動を保証。
    - calendar_update_job を実装。J-Quants から差分取得し冪等保存。バックフィルや健全性チェックを実装。
  - ETL / pipeline:
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult）。ETL の実行結果・品質問題・エラーを集約して返却可能。
    - pipeline モジュール（差分取得／保存／品質チェックの方針）を実装。バックフィル日数や品質チェックの重大度管理を含む。
  - etl モジュールは ETLResult を再エクスポート。

- 共通実装・運用上の配慮
  - DuckDB を主要なストレージとして想定した SQL 実装。
  - トランザクションを利用した冪等処理、失敗時のロールバック試行とログ出力。
  - ログ出力（logger）を各モジュールで利用し詳細な実行情報を記録。
  - テスト容易性: OpenAI 呼び出しや sleep 等を patch で差し替え可能に設計。

Fixed
- （初期リリース：該当なし）

Changed
- （初期リリース：該当なし）

Security
- 環境変数による API キー管理を前提（OPENAI_API_KEY など）。コード内にハードコードされた秘密情報は含まれない設計。
- .env 読み込み時に OS 環境変数の保護機能（protected set）を実装。

Notes / Known behaviors
- OpenAI との統合は gpt-4o-mini を想定しており、JSON Mode（response_format={"type": "json_object"}）を利用。実行環境の OpenAI SDK バージョン差異に応じた例外フィルタリングを行っている（status_code の存在有無に対応）。
- API 失敗時はフェイルセーフとして処理を継続する設計（スコアは 0.0 にフォールバック、部分的にスキップして他の銘柄や処理を保護）。
- DuckDB の executemany における空リストバインドの制約を回避するため、事前チェックを実施。
- 日付の扱いはすべて date / naive datetime（UTC や JST の変換は明示的）で行い、ルックアヘッドバイアスを防止するため内部での日付参照は target_date ベース。

---

今後の予定（未実装 / 検討中の点）
- Strategy / execution / monitoring の具体的な実装詳細の追加とエンドツーエンドテスト。
- ai/regime_detector と news_nlp の評価パイプライン・キャッシュ機構やコスト最適化（API コール削減）。
- 増分 ETL のスケジューリング・監視ジョブの追加。

もし他に強調したい差分や公開するバージョン日付の修正希望があればお知らせください。