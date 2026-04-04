Keep a Changelog 準拠 — 変更履歴 (日本語)
======================================

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングに従います。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期リリース
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で特定）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パースの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートのエスケープ処理対応。
    - インラインコメントの取り扱い（クォートあり/なしでの挙動）。
    - 無効行のスキップと警告出力。
  - 上書きポリシー:
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - .env.local は override=True（ただし OS 環境変数は保護）。
  - Settings クラスを提供（settings インスタンス経由で取得可能）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須取得メソッド（未設定時は ValueError）。
    - KABU_API_BASE_URL, LINE_API 関連、データベースパス（DUCKDB_PATH, SQLITE_PATH）等の既定値。
    - 監視用設定（PID ファイル/kill flag、閾値: CPU/MEM/DISK 等）。
    - 環境（KABUSYS_ENV）のバリデーション（'development' / 'paper_trading' / 'live'）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP（OpenAI 統合） (src/kabusys/ai/news_nlp.py)
  - score_news(conn, target_date, api_key=None):
    - 前日 15:00 JST ～ 当日 08:30 JST の記事を対象に、銘柄ごとのセンチメント（-1.0～1.0）を算出して ai_scores テーブルへ書き込み。
    - calc_news_window(target_date) によるウィンドウ計算（UTC naive datetime を返す）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最新 _MAX_ARTICLES_PER_STOCK 件、文字数トリム）。
    - 1 API コールで最大 _BATCH_SIZE（デフォルト 20）銘柄をバッチ処理。
    - OpenAI (gpt-4o-mini) の JSON Mode を使用、response_format による厳密 JSON 想定。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（リトライ実装）。
    - レスポンスのバリデーション（results 配列, code/score の存在チェック、未知コードの無視、数値チェック、±1.0でクリップ）。
    - 部分失敗に備え、書込みは対象コードのみを DELETE → INSERT（冪等性と既存データ保護）。
    - API キー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError。
    - API 呼び出し失敗時は該当チャンクをスキップして継続（フェイルセーフ、例外を上げない設計）。

- 市場レジーム判定（AI + MA 合成） (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None):
    - ETF 1321（日経225連動）の直近 200 日終値から MA200 乖離（ma200_ratio）を計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロ経済キーワードで raw_news をフィルタし、最大 _MAX_MACRO_ARTICLES 件のタイトルを取得。
    - OpenAI (gpt-4o-mini) でマクロセンチメントを -1.0～1.0 に評価（記事がない場合は LLM 呼び出しを行わず 0.0）。
    - レジームスコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)（MA 重み 0.7、マクロ重み 0.3、MA スケール 10）。
    - スコア閾値により regime_label を 'bull' / 'neutral' / 'bear' と判定。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）。
    - API エラー時は macro_sentiment=0.0 にフォールバック（警告ログを出力し例外を投げない）。
    - API キー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError。

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum(conn, target_date):
      - mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離率）を計算。データ不足時は None。
    - calc_volatility(conn, target_date):
      - atr_20（20日 ATR）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。データ不足は None。
    - calc_value(conn, target_date):
      - raw_financials から最新財務データ（report_date <= target_date）を取得し、PER / ROE を計算。EPS が 0 または欠損なら PER は None。
    - 設計方針:
      - DuckDB 上の prices_daily / raw_financials のみを参照し、外部 API や発注とは独立。
      - 結果は (date, code) をキーとする dict のリストで返す。
      - Z スコア正規化ユーティリティは kabusys.data.stats から提供。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns(conn, target_date, horizons=None):
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンが不正なら ValueError。
    - calc_ic(factor_records, forward_records, factor_col, return_col):
      - スピアマンのランク相関（IC）を計算。十分な有効レコードがない場合は None。
    - factor_summary(records, columns):
      - count/mean/std/min/max/median を算出。
    - rank(values):
      - 同順位は平均ランクで扱うランク変換。

- データ（Data）モジュール (src/kabusys/data/)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを実装。
    - market_calendar テーブルが存在する場合は DB の値を優先、未登録日は曜日(土日)ベースでフォールバック。
    - next/prev_trading_day は最大探索日数 (_MAX_SEARCH_DAYS) を設定して無限ループ回避。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS):
      - J-Quants API から差分取得し market_calendar を冪等更新（fetch -> save）。バックフィル日数や健全性（将来日付の異常検出）を備える。
    - 設計方針: DB 登録あり→DB優先、なし→曜日フォールバックで一貫した結果を返す。

  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加（target_date, fetched/saved counts, quality_issues, errors 等）。
    - ETLResult.to_dict() で quality_issues を辞書化して返却可能。
    - 差分更新・バックフィル・品質チェック（quality モジュールとの連携）を想定した設計ノートを実装。
    - jquants_client を使った保存処理との連携を想定。

  - jquants_client 等のクライアント層と連携するコードを想定した設計となっている（実装ファイルは data パッケージ内で参照）。

- パッケージの公開インターフェース整理
  - ai, research の __init__ で主要関数をエクスポート（例: kabusys.ai.score_news / score_regime, kabusys.research.calc_momentum など）。
  - data.etl は ETLResult を再エクスポート。

Security
- 環境変数の取り扱いで OS 環境変数を保護する仕組みを導入（.env.local 等で上書きされないよう保護）。

Notes / Design principles
- ルックアヘッドバイアス防止:
  - 日付依存の処理は datetime.today()/date.today() を内部で参照しない設計。
  - DB クエリは target_date 未満（排他）や LEAD/LAG を用いて将来データ参照を防止。
- フェイルセーフ設計:
  - 外部 API（OpenAI/J-Quants）失敗時は可能な限りフォールバックして継続（例: macro_sentiment=0.0、チャンク単位でのスキップ）。
- 冪等性:
  - DB 書込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT を想定）で実装。
- DuckDB を主なストレージとして使用。executemany の制約（空リスト不可）に配慮した実装あり。
- ロギングを多用し、失敗時には警告/例外ログを出力。

Breaking Changes
- 初版リリースのため該当なし。

Acknowledgements / Requirements
- OpenAI API (gpt-4o-mini) を用いる機能は環境変数 OPENAI_API_KEY または関数引数 api_key のいずれかが必須。
- J-Quants / kabu API を利用するには JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の設定が必要。
- デフォルトのデータベースファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

今後の予定（例）
- ai モジュールのテスト用モックの整備（現在は _call_openai_api を patch する想定）。
- jquants_client / quality モジュールの詳細実装と ETL パイプライン統合。
- 追加ユーティリティ（監視・実行モジュール）の公開。

-----