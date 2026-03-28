Keep a Changelog に準拠した CHANGELOG.md（日本語）
==============================================

すべての重要な変更・追加はここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

0.1.0 - 2026-03-28
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にてパッケージ名とバージョン __version__="0.1.0" を設定。
    - __all__ に data, strategy, execution, monitoring を公開（将来のサブパッケージ用エントリ）。
  - 環境設定管理
    - src/kabusys/config.py
      - .env/.env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml に基づく）。
      - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env パーサの強化:
        - export KEY=val 形式対応
        - シングル/ダブルクォート文字列のバックスラッシュエスケープ処理対応
        - クォートなし行のインラインコメント処理（'#' の前が空白またはタブの場合はコメント扱い）
      - 環境値取得用 Settings クラスを提供:
        - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティ（必須変数は _require で未設定時 ValueError を投げる）
        - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）
        - デフォルトの DuckDB/SQLite パス設定と is_live / is_paper / is_dev の補助プロパティ
  - AI ニュース/NLP
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄単位のセンチメントスコアを算出。
      - バッチ処理（_BATCH_SIZE=20）・1銘柄あたり記事上限制御（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - JSON Mode を利用したレスポンス検証とパース復元（余分な前後テキストを含む場合に最外の {} を抽出）。
      - リトライ/指数バックオフ（429、ネットワーク断、タイムアウト、5xx）を実装し、失敗時はフェイルセーフでスキップ。
      - スコアを ±1.0 にクリップ。
      - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション、ROLLBACK 保護）。
      - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。API キーは引数または OPENAI_API_KEY 環境変数で指定。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
      - マクロニュース抽出（マクロキーワード一覧）→ OpenAI 呼び出し（gpt-4o-mini、JSON Mode）→ スコア合成と閾値判定。
      - API 失敗時は macro_sentiment = 0.0 とするフェイルセーフ、リトライ/バックオフ実装。
      - DuckDB の market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK 保護）。
      - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時 1 を返す。API キーは引数または OPENAI_API_KEY 環境変数で指定。
    - ai パッケージ公開
      - src/kabusys/ai/__init__.py で score_news をエクスポート。
  - データプラットフォーム（Data）
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理: market_calendar テーブルを基にした営業日判定・前後営業日の取得・期間内営業日の列挙（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - DB データが不足する場合は曜日ベースでフォールバック（土日非営業日扱い）。
      - カレンダー夜間更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装（J-Quants API から差分取得 → save_market_calendar 呼び出し、バックフィル・健全性チェックあり）。
      - 最大探索日数上限（_MAX_SEARCH_DAYS）やバックフィル日数、先読み日数等の安全設計。
    - src/kabusys/data/pipeline.py
      - ETL パイプライン用ユーティリティと ETLResult データクラスを実装。
      - 差分更新、バックフィル、品質チェックの設計方針に準拠した構造を提供。
      - ETLResult は取得数・保存数・品質問題・エラー一覧を保持し、has_errors / has_quality_errors / to_dict を提供。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
    - data パッケージ及び jquants_client 参照（jquants_client は外部クライアント実装前提）。
  - 研究用モジュール（Research）
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value 等の量的ファクター計算を実装:
        - calc_momentum(conn, target_date): 1m/3m/6m リターン、200 日 MA 乖離（データ不足時は None）。
        - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比率等。
        - calc_value(conn, target_date): PER（EPS が 0 或いは欠損で None）、ROE（raw_financials から最新報告を取得）。
      - DuckDB SQL を活用して効率的に計算、戻り値は (date, code) キーの辞書リスト。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）、ホライズン検証（1..252）、1 クエリでまとめて取得。
      - IC（Information Coefficient）計算 calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関を実装（同順位は平均ランク処理）。
      - 統計サマリー factor_summary(records, columns) — count/mean/std/min/max/median を算出。
      - rank(values) ユーティリティ（小数丸めで ties を安定的に扱う）。
    - research パッケージ公開
      - src/kabusys/research/__init__.py で主要関数とデータユーティリティをエクスポート（zscore_normalize は kabusys.data.stats から再利用）。
  - ログ & エラー処理
    - 各モジュールにおいて詳細な logger メッセージを追加（情報ログ・警告・例外時の例外ログ）。
    - DB 書き込みはトランザクションを基本とし、例外時に安全に ROLLBACK を試行する設計。

Changed
- 新規リリースのため変更履歴なし。

Fixed
- 新規リリースのため修正履歴なし。

Security
- OpenAI API キーは引数で注入可能（テスト容易性向上）かつ環境変数 OPENAI_API_KEY による解決をサポート。キー未設定時は明確な ValueError を送出して漏洩リスクを低減。
- .env 読み込み時に OS 環境変数を保護する実装（protected set）を導入。

Notes / Known limitations
- jquants_client や外部 API クライアント（kabu API・Slack 送信処理等）は本スニペット内で参照しているが、実装は別モジュール（外部）に依存します。
- strategy / execution / monitoring サブパッケージの実装はこのリリースではスニペットに含まれていない可能性があります（将来的に追加予定）。
- 一部関数は入力データが不足する場合に None を返す設計です（使用側での扱いに注意してください）。
- 日付取り扱いは意図的に target_date ベースで実行し、datetime.today()/date.today() の直接参照を避けてルックアヘッドバイアスを防止しています（一部ジョブは内部で date.today() を利用、calendar_update_job 等は運用上のルールによる）。

開発者向けメモ
- テスト容易性のため、OpenAI 呼び出し部分（各モジュールの _call_openai_api）を unittest.mock.patch で差し替える設計になっています。
- DuckDB executemany に関する互換性（空リスト不可）を考慮した実装が含まれています。
- ロジックの多くは SQL（DuckDB）で実行されるため、性能やスキャン範囲は定数で制御されています（例: _MOMENTUM_SCAN_DAYS, _VOLATILITY_SCAN_DAYS 等）。

今後の予定（例）
- strategy / execution / monitoring の具象実装と発注ロジックの統合。
- jquants_client と kabu ステーションクライアントの実装・テスト。
- 追加の品質チェックルールと監視アラートの充実。

（以上）