CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。
日付や内容はコードベースから推測して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - モジュール構成の公開: kabusys.{data, research, ai, config, execution, monitoring}（__all__ に準拠）。
- 環境設定機能を追加（kabusys.config）
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサー実装: export 文対応、シングル/ダブルクォートとエスケープ対応、インラインコメント処理（クォート有無で挙動を分岐）。
  - 上書き制御（override）と OS 環境変数保護（protected set）を実装。
  - Settings クラスを提供: 必須変数取得（_require）、デフォルト値、検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）、パスデフォルト（DUCKDB_PATH / SQLITE_PATH）、is_live/is_paper/is_dev の便利プロパティ。
- ニュース NLP モジュールを追加（kabusys.ai.news_nlp）
  - ニュースの時間ウィンドウ計算（JST → UTC 対応）を提供（calc_news_window）。
  - raw_news / news_symbols から銘柄毎に記事を集約して OpenAI にバッチ送信し、ai_scores テーブルへ書込む処理を実装（score_news）。
  - OpenAI（gpt-4o-mini）の JSON mode を利用。バッチ処理サイズ上限 (_BATCH_SIZE=20)、1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
  - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装（_MAX_RETRIES / _RETRY_BASE_SECONDS）。
  - レスポンスの厳密なバリデーション実装（JSON抽出、results 配列検査、code/score の型検査、スコアクリップ ±1.0）。
  - 部分失敗に対応する冪等書き込み戦略（取得できたコードのみ DELETE → INSERT）とトランザクション（BEGIN/COMMIT/ROLLBACK）処理。
  - フェイルセーフ設計: API 失敗時は例外を上位に投げず、該当チャンクはスキップして処理を継続。
- 市場レジーム判定モジュールを追加（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動型）200日移動平均乖離とマクロニュース LLM センチメントを重み付きで合成して日次レジーム判定（bull/neutral/bear）を実装（score_regime）。
  - ma200 計算（_calc_ma200_ratio）ではルックアヘッドバイアス回避のため target_date 未満のみを使用し、データ不足時は中立値（1.0）へフォールバック。
  - マクロニュース抽出（キーワードベース、最大記事数制限）と LLM 評価（gpt-4o-mini）を組み合わせ、重み（MA 70% / Macro 30%）でスコアを合成。
  - OpenAI 呼び出しでのリトライ・例外ハンドリング（RateLimitError/APIConnectionError/APITimeoutError/APIError）とフォールバック（macro_sentiment=0.0）を実装。
  - market_regime テーブルへの冪等書き込み（DELETE→INSERT）およびトランザクション/ROLLBACK 保護を実装。
- データ ETL / パイプライン機能を追加（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを追加して ETL の集計結果・品質問題・エラーを構造化（to_dict により品質問題を簡易化して出力）。
  - テーブル存在確認、最大日付取得などのユーティリティを実装。
  - 差分更新・バックフィル設計を想定した定数（_MIN_DATA_DATE, _DEFAULT_BACKFILL_DAYS 等）を定義。
- マーケットカレンダー管理を追加（kabusys.data.calendar_management）
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定ロジックを実装。
  - market_calendar テーブルがない場合の曜日ベースフォールバック（週末除外）を実装し、DB にデータがある場合は DB 値優先の一貫した挙動を確保。
  - calendar_update_job を実装: J-Quants API から差分取得（lookahead, backfill, sanity check）→ jq.save_market_calendar による保存とログ出力。
  - 探索ループに上限（_MAX_SEARCH_DAYS）を設け、無限ループを防止。
- Research（ファクター計算・特徴量探索）を追加（kabusys.research）
  - factor_research: calc_momentum（1M/3M/6M リターン、ma200乖離）、calc_volatility（20日 ATR / 相対ATR / 平均売買代金 / 出来高比率）、calc_value（PER/ROE）を実装。DuckDB SQL を用いた実装で、データ不足時は None を返す設計。
  - feature_exploration: calc_forward_returns（任意ホライズンで将来リターン取得、horizons 検証）、calc_ic（Spearman ランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - 外部ライブラリに依存せず、標準ライブラリと DuckDB のみで実装。
- 内部設計・安全性上の配慮
  - 全ての分析処理において datetime.today()/date.today() を直接参照しない実装方針（ルックアヘッドバイアス防止）を明記・適用。
  - DuckDB の executemany に関する互換性問題を考慮して、空パラメータチェックを事前に行う実装。
  - OpenAI 呼び出し部分は各モジュールで独立実装し、モジュール間のプライベート関数共有を避ける設計（テスト時の差し替え箇所を明記）。

Fixed
- LLM 呼び出しでのエラー処理を堅牢化
  - OpenAI レスポンスの JSON パース失敗や予期しない構造に対するフォールバック（例: レスポンスから最外の {} を抽出して再パース）を実装し、致命的な例外とならないように変更。
  - API の 5xx / ネットワークエラー / レート制限を指数バックオフでリトライし、最終的に失敗した場合は該当処理をスキップして他に影響を及ぼさないようにした。
- DB トランザクションの保護強化
  - INSERT/DELETE 実行時に例外が発生した場合に ROLLBACK を試み、ROLLBACK 失敗時は警告を出力する実装を追加。
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、クォート無し時のインラインコメント判定を実装。

Security
- 環境変数取り扱い
  - OS 環境変数を保護する protected セットを導入し、.env の上書きを制御可能にした。
  - 必須トークン（OpenAI / SLACK / KABU API 等）を Settings で _require により取得し、未設定時は明確なエラーメッセージを出す。

Notes / Design decisions
- 多くの処理で「部分失敗を許容して残りを継続する」方針を採用（LLM API の不安定さを考慮）。
- AI レイヤーは gpt-4o-mini と JSON mode を使用する想定。出力の厳密な JSON 運用を前提としているため、レスポンス検証ロジックを重視。
- DuckDB をデータストアの中心に据え、SQL ウィンドウ関数を多用して高性能に集計・計算する設計。

許容事項（今後の改善候補）
- ai モジュールのテスト用に呼び出しラッパーを外部注入可能にしているが、より明示的な DI（依存注入）インターフェースの整備が有用。
- OpenAI 呼び出しのレスポンススキーマが変化した場合の互換性レイヤー（バージョン検出やフェールバック）を拡張すると堅牢性が増す。
- calendar_update_job や ETL 実行部分に監査ログ・メトリクス出力を追加すると運用性が向上する。

--- 

この CHANGELOG はコードから読み取れる機能・挙動を基に作成した推測的記述を含みます。実際の変更履歴（コミットメッセージ等）と差異がある場合があります。必要であれば各項目を実際のコミットやリリースノートに合わせて調整します。