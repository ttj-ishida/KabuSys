# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - 公開モジュール群のエクスポート: data, strategy, execution, monitoring。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
  - 上書き制御: .env と .env.local の読み込み優先度（OS環境変数を保護する protected 機能）。
  - Settings クラスを提供し、各種必須/任意設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK の閾値
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL のバリデーション
  - 必須環境変数未設定時には ValueError を送出する厳密な取得関数を採用。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（ai_score）を計算する score_news を実装。
  - ニュース収集ウィンドウを JST ベースで計算する calc_news_window を提供（前日 15:00 JST ～ 当日 08:30 JST）。
  - バッチ処理（1 API 呼び出しで最大 _BATCH_SIZE=20 銘柄）と、1銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
  - OpenAI 呼び出しのリトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフを実装。
  - レスポンスの堅牢なバリデーションとパースロジック（JSON の前後余剰テキストの復元・results 構造チェック・コードの正規化・数値チェック）、およびスコアの ±1.0 クリップ。
  - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT）。DuckDB の executemany の制約に配慮した実装。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動）の 200 日移動平均乖離（_MA_WINDOW=200）とマクロニュース LLM センチメントを重み合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - MA 計算は target_date 未満のデータのみを使用、データ不足時は安全に中立値を返す。
  - マクロセンチメントはニュースタイトルをフィルタ（マクロキーワード群）して OpenAI に送信、失敗時は 0.0 にフォールバックするフェイルセーフ設計。
  - レジームスコアの合成、閾値によるラベリング、そして market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - OpenAI 呼び出しの再試行・エラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError）を実装。

- データプラットフォーム（src/kabusys/data/*）
  - ETL パイプライン基盤:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で re-export）。ETL の取得数、保存数、品質問題、エラーの集約を提供。
    - pipeline モジュールに差分取得・保存・品質チェックを行う設計を反映（差分更新・バックフィル・品質チェックの方針）。
  - カレンダー管理（calendar_management.py）:
    - market_calendar を使った営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時の曜日ベース（週末除外）フォールバックと、DB 登録値優先の一貫した補完ロジック。
    - calendar_update_job を実装し J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック付き）。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止、_BACKFILL_DAYS, _CALENDAR_LOOKAHEAD_DAYS 等の運用設定を導入。
  - jquants_client を利用する想定で API 取得／保存処理を呼び出す実装方針を反映。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - モメンタム（1M/3M/6M リターンおよび 200 日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）を DuckDB と SQL で計算する calc_momentum, calc_volatility, calc_value を実装。
    - 実装は prices_daily / raw_financials のみを参照し、外部発注や外部 API を呼ばない安全設計。
    - データ不足時は None を返す挙動を採用。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns、IC（Spearman の ρ）計算 calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - horizons のバリデーションや効率的な単一クエリ取得の工夫、ties を平均ランクで扱う実装を含む。
  - research パッケージの __init__ で主要関数をエクスポートし、data.stats.zscore_normalize を再利用。

- テスト・運用を意識した設計
  - LLM 呼び出し部分はユニットテストから差し替え可能な設計（_call_openai_api を patch して差し替えられる）。
  - ルックアヘッドバイアス防止のため、各アルゴリズムで datetime.today()/date.today() を直接参照しない方針を徹底。
  - DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT 相当の扱いを想定）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし（リリース時点で特記すべきセキュリティ修正はありません）

Notes / Design decisions
- DuckDB を主要な分析用 DB として採用。executemany の空パラメータに関する互換性注意（実装で回避）。
- OpenAI（gpt-4o-mini）呼び出しは JSON Mode を使用し、厳密な JSON 出力を期待するが、実運用でのノイズに対して堅牢に処理する実装になっています。
- API キー（OPENAI_API_KEY）は関数引数から注入可能で、テスト時に明示的に差し替えられるように設計。

---

今後の予定（非包括的）
- strategy / execution / monitoring の実装拡張（現在はパッケージエクスポートのみ）。
- jquants_client の具体的実装と ETL pipeline の結合テスト。
- モデル評価用の追加メトリクス・可視化機能の追加。

（以上）