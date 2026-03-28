Keep a Changelog
=================

このファイルは Keep a Changelog の形式に準拠しており、将来のバージョン管理と利用者向けの変更履歴の記録を目的としています。

[0.1.0] - 2026-03-28
-------------------

Added
- 初期リリース: kabusys パッケージ（バージョン 0.1.0）
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義 (data, strategy, execution, monitoring)。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に _find_project_root() で探索（CWD 非依存）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応。
    - .env.local は override=True で読み込み。ただし起動時の OS 環境変数は保護（protected set）される。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - 必須環境変数チェックを行う _require() を備える（未設定時は ValueError）。
    - 主要な設定プロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のみ許容）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）
    - ヘルパー: is_live, is_paper, is_dev

- AI モジュール (src/kabusys/ai/)
  - ニュースセンチメント (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）の JSON mode にバッチ送信してセンチメントを算出。
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う calc_news_window）。
      - チャンク/バッチ処理: 最大 _BATCH_SIZE=20 銘柄ずつ、1 銘柄あたり _MAX_ARTICLES_PER_STOCK=10 記事・_MAX_CHARS_PER_STOCK=3000 文字にトリム。
      - 再試行／バックオフ: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフで最大リトライ。
      - レスポンス検証: JSON パース、"results" リスト、各 item の code と score を検証。スコアは ±1.0 にクリップ。
      - DB 書き込みは部分失敗に耐える設計（対象コードのみ DELETE → INSERT を実行、DuckDB executemany の空リスト制約に対応）。
      - テスト用に OpenAI 呼び出しを差し替え可能 (_call_openai_api を patch 可能)。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の直近 200 日終値から MA200 乖離率を計算（ルックアヘッドを避けるため target_date 未満のみ使用）。
      - raw_news からマクロキーワードでフィルタした記事タイトルを抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価（記事無しや API 失敗時は macro_sentiment=0.0 にフォールバック）。
      - 合成ルール: レジームスコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1,1) 。閾値に基づき 'bull'/'neutral'/'bear' を判定。
      - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を行い、失敗時は ROLLBACK を試行して例外を上位へ伝播。
      - マクロキーワードやモデル定数、リトライ回数等はモジュール内定数で管理。
      - OpenAI 呼び出しは独立実装でモジュール結合を避け、テストで差し替え可能。

- リサーチ（因子・特徴探索）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m / ma200_dev を計算。ma200_dev は 200 行未満で None。
      - DuckDB のウィンドウ関数を利用して効率的に取得。
    - calc_volatility(conn, target_date)
      - 20 日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。データ不足時は None。
    - calc_value(conn, target_date)
      - raw_financials の直近レポートから PER（EPS が 0/欠損なら None）と ROE を計算。
    - すべて DuckDB の prices_daily や raw_financials のみ参照し、本番発注等へは影響しない設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズンの将来リターン（fwd_1d, fwd_5d, fwd_21d 等）を計算。horizons の妥当性検査あり。
    - calc_ic(factors, forwards, factor_col, return_col)
      - スピアマンのランク相関（IC）を算出。有効レコード数が 3 未満の場合は None。
    - rank(values)
      - 同位順位は平均ランクにする実装（round(v,12) により ties の安定化）。
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を算出（None は除外）。

- データ基盤 (src/kabusys/data/)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルが無い場合は曜日ベース（土日休場）でフォールバック。
    - calendar_update_job(conn, lookahead_days=90)
      - jquants_client 経由で差分取得し market_calendar に冪等保存。バックフィル (_BACKFILL_DAYS)、先読み、健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, etl.py)
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラーメッセージ等を格納）。
    - 差分更新、保存（jquants_client の save_* を利用し冪等処理）、品質チェックのフレームワークを用意。
    - data.etl で ETLResult を再エクスポート。

- 設計上の注意点（全体）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を内部ロジックで参照しない（外部から target_date を注入）。
  - DuckDB を主要なストレージとして使用（DuckDB 固有の制約に配慮した実装）。
  - API 呼び出しに対してはフェイルセーフ設計（API 失敗時は 0/空でフォールバックし、逐次処理を継続）。
  - テスト容易性: OpenAI 呼び出しなどを patch で差し替えられるよう実装されている箇所を明示。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 相当の扱い）し、部分失敗で既存データを不必要に消さない工夫を行っている。
  - ロギング: 各モジュールで詳細な info/debug/warning/exception ログを出す設計。

Notes / 初期セットアップメモ
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（score_news / score_regime を利用する場合）
- デフォルトファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- KABUSYS_ENV の有効値: development, paper_trading, live
- LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Acknowledgements / 開発者向け注記
- OpenAI への呼び出しは gpt-4o-mini を想定した JSON mode を利用（レスポンスの堅牢なパースと検証を実装）。
- テストのために各モジュールの API 呼び出し部にはモック差し替えの想定がある（例: news_nlp._call_openai_api, regime_detector._call_openai_api）。
- 今後のリリースでは monitoring/strategy/execution の詳細な公開 API と CLI /ジョブ起動部分の追加を予定。

--- 
（この CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノートとして利用する際は必要に応じて具体的な差分・チケット番号・著者などを追記してください。）