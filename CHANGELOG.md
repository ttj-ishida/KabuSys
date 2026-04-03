CHANGELOG
=========

すべての注目すべき変更履歴を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

フォーマット:
- 主要な変更はバージョンごとに分類
- 各バージョンでは Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで記載

Unreleased
----------
（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-03
-----------------

初期公開リリース。以下の主要機能と実装を含みます。

Added
-----
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を package-level に定義。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは以下をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式
    - シングル/ダブルクォート文字列のバックスラッシュエスケープ処理
    - インラインコメント処理（クォートなしでは '#' の直前が空白の場合のみコメントと判定）
  - 環境変数保護: OS 環境変数を protected として .env.local の上書きを制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視系 / システム設定をプロパティ経由で取得:
    - 必須項目取得時は未設定で ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - デフォルト値 (KABU_API_BASE_URL, ローカル DB パス等) を提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。
    - is_live / is_paper / is_dev ヘルパーを提供。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントをスコアリング。
    - 処理ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部では UTC naive datetime に変換）。
    - バッチ実行: 最大 20 銘柄/回、1 銘柄当たり最大 10 記事・3000 文字でトリム。
    - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" 配列、code の照合、数値変換、finite チェック。無効なレスポンスはスキップ。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは部分失敗対策として対象コードのみ DELETE → INSERT（トランザクションを使用）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector.score_regime
    - ETF 1321 の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除。
    - マクロ記事抽出はキーワードベース（日本・米国等の主要ワード）。記事が無い場合は LLM 呼び出しを行わず macro_sentiment=0.0。
    - OpenAI 呼び出しは json パース失敗・API エラー時に安全にフォールバック（macro_sentiment=0.0）し例外を上げない設計。
    - 結果は market_regime テーブルへ冪等性を保ってトランザクションで書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダーの管理機能（market_calendar）を提供。
    - 営業日判定（is_trading_day）、SQ判定（is_sq_day）、次/前営業日取得（next_trading_day / prev_trading_day）、範囲内営業日取得（get_trading_days）を実装。
    - DB に calendar データがない場合は曜日ベースのフォールバック（土日非営業日）。
    - next/prev_trading_day の最大探索範囲を _MAX_SEARCH_DAYS（60日）で制限し、見つからない場合は ValueError を送出。
    - calendar_update_job: J-Quants クライアント経由で差分取得して market_calendar を更新。バックフィル（日数指定）と健全性チェックを実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETLResult は取得数・保存数・品質問題・エラー一覧を保持し、has_errors / has_quality_errors プロパティと to_dict() を提供。
    - pipeline モジュールは差分取得・保存・品質チェックの設計方針を実装するためのユーティリティを含む（J-Quants クライアント・quality モジュールと連携）。

- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR/株価、20日平均売買代金、出来高比率を計算。必要行数未満は None を返す。
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算（EPS が 0/欠損のとき PER は None）。
    - 全関数は DuckDB を用いた SQL ベース実装で、prices_daily / raw_financials のみ参照し副作用なし。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実施。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。有効レコードが 3 未満なら None を返す。
    - rank: 同順位は平均ランクで扱い、丸め（round(v,12)）により浮動小数の ties 問題に対処。
    - factor_summary: count/mean/std/min/max/median を計算（None 値除外）。

Changed
-------
- （初期リリースのためなし）

Fixed
-----
- （初期リリースのためなし）

Deprecated
----------
- （初期リリースのためなし）

Removed
-------
- （初期リリースのためなし）

Security
--------
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は明示的に ValueError を送出して誤操作を防止。

Notes / 設計方針（重要）
---------------------
- ルックアヘッドバイアス回避: 主要な処理（AI スコアリング、レジーム判定、ETL、研究関数）は内部で datetime.today()/date.today() を参照せず、必ず target_date を受け取る設計。
- フェイルセーフ: 外部 API（OpenAI、J-Quants）失敗時は可能な限り部分的に継続し、致命的でない限り例外を上位に伝播させない（ログに警告を出す）。
- DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を確保。部分失敗時に他レコードを保護するため、対象コードのみを DELETE → INSERT で置換する実装。
- テスト容易性: OpenAI 呼び出し箇所は内部関数を patch して差し替え可能にしている。

開発上の注釈
--------------
- DuckDB を主要なデータ層として利用しており、executemany の空リスト取り扱い等、DuckDB バージョン依存の実装上の注意を考慮している。
- news_nlp と regime_detector は別々に OpenAI 呼び出し関数を持ち、モジュール間でプライベート関数を共有しない設計にしている（結合度低減）。

今後の予定（想定）
-----------------
- Strategy / execution / monitoring モジュールの実装拡張（現時点でパッケージのエクスポート名があるのみ）。
- 追加品質チェックや ETL の可視化・監査ログ強化。
- モデルやプロンプト改善による NLP スコアリング精度向上。