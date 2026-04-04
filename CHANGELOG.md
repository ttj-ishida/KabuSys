CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

[Unreleased]
-------------

なし

[0.1.0] - 2026-04-04
-------------------

Added
- 初回公開リリース (0.1.0)。
- パッケージ構成
  - kabusys パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ に定義。
  - バージョン定義: __version__ = "0.1.0"。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数を保護するため protected set を利用して上書きを制御。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パースの強化:
    - コメント・export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしでのインラインコメント判定ロジック。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須: 未設定時は ValueError）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（デフォルトは空文字）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH（デフォルト: data/execution.pid）、KILL_FLAG_PATH（デフォルト: data/kill.flag）
    - KILL_FLAG_CLEAR_ON_START（デフォルト: "0" -> False）
    - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（デフォルト値あり）
    - KABUSYS_ENV 検証（allowed: development, paper_trading, live）と LOG_LEVEL 検証
    - ヘルパー: is_live / is_paper / is_dev
- AI モジュール (kabusys.ai)
  - news_nlp (ニュースセンチメント)
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI (gpt-4o-mini) に JSON Mode でバッチ送信してセンチメントを取得。
      - タイムウィンドウは JST 基準で「前日 15:00 JST 〜 当日 08:30 JST」（UTC では前日 06:00 ～ 23:30）として calc_news_window() を提供。
      - バッチ処理: 最大 _BATCH_SIZE=20 銘柄／コール、1銘柄あたり _MAX_ARTICLES_PER_STOCK=10 件、_MAX_CHARS_PER_STOCK=3000 文字でトリム。
      - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで再試行。その他エラーはスキップして継続（フェイルセーフ）。
      - レスポンス検証: JSON パース復元ロジック、"results" リスト・各要素の code/score の検証、未知コードは無視、スコアは ±1.0 にクリップ。
      - DB 書き込みは冪等手法（ターゲット日・コードで DELETE → INSERT）およびトランザクションで実装。部分失敗時に既存スコアを保護するようコード単位で絞り込んで削除。
      - テスト容易性: _call_openai_api のパッチ差替えを想定。
  - regime_detector (市場レジーム判定)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを合成して日次レジーム判定（'bull' / 'neutral' / 'bear'）。
      - 合成重み: MA 70%（スケール係数 10.0）、マクロ 30%。clip と閾値によりラベル付与（BULL_THRESHOLD=0.2, BEAR_THRESHOLD=0.2）。
      - マクロニュースは raw_news からマクロキーワードでフィルタ（最大 _MAX_MACRO_ARTICLES=20 件）。ニュースがない場合は LLM 呼び出しを行わず macro_sentiment=0.0。
      - OpenAI 呼び出しのリトライとフェイルセーフ: API 呼び出し失敗時は macro_sentiment=0.0 とし処理を継続。
      - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。
      - テスト容易性: _call_openai_api のパッチ差替えを想定、news_nlp と実装を分離してモジュール結合を低減。
- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev を計算。データ不足時は None。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。必要行数未満は None。
    - calc_value(conn, target_date): latest raw_financials から per (close / eps) と roe を計算（EPS が 0/欠損のときは None）。
    - DuckDB ベースの SQL とウィンドウ関数利用で、外部 API へはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターン（営業日ベース）を一回のクエリで取得。horizons の検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算。十分なサンプルがない場合は None。
    - rank(values): 同順位は平均ランクを返す実装（round(v,12) を利用して ties を扱う）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算するユーティリティ。
  - kabusys.research パッケージは必要関数を __all__ でエクスポート。
- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルの存在/未登録日に対しては曜日ベースのフォールバック（週末は非営業日）を行い、DB 登録ありは DB 値を優先する一貫したロジックを実装。
    - 探索制限: 最大探索範囲 _MAX_SEARCH_DAYS=60 を設けて無限ループを防止。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS): J-Quants クライアントを使って差分取得→save_market_calendar で冪等保存。バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（未来日が過度に大きい場合スキップ）を実装。
  - pipeline / etl
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETL フローの設計（差分更新、保存、品質チェック）に対応する基盤コード（ETLResult により品質問題・エラーを集約して返却）。
    - DuckDB のテーブル存在チェック等のユーティリティを実装。
- その他
  - 全体設計における「ルックアヘッドバイアス防止」方針の徹底:
    - date.today() / datetime.today() を直接参照しない（関数は target_date 引数を受け取る）。
  - 外部依存最小化:
    - Research の一部は標準ライブラリのみで実装（pandas 等に依存しない）。
  - テストフレンドリーな実装:
    - OpenAI 呼び出し箇所は内部関数をモックしやすく設計。

Changed
- 新規リリースのため特記すべき変更はなし（初版）。

Fixed
- 新規リリースのため特記すべき修正はなし（初版）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱い:
  - news_nlp.score_news と regime_detector.score_regime は api_key 引数を受け取り、未設定時は環境変数 OPENAI_API_KEY を参照する。キー未設定時は ValueError を送出。
  - 環境変数自動読み込み機能を無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を導入し、テスト環境等での誤読込みを防止可能。

Notes / 実装上の注意
- DB 書き込みはトランザクションで保護しているが、ROLLBACK に失敗した場合は警告ログを出力する実装になっている。
- DuckDB の executemany に空リストを渡すと不具合を起こすバージョン互換性を考慮し、空リストチェックを行っている。
- OpenAI とのやり取りは JSON Mode で厳密 JSON を期待するが、稀に前後テキストが混ざるケースを復元するフォールバックがある。
- 各機能は DuckDB 接続オブジェクトを受け取り、prices_daily / raw_news / news_symbols / raw_financials / market_calendar / ai_scores などのテーブルを参照することを前提としている。

開発者向け
- テスト時には以下の内部関数を patch することで外部 API 呼び出しをモックできます:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api

以上。