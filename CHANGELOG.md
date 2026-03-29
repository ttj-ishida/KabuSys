Keep a Changelogに準拠したCHANGELOG.md

すべての注目すべき変更をこのファイルに記載します。履歴はセマンティックバージョニングに従います。
このプロジェクトの最初の公開リリースを示します。

v0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から親ディレクトリを探索（配布後も動作）。
  - .env パーサー実装: export 構文、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 既存 OS 環境変数を保護するための protected 上書き制御を実装。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを公開）。
  - 必須環境変数取得時の _require による明示的エラー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - デフォルト DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。
  - KABUSYS_ENV の検証（development / paper_trading / live）および LOG_LEVEL の検証。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール: ニュースを銘柄別に集約し OpenAI（gpt-4o-mini）でセンチメントを評価、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - 最大バッチサイズ、記事数制限、文字数トリムなどトークン肥大化対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しに対するリトライ／エクスポネンシャルバックオフ（429・ネットワーク断・タイムアウト・5xx 対応）。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - 部分失敗時に既存データを消さない idempotent な DB 書き換え（DELETE → INSERT、対象コードを限定）。
    - テスト用フック: _call_openai_api をパッチ差し替え可能。
  - regime_detector モジュール: ETF 1321（日経225連動型）200日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からキーワードでフィルタしてタイトルを抽出し LLM に渡す。
    - OpenAI 呼び出しに対するリトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0 として継続）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト用フック: _call_openai_api を差し替え可能。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。

- Data モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の API。
    - market_calendar 未取得時の曜日ベース・フォールバックを提供（休日情報がない場合も動作）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループ回避。
    - calendar_update_job: J-Quants からの差分取得、バックフィル（直近 _BACKFILL_DAYS 日）および健全性チェックを実装。
    - DB 登録値優先かつ未登録日は曜日フォールバックという一貫した挙動。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー等を保持）。
    - _get_max_date / _table_exists 等のユーティリティ、差分更新・バックフィル・品質チェック設計に基づく枠組みを用意。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - jquants_client / quality を利用する設計（実装は別モジュール想定）。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。欠損時は None。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 もしくは欠損のとき PER=None）。
    - DuckDB を用いた SQL ベースの計算で、外部 API へのアクセスは行わないことを保証。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン後の将来リターン（horizons デフォルト [1,5,21]）を計算。horizons の入力検証あり。
    - calc_ic: Spearman のランク相関（Information Coefficient）を実装。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - kabusys.research パッケージ __all__ に主要関数をエクスポート。

- 汎用実装・運用面の配慮
  - すべての「日付基準処理」は datetime.today() / date.today() に依存しない設計（ルックアヘッドバイアス防止）。
  - DuckDB を利用した一貫した DB インターフェース: SQL と Python の組合せで高性能に処理。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）と例外時のロールバック処理を実装。
  - ロギング注記を多用し運用時のトラブルシュートを容易化。
  - テスト容易性のために一部内部関数を patch 可能に設計（例: _call_openai_api）。

Fixed / Improved (実装上の堅牢性向上)
- .env パーサーの堅牢化（クォート内のバックスラッシュ処理、インラインコメントの扱い、export 形式対応）。
- DuckDB executemany の空リストバインド問題に対処（空リスト時に実行をスキップ）。
- OpenAI 呼び出しでの多様な失敗ケース（429、ネットワーク断、タイムアウト、5xx、非5xx）への適切なリトライ/フォールバック処理を導入。
- 欠損データやデータ不足時のフォールバック値（例: ma200_ratio=1.0、macro_sentiment=0.0）を明示的に設定してフェイルセーフ化。
- レスポンスのパース失敗時にワーニングを出力して処理を継続する方針を採用（例外を上位へ投げない箇所あり）。

Security
- OS 環境変数を保護するため、.env 読み込み時に既存環境変数を上書きしないデフォルト動作。明示的 override を許可。
- OpenAI API キーや各種トークンは環境変数での注入を前提。必須キー未設定時は明示的な ValueError を投げる。

Notes / ユーザー向け移行・利用上の注意
- 必須テーブル（使用想定）: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等。各モジュールはこれらのテーブル構造・カラムを前提に動作します。
- OpenAI 関連機能を使うには OPENAI_API_KEY（もしくは関数引数での api_key）が必要です。API 呼び出しは gpt-4o-mini を想定。
- 自動環境ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで有用）。
- デフォルトで使用される DB ファイルパスは Settings.duckdb_path / sqlite_path を参照してください（環境変数で上書き可能）。
- 本リリースは「リサーチ / データ処理 / AI スコアリング / レジーム判定」を中心とした初期実装であり、発注・実際の売買実行（kabusys.execution など）は別モジュール想定。

Deprecated
- なし（初回リリース）。

Removed
- なし（初回リリース）。

Security Issues
- なし（既知のセキュリティ問題はありません）。

今後の予定（非網羅）
- モジュール間の更なるテストカバレッジ強化（モックによる OpenAI / J-Quants クライアントの単体テスト）。
- 実行系（execution）や監視（monitoring）周りの実装拡充。
- ai モジュールのモデル切替やローカルモデル対応（オプション化）。
- データ品質チェック結果に基づく自動アラートや Dashboard 連携。

----- End of CHANGELOG -----