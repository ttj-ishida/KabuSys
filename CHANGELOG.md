CHANGELOG
=========

すべての注目に値する変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現時点で未リリースの変更はここに記載します。）

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース（パッケージバージョン: 0.1.0）。
- パッケージの公開インターフェースを定義。
  - src/kabusys/__init__.py にてバージョン管理と主要サブパッケージをエクスポート（data, research, ai 等）。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env および .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
    - export KEY=val 形式やクォート/エスケープ、行内コメントなどを考慮した堅牢な .env パーサーを実装。
    - OS 環境変数の保護（protected set）と override 挙動をサポート。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
    - Settings クラスを提供し、必須変数は _require() による検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。デフォルト値や Path 変換（duckdb/sqlite パス）、環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメント（ai_score）を算出、ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数・文字数トリム、API 呼び出しのリトライ（429/ネットワーク/5xx へ指数バックオフ）、レスポンス検証（JSON 解析／results 構造のバリデーション）、スコアの ±1.0 クリップを実装。
    - API 呼び出し部分は _call_openai_api を介しており、テスト時に差し替え可能（unittest.mock.patch を想定）。
    - 部分失敗時に他銘柄の既存スコアを保護するため、DELETE（銘柄別）→ INSERT の冪等書き込みを実装（DuckDB executemany の挙動を考慮）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュース由来の LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する処理を実装。
    - prices_daily / raw_news を参照し ma200_ratio を計算、マクロ記事はキーワードフィルタで抽出、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API レスポンスのパースや API エラーに対してはフォールバック（macro_sentiment=0.0）し、全体を冪等に market_regime テーブルへ書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - OpenAI 呼び出しの個別実装・リトライ制御を行いテスト容易性を確保。

- Research（因子・特徴量分析）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum ファクター（1M/3M/6M リターン、200日 MA 乖離）、Volatility / Liquidity（20日 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily/raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（必要行数未満なら None）、営業日スキャン範囲のバッファ設計等を反映。
    - 関数は (date, code) をキーとする dict のリストを返す設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出ユーティリティ calc_forward_returns（複数ホライズン対応、入力検証、1クエリでの取得）、IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク化して算出）、ランク関数 rank（同順位は平均ランク処理）、統計サマリー関数 factor_summary を実装。
    - pandas 等に依存せず標準ライブラリで実装。

  - src/kabusys/research/__init__.py で上記の主要関数をエクスポート。

- Data（データ基盤）モジュール
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルを活用した営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データがない場合の曜日ベースのフォールバック、部分的にしかデータがない場合でも一貫した挙動を担保するロジックを提供。
    - calendar_update_job を実装し、J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）経由で差分取得と冪等保存を行う。バックフィル・健全性チェックを備える。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインのユーティリティを実装。差分取得、保存（idempotent）、品質チェック（quality モジュール）を組み合わせる設計。
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors 等）を実装し、has_errors / has_quality_errors / to_dict を提供。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポートして公開インターフェースを簡素化。

- 基本設計・実装方針（横断的）
  - DuckDB を一次データストアとして使用（関数は DuckDB 接続を受け取る設計）。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() の不用意な参照を避け、全関数が target_date を明示的に受け取るように設計。
  - 外部 API 呼び出し（OpenAI、J-Quants）に対しては堅牢なリトライ/フォールバックを実装し、API の失敗が全体を停止させない設計。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT や ON CONFLICT を想定）し、部分失敗時に既存データを不必要に上書きしない設計を採用。
  - テスト容易性のため、OpenAI 呼び出し等はモック差し替え（パッチ）可能なよう分離して実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 限界事項
- OpenAI API キーは api_key 引数経由もしくは環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出する設計。
- ai/news_nlp と ai/regime_detector は共に gpt-4o-mini と JSON Mode を利用するが、内部で別個に API 呼び出し実装を持ち、相互にプライベート関数を共有しない設計（モジュール結合を低減）。
- DuckDB executemany に関する挙動（空リストを渡せない等）を考慮した実装を行っている。
- 外部クライアント実装（jquants_client 等）は別モジュール（kabusys.data.jquants_client）に依存しており、実運用では適切なクレデンシャル・API の準備が必要。

作者・貢献
- 初回リリース。

（以降のリリースでは変更点をこのファイルに追記してください。）