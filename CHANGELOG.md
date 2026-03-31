# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
初版リリースの内容はコードベースから推測して記載しています。

全般的な方針・共通知識
- 多くの処理でルックアヘッドバイアスを防ぐために datetime.today() / date.today() を直接参照しない実装が採用されています（呼び出し元が基準日を明示的に渡す設計）。
- DuckDB を主要なローカルデータストアとして利用。executemany の空リストバインドや list 型パラメータのバインドの互換性に注意した実装になっています。
- OpenAI（gpt-4o-mini）を利用する NLP / LLM 呼び出し部分は堅牢化（JSON 検証・リトライ・バックオフ・フェイルセーフ）されています。テスト用に API 呼び出し関数を差し替え可能な設計です。

Unreleased
- （今後の変更をここに記載）

[0.1.0] - 2026-03-31
======================================
Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にバージョンと公開モジュールを定義。

- 環境設定 / 設定読み込み
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探索して行うため CWD に依存しません。
      - 読み込み順序: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント扱いなどに対応。
      - 既存 OS 環境変数の保護（protected set）を考慮して .env.local の上書き挙動を制御。
    - Settings クラスを提供。必須環境変数取得のヘルパー（_require）と以下のプロパティを公開:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
      - KABUSYS_ENV の検証（development / paper_trading / live）
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev の便利プロパティ

- AI モジュール（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - バッチサイズ、1 銘柄あたりの最大記事数・最大文字数、JST → UTC によるニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）などを細かく制御。
    - レスポンスのバリデーションと数値クリップ（±1.0）を実装。JSON パース失敗時は余分な前後テキストを含むケースを回復するロジックあり。
    - 一時エラー（429 / ネットワーク断 / タイムアウト / 5xx）は指数バックオフでリトライ。その他のエラーはスキップして継続するフェイルセーフ設計。
    - 書き込みは部分失敗に備えて、取得成功した銘柄のみを DELETE → INSERT で置換（DuckDB executemany 空リスト対応を考慮）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - テスト用フック: _call_openai_api を patch 可能。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジームを日次判定（'bull'/'neutral'/'bear'）。
    - prices_daily と raw_news を参照して ma200_ratio を算出、マクロニュースはキーワードフィルタで抽出して LLM による macro_sentiment を取得。
    - LLM 呼び出しは リトライ / バックオフ / 5xx 特別扱い を実装。API 失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
    - OpenAI クライアントは OpenAI(api_key=...) を想定、モデル gpt-4o-mini を使用。

- Research（因子計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム (1M/3M/6M)、200 日移動平均乖離、ATR（20 日）、平均売買代金・出来高変化率、PER・ROE（raw_financials から取得）等のファクター計算を実装。
    - DuckDB 上の SQL ウィンドウ関数を多用し、高速に日付基準で計算する。データ不足時は None を返す設計。
    - 公開関数: calc_momentum, calc_volatility, calc_value（各関数は conn と target_date を受け取りリスト形式で結果を返す）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意の営業日ホライズン）、IC（Spearman の ρ）計算、ランク関数（同順位は平均ランク）、ファクター統計サマリーを実装。
    - calc_forward_returns は複数ホライズンをまとめて 1 クエリで取得。horizons のバリデーションあり。
    - calc_ic は少数レコード（<3）や分散ゼロケースを安全に扱う。
    - factor_summary は count/mean/std/min/max/median を計算。

  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- Data（データ取得・ETL・カレンダー管理）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理。market_calendar テーブルの有無を考慮した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB にデータがない場合は曜日（平日）ベースのフォールバックを使用する設計で一貫性を保つ。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル、健全性チェックあり）。
    - _MAX_SEARCH_DAYS 等の安全パラメタを導入し無限ループ等を防止。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基本機能とユーティリティ。
    - ETLResult dataclass を定義（取得件数・保存件数・品質問題・エラーリスト等を含む）。to_dict により品質問題はシリアライズ可能な形式へ変換。
    - 差分更新のための最大日付取得、テーブル存在チェック等のユーティリティを実装。
    - jquants_client と quality モジュールを組み合わせる想定（コードベースに jquants_client の使用箇所を明示）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - テーブル存在確認や日付変換ユーティリティなど DuckDB 周りの互換性考慮が含まれる。

- 監視・実行・その他モジュールの土台
  - パッケージ構造に data, research, ai, monitoring, execution, strategy など主要サブパッケージを示唆（__all__ による公開）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を用いる設計。キー未設定時は ValueError を送出して明示的に失敗。
- .env 自動読み込み時に OS 環境変数を誤って上書きしない仕組み（protected set）を導入。

Notes / Implementation details / 開発上の注意
- 実運用では環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）の管理が必須。
- news_nlp と regime_detector の両方で OpenAI の JSON Mode を利用し、レスポンスの妥当性チェックを厳密に行っている。API の挙動変化に備えて status_code の有無に柔軟に対応するコードを含む。
- DuckDB のバージョン互換性（executemany の挙動やリストバインド）に合わせた回避策が実装されているため、DuckDB バージョン変更時は注意が必要。
- 多くの DB 書き込みは冪等（DELETE→INSERT など）で行われ部分失敗時に既存データを不必要に消さないよう配慮されている。

Acknowledgements
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートや API 仕様はプロジェクトの正式なリリース文書に従ってください。