Keep a Changelog に準拠した CHANGELOG.md

すべての変更は慣例に従いセクション別（Added / Changed / Fixed / Deprecated / Removed / Security）で記載しています。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース (バージョン 0.1.0)
- パッケージのエントリポイントを追加
  - kabusys/__init__.py に __version__ = "0.1.0" と __all__ エクスポート（data, strategy, execution, monitoring）。
- 環境設定管理
  - kabusys.config.Settings を実装。.env ファイルまたは OS 環境変数から設定を読み込む。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml）から .env/.env.local を探索してロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式やクォート・エスケープ・インラインコメントに対応。
  - 必須値取得のための _require ヘルパーと、env/log level の入力検証（有効値チェック）を実装。
  - 主要設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。
- AI（NLP）コンポーネント
  - kabusys.ai.news_nlp:
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini, JSON Mode）により銘柄ごとのセンチメントを算出し、ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/リクエスト）、記事トリム（記事数・文字数制限）、JSON レスポンス検証を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数的バックオフリトライを実装。例外が発生してもフェイルセーフで他銘柄処理を継続。
    - テスト用に _call_openai_api をパッチ差替え可能（unittest.mock.patch）。
    - calc_news_window(target_date) を実装（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC ナイーブなウィンドウ）。
  - kabusys.ai.regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに書き込み。
    - マクロキーワードフィルタによる raw_news タイトル抽出、OpenAI 呼び出し、複数リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - ルールに基づく regime_label ('bull' / 'neutral' / 'bear') 判定ロジックを実装。DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
- データ基盤
  - kabusys.data.pipeline:
    - ETLResult データクラスを定義し、ETL の取得件数・保存件数・品質チェック結果・エラーを集約。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得ロジック等を実装。
  - kabusys.data.etl: pipeline.ETLResult を再エクスポート。
  - kabusys.data.calendar_management:
    - 市場カレンダー管理と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - calendar_update_job(conn, lookahead_days=90): J-Quants API を通じたカレンダー差分取得 → market_calendar への冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）。
    - カレンダー未取得時の曜日ベースフォールバックやバックフィル、健全性チェックを実装。
- リサーチ / ファクター計算
  - kabusys.research.factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を利用して PER / ROE を計算（EPS 欠損や 0 の場合は None）。
    - 計算結果を (date, code) 単位の dict リストで返却。
  - kabusys.research.feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターン（複数ホライズン）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク）ベースの IC を実装。
    - rank(values): 同順位は平均ランクに変換（丸め考慮）。
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリーを計算。
  - kabusys.research.__init__ で主要関数をエクスポート。
- 安全設計・テスト性
  - 全体的に「ルックアヘッドバイアス防止」を徹底（datetime.today() / date.today() を直接参照しない関数実装）。
  - OpenAI 呼び出し部分はテスト時に差し替え可能（内部関数をパッチできる）。
  - DuckDB の executemany に対する互換性（空リスト回避）などの実装上の注意を反映。

Fixed
- 外部 API 異常時のハンドリングを明示的に実装:
  - news_nlp/regime_detector の OpenAI 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を指数的バックオフでリトライし、全リトライ失敗時はフェイルセーフ（0.0 など）で継続するようにした。
- DuckDB 互換性対応:
  - executemany に空リストを渡さないようガードし、部分失敗時に既存データを保護するロジックを導入（ai_scores の DELETE → INSERT における保護）。
- calendar_management の market_calendar が未取得またはカラムが NULL のケースに対するフォールバック（曜日ベース）と警告ログ出力を追加。

Changed
- なし（初版のため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 卒業メモ（移行・利用時の注意）
- OpenAI API
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。未設定時は ValueError を送出します。
  - 使用モデルは gpt-4o-mini、JSON Mode でのやり取りを前提としています。プロンプトは厳密な JSON 出力を期待する設計です。
- 必要な DB テーブル（DuckDB スキーマ）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などが存在することを前提とした実装です。初回導入時は必要スキーマを用意してください。
- 環境変数 / .env
  - 自動ロードはプロジェクトルート検出に依存します。パッケージ配布後に動作させる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を検討してください。
- テスト
  - OpenAI 呼び出し箇所は内部の _call_openai_api を unittest.mock.patch で差し替え可能です。これによりネットワークに依存しないユニットテストが可能です。

お問い合わせ・貢献
- バグ報告や改善提案は Issue を立ててください。重大な設計方針（ルックアヘッドバイアス防止、冪等保存、フェイルセーフなど）は今後も維持します。