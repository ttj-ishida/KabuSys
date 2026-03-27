CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。
このプロジェクトの初期リリースを含む変更履歴を日本語でまとめます。

フォーマット:
- Added: 新機能
- Changed: 変更点（移行注意など）
- Fixed: 修正
- Removed: 削除
- Security: セキュリティ関連

[Unreleased]
------------

（次のリリースに向けた変更点をここに記載します）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース "KabuSys"（バージョン 0.1.0）
  - パッケージ公開情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブパッケージを定義。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み優先度: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込み無効化可能。
    - .env パーサ実装（クォート / エスケープ / コメントの扱いを考慮）。
    - Settings クラスを公開（settings）。J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live） / ログレベル等の取得をプロパティで提供。
    - 必須変数未設定時は ValueError を送出する _require 関数。

- AI（LLM）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を使ってニュースごとのセンチメントを算出。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数／文字数）やレスポンスバリデーションを実装。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）、エラー時はフェイルセーフでスキップ。
    - score_news(conn, target_date, api_key=None) を公開。ai_scores テーブルへの冪等的な書き換え（DELETE→INSERT）を行う。
    - calc_news_window(target_date) により JST 時間窓（前日 15:00 ～ 当日 08:30）を UTC タイムスタンプで計算。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（225 連動 ETF）の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しと再試行、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - score_regime(conn, target_date, api_key=None) を公開し、market_regime テーブルへ冪等書き込みを行う。
    - ルックアヘッドバイアス対策（datetime.today() を参照せず、価格・ニュースは target_date 未満のみを参照）。

- Data（データ基盤）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の読み書き、営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job(conn, lookahead_days=90) による J-Quants からの差分取得と冪等保存（fetch / save 呼び出し）を実装。
    - DB データがない場合は曜日ベース（土日除外）のフォールバックを行う。探索の最大日数制限を設定して無限ループを防止。

  - src/kabusys/data/pipeline.py
    - ETL の高レベル設計に基づくユーティリティと ETLResult データクラスを実装。
    - 差分取得、バックフィル、品質チェック（quality モジュール参照）を想定した設計。ETL 実行結果を保持する ETLResult (to_dict, has_errors, has_quality_errors) を提供。
    - 内部補助関数（テーブル存在チェック、最大日付取得、カレンダー調整）を実装。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート（公開インターフェース）。

  - data モジュール内で jquants_client（外部クライアント）を利用する形で設計（fetch/save の抽象化）。

- Research（リサーチ）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum / Value / Volatility / Liquidity）を実装。
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials の最新財務を使って PER / ROE を算出。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API には影響しない設計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターンを一度のクエリで計算する。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を計算。3 件未満なら None。
    - rank(values): 同順位は平均ランクとするランク変換。丸めを入れて ties の検出安定化を実装。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計ユーティリティ。
    - research パッケージは data.stats の zscore_normalize を再利用している（src/kabusys/research/__init__.py）。

- 公開 API の整理
  - 各パッケージ内で主要関数を __all__ でエクスポート（例: ai.score_news / ai.score_regime の公開、research の関数一覧）。

Changed
- 初回リリースのため該当項目なし。

Fixed
- 初回リリースのため該当項目なし。

Removed
- 初回リリースのため該当項目なし。

Security
- OpenAI API キー取り扱い:
  - score_news / score_regime は api_key 引数を受け付けるか、環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して処理を中断。
  - .env 自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すること（1）。

Notes / 実装上の重要点（ユーザ向け）
- ルックアヘッドバイアス防止:
  - AI・レジーム・研究系の関数は内部で datetime.today() を参照せず、常に呼び出し時に明示した target_date を基準にデータ（date < target_date など）を扱う設計。
- フェイルセーフ:
  - LLM 呼び出しでエラーやパース失敗が発生した場合、多くの箇所で例外を投げずにフォールバック（例えば macro_sentiment=0.0、スコア取得失敗はスキップ）して処理を続行するように実装されています。呼び出し側でのエラーハンドリング設計を推奨します。
- DuckDB の互換性:
  - executemany に空リストを渡せないバージョン対策など、DuckDB（0.10 系など）との互換性を考慮した実装が含まれています。
- デフォルトパス:
  - DuckDB と SQLite のデフォルトパスはそれぞれ data/kabusys.duckdb、data/monitoring.db。環境変数で上書き可能（DUCKDB_PATH / SQLITE_PATH）。
- カレンダーデータのフォールバック:
  - market_calendar テーブルが未取得・不足の場合、営業日判定は土日ベースでフォールバックしますが、DB に登録されている日付がある場合はそちらを優先します。

既知の制約・今後の改善候補
- AI モデルやプロンプトのチューニング、バッチの最適化（遅延やトークンコスト削減）。
- AI レスポンスのさらなる堅牢化（異常応答の検出・自動修復）。
- ETL 内での品質チェック結果に基づく自動アクション（現状は結果収集に留める設計）。
- raw_financials に基づく PBR・配当利回りの未実装（将来実装予定）。

署名
- 初期公開リリース: KabuSys チーム（ソース内モジュール群に基づいて作成）