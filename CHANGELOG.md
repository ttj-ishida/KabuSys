CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を作成。
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード: プロジェクトルート（.git または pyproject.toml）を検出して
    .env → .env.local の順でローカル設定を読み込む（OS 環境変数優先）。
  - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 に対応。
  - .env パーサーは export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理など堅牢に実装。
  - 必須キー取得 _require() は未設定時に ValueError を送出。
  - Settings が提供する主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL 検証
    - is_live / is_paper / is_dev ユーティリティ

- ニュースNLP（AI）モジュール (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。
  - calc_news_window(target_date) による JST ベースのニュース収集ウィンドウ計算を実装（前日15:00〜当日08:30 JST 相当）。
  - score_news(conn, target_date, api_key=None): 指定日のニュースをスコア化して ai_scores テーブルへ idempotent に書き込み（DELETE→INSERT）。
  - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ずつ API に送信。1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - API リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ、上限到達時は該当チャンクをスキップ（フェイルセーフ）。
  - レスポンス検証: JSON 抽出・構造検証・スコア数値変換・±1.0 クリップなど堅牢に処理。パース失敗時はそのチャンクをスキップし他を保護。
  - テスト容易性: _call_openai_api を patch で差し替え可能。
  - ログ出力で処理状況を詳細に記録。

- マーケットレジーム判定モジュール (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を組み合わせて日次レジーム（bull / neutral / bear）を算出。
  - score_regime(conn, target_date, api_key=None): ma200_ratio の計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - マクロ記事抽出はキーワードリスト（日本語・英語）でフィルタし最大記事数を制限。
  - API リトライとフォールバック: API 失敗時は macro_sentiment=0.0 として継続。JSON パース失敗等もフェイルセーフで処理。
  - ルックアヘッドバイアス対策: target_date 未満のデータのみを使用し、date.today()/datetime.today() を参照しない設計。

- データプラットフォーム: ETL / カレンダー / パイプライン (src/kabusys/data)
  - pipeline.ETLResult とそれを再エクスポートする etl インターフェースを追加（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETLResult は取得数・保存数・品質チェック結果・エラー一覧等を含むデータクラスで、to_dict() により品質情報をシリアライズ可能。
  - calendar_management.py:
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - DB データ優先、未登録日は曜日ベースのフォールバック。最大探索範囲で無限ループ防止。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API（jquants_client を想定）から差分取得して market_calendar を更新。バックフィル期間・健全性チェックを組み込み。
  - pipeline.py:
    - ETL の設計方針に沿った差分取得、保存（idempotent）、品質チェックのためのユーティリティを実装。内部ユーティリティとしてテーブル存在確認や最大日付取得を提供。

- 研究（Research）モジュール (src/kabusys/research)
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比率などを計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER / ROE を算出（EPS=0 などは None）。
    - 実装は DuckDB + SQL ウィンドウ関数を多用し、欠損時は None を返す設計。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）を計算（ホライズン検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を実装。有効レコードが 3 未満なら None を返す。
    - rank(values): 同順位は平均ランクを返す安全なランク変換。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリーを実装。
  - research パッケージ __init__.py で主要関数を再エクスポート（zscore_normalize 等）。

Changed
- 設計上の方針（コード全体に適用）
  - ルックアヘッドバイアス回避: AI モジュールや研究モジュールは target_date 未満のみを用いる等、将来情報の流入を防ぐ実装方針を明示的に採用。
  - フェイルセーフ設計: 外部 API（OpenAI, J-Quants）失敗時は例外を無闇に上げず、可能な範囲で処理を継続（ログ出力・部分スキップ）してシステムの堅牢性を高める。
  - DuckDB 互換性: executemany に空リストを渡せない等の制約を考慮してデリケートな DB 操作（DELETE/INSERT）を実装。

Fixed
- 初期リリースのため明示的な bug-fix は無し（このリリースでの設計・実装により既知の堅牢化要素を導入）。

Security
- 外部 API キー等の必須値は環境変数から取得する設計。設定不足時は ValueError を送出して明示的に失敗させる箇所あり（安全性向上）。

Notes / 備考
- OpenAI API の利用は gpt-4o-mini を想定。API 呼び出しは response_format={"type": "json_object"} を用いて JSON Mode を期待するが、レスポンスが不正な場合の復元ロジックも実装。
- ai モジュールにおける内部 _call_openai_api は各モジュールで独立実装しており、ユニットテスト時に patch しやすい設計。
- J-Quants クライアント（jquants_client）は data モジュールから参照される想定で、外部 API との接続/保存ロジックは jquants_client 経由で分離されている。
- 今後のリリースでは strategy / execution / monitoring 系の具体的な自動売買・監視実装が追加される想定。

リンク
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/