Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを使用します。

v0.1.0 - 2026-03-29
-------------------

Added
- パッケージ初期リリース。名前空間: kabusys、バージョン 0.1.0。
- 基本パッケージ構成を追加:
  - kabusys/__init__.py に __version__ と公開サブパッケージ一覧を定義。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml で探索（配布後も動作）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは次に対応:
    - 空行・コメント行、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォートあり/なしの挙動差分）など。
    - ファイル読み込み失敗時に警告を出力して継続。
    - override フラグと protected（OS 環境変数保護）をサポート。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / データベースパス 等のプロパティ（必須項目は _require で ValueError を投げる）。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の妥当性チェック。
    - duckdb/sqlite のデフォルトパス処理（Path.expanduser）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとにニュースを統合し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して比較）、calc_news_window ユーティリティを提供。
    - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大記事数・文字数でトリム（トークン肥大対策）。
    - エラー対策: 429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。それ以外はスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーションと部分書き込み: 有効なコードのみ抽出して DELETE → INSERT（部分失敗時に他コードの既存スコアを保護）。
    - テストフック: _call_openai_api を unittest.mock.patch で差し替え可能。
    - JSON パース時の堅牢化（前後余計なテキストが混入した場合は最外側の {} を抽出して復元）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime に書き込む。
    - マクロ記事抽出はキーワードベース（複数キーワード）で raw_news から取得、記事がない場合は LLM を呼ばずマクロスコアは 0.0。
    - OpenAI 呼び出しは独立実装でテスト差し替え可能。API 失敗時は macro_sentiment=0.0 として継続。
    - スコア合成・閾値により regime_label を bull/neutral/bear に割当て。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装、失敗時は ROLLBACK とログ。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。NULL ハンドリングを厳格に実装して不正な集計を防止。
    - calc_value: raw_financials から最新財務データを取得して PER, ROE を計算（EPS 0/欠損は None）。
    - 設計方針: DuckDB の SQL ウィンドウ関数を活用し、外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンは正整数かつ <=252 の検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）をランク化して計算。有効レコードが 3 未満なら None を返す。
    - rank: 同順位（ties）は平均ランクで処理、丸め誤差を防ぐため round(v,12) を利用。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research/__init__.py で主要関数を再エクスポート。

- Data（kabusys.data）
  - calendar_management:
    - JPX 市場カレンダー管理ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB に calendar データが無い場合は曜日ベースのフォールバック（土日を非営業日扱い）。DB 登録があればそれを優先する一貫した振る舞い。
    - next/prev_trading_day は最大探索範囲制限（_MAX_SEARCH_DAYS）を設けて無限ループを防ぐ。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新、バックフィル（直近 _BACKFILL_DAYS 日）と健全性チェックを実装。
  - pipeline / ETL:
    - ETL パイプラインのインターフェースと ETLResult データクラスを実装（kabusys.data.pipeline）。
    - ETLResult は取得数・保存数・品質問題リスト・エラーリストを保持、to_dict() でシリアライズ可能。
    - 差分更新ロジック、最終取得日の取得ユーティリティ、品質チェック結果の収集方針（Fail-Fast ではなく収集）などを実装。
    - デフォルトのバックフィル日数・カレンダー先読み日数等の定数を定義。
  - etl モジュールは ETLResult を再エクスポート。

- 共通設計方針（全体）
  - ルックアヘッドバイアス防止のため、モジュール内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - OpenAI/API 呼び出しは再試行・バックオフ・フェイルセーフを備え、テストで差し替え可能なフックを用意。
  - DuckDB を主要なローカルデータストアとして使用し、SQL ウィンドウ関数を多用して効率的に集計。
  - DB 書き込みは冪等性を考慮（DELETE → INSERT、または ON CONFLICT）して設計。

Fixed
- 初期リリースのため該当なし。

Notes / Developer hints
- OpenAI SDK（OpenAI クライアント）を使う箇所は api_key を引数で注入可能。None の場合は環境変数 OPENAI_API_KEY を参照する。
- テストでは各モジュール内の _call_openai_api をパッチすることで外部 API 呼び出しを置換可能。
- DuckDB の executemany は空リストを受け付けないバージョンへの互換性考慮が散見される（空チェックを行ってから executemany を呼ぶ実装になっている）。

セマンティック バージョニング
- このリリースは初回（0.1.0）。API 変更・機能追加・バグ修正は今後のバージョンで記載します。