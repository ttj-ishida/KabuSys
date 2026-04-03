Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- 初期リリース: kabusys パッケージのベース実装を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 管理
      - プロジェクトルート検出（.git / pyproject.toml）に基づく自動 .env 読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env の行パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
      - .env の読み込み時に OS 環境変数を保護する protected 機能（override オプションあり）。
      - Settings クラスを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境判定など）。
      - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値チェック）。
    - kabusys.ai
      - news_nlp:
        - Raw news を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントを評価する score_news を実装。
        - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を calc_news_window で提供。
        - バッチ送信（デフォルト 20 銘柄/回）、記事/文字数トリム、レスポンスバリデーション（JSON 抽出、results キー、スコア型チェック）、スコア ±1 クリップ。
        - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
        - テスト用に _call_openai_api を差し替え可能に設計。
      - regime_detector:
        - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
        - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ利用、データ不足時は中立扱い）とマクロニュース抽出、OpenAI 呼び出し（JSON Mode）を組み合わせる。
        - マクロキーワードリスト、リトライ / バックオフ、API 失敗時のフォールバック（macro_sentiment=0.0）、および idempotent な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
        - OpenAI クライアント生成は api_key を引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照してエラーを投げる。
    - kabusys.data
      - calendar_management:
        - JPX カレンダー管理用ユーティリティ群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
        - market_calendar が未取得の場合は曜日ベース（平日 = 営業日）でフォールバックする一貫したロジック。
        - calendar_update_job: J-Quants API から差分フェッチして market_calendar を冪等的に保存するジョブ（バックフィル、健全性チェック、エラーハンドリングを含む）。
      - pipeline / etl:
        - ETLResult データクラスを実装（取得件数・保存件数・品質検査結果・エラーの集約）。
        - ETL パイプライン設計の骨子（差分更新、保存、品質チェック方針）を実装（jquants_client と quality モジュールを利用）。
      - etl パッケージが ETLResult を再エクスポート。
    - kabusys.research
      - factor_research:
        - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を DuckDB クエリで計算（営業日ベースでルックバック、データ不足時は None を返す）。
        - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（NULL/データ不足を考慮）。
        - calc_value: raw_financials から直近財務を取得して PER / ROE を計算（EPS=0/欠損は None）。
      - feature_exploration:
        - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
        - calc_ic: Spearman（ランク）相関（IC）計算を実装。レコード不足や分散ゼロの場合は None を返す。
        - rank: 同順位は平均ランクとするランク付け（丸め処理で ties の検出を安定化）。
        - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
    - パッケージの __all__ エクスポートを整備（ai, research 等）。

Design / Reliability / Security notes
- ルックアヘッドバイアス防止:
  - AI モジュール / リサーチ系は内部で datetime.today() / date.today() を用いず、呼び出し側から target_date を渡す設計。
  - DB クエリは target_date 未満 / 排他条件 を用いるなどルックアヘッドを避ける実装を意識。
- DB 書き込みはできるだけ冪等（DELETE→INSERT）にして部分失敗で既存データを守る。
- OpenAI 呼び出しは JSON Mode を利用しレスポンスの厳密なパースを試みるが、冗長テキスト混入に備えて最外側の {} 抽出などの復元処理を行う。
- テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（モジュール内プライベート関数をパッチ）。
- 環境変数の自動読み込みは配布後も動作するよう __file__ を起点にプロジェクトルートを探索する実装。
- 環境変数や API キーが未設定時は ValueError を投げる箇所があり、呼び出し側で適切に設定する必要がある（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。
- DuckDB を主要な分析 DB として利用する想定（DuckDB の executemany の挙動に関する回避処理などを含む）。

Known limitations / TODO
- バリューファクター: PBR・配当利回りは未実装（calc_value の注記参照）。
- news_nlp / regime_detector: OpenAI（gpt-4o-mini）に依存。API 利用料・レート制限、モデル変更への互換性に留意する必要あり。
- 一部の外部クライアント（jquants_client, quality）を期待しているため、実行にはそれらの実装／設定が必要。
- calendar_update_job / pipeline の一部は jquants_client の実装（fetch/save）次第で動作結果が変わる。
- 現バージョンではセキュリティ関連の自動秘匿化・暗号化は実装していない（API キーは環境変数で管理する前提）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- API キーは環境変数で提供する設計（OPENAI_API_KEY 等）。公開リポジトリ等での直書きは避けてください。

Acknowledgements
- 本実装は DuckDB と OpenAI API（Chat Completions / JSON Mode）を中心に設計しています。

-----