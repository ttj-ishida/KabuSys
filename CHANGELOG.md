CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。フォーマットは「Keep a Changelog」準拠です。

フォーマット方針
- 日付はリリース日を示します。
- セクション: Added / Changed / Fixed / Deprecated / Removed / Security

Unreleased
----------
（無し）

0.1.0 - 2026-04-04
-----------------

Added
- 基本情報
  - 初期リリース: KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に検出。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。OS 環境変数は保護（上書き防止）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォート無しは '#' の直前が空白/タブでコメント扱い）
  - Settings クラスを提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須設定チェック（未設定時は ValueError）
    - KABU_API_BASE_URL, LINE_* トークン、データベースパス（duckdb/sqlite）等のデフォルト値
    - CPU/MEM/DISK閾値、PID/KILL フラグ関連パス
    - 環境（KABUSYS_ENV）の検証（development/paper_trading/live）とログレベル検証

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価。
  - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB と比較）。
  - バッチ処理: 最大 20 銘柄/チャンク、1銘柄あたり最大 10 記事・3000 文字にトリム。
  - OpenAI へのリトライ／バックオフ実装（429・ネットワーク断・タイムアウト・5xx を対象）。
  - レスポンスの厳格なバリデーション（JSON モードの不整合や余分な前後文字列に対する復元処理を含む）。
  - スコアは ±1.0 にクリップし、結果を ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。
  - 公開関数: score_news(conn, target_date, api_key=None)

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）。
  - マクロニュースはニュース NPL モジュールのウィンドウ計算を利用し、キーワードフィルタで抽出。
  - OpenAI 呼び出し: gpt-4o-mini、JSON mode、リトライ／エラー時は macro_sentiment=0.0 でフェイルセーフ。
  - レジームスコアはクリップし閾値でラベル付け、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 公開関数: score_regime(conn, target_date, api_key=None)

- データ関連ユーティリティ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分取得バッチ（calendar_update_job）と市場日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の API を提供。
    - market_calendar が未取得のケースに対する曜日ベースのフォールバック（週末を休日扱い）。
    - 最大探索日数制限を設け、無限ループを防止。
    - J-Quants クライアント経由で取得・保存（fetch_market_calendar / save_market_calendar を使用）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ターゲット日、取得数/保存数、品質問題、エラー一覧等を保持）。
    - 差分取得・バックフィル方針、品質チェック統合の設計（詳細は module docstring に記載）。
    - DuckDB 互換性考慮（executemany の空リスト回避など）。

- リサーチ／ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。必要行数不足時は None。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算。価格は prices_daily の終値を使用。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンは営業日ベース。
    - calc_ic: Spearman（ランク）による Information Coefficient を計算（有効レコードが 3 件未満なら None）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出（None 値は除外）。
    - rank: 同順位は平均ランクを与えるランク関数（丸めで ties を安定化）。

Design / Safety / Implementation notes
- ルックアヘッドバイアス対策:
  - 主要モジュール（news_nlp, regime_detector 等）は datetime.today() / date.today() を内部的に参照せず、必ず caller が target_date を渡す設計。
  - SQL クエリも target_date 未満／排他条件等でルックアヘッドを防止するよう注意。
- DB 書き込み:
  - 冪等性を重視（DELETE→INSERT、ON CONFLICT の代替手段など）。
  - トランザクション（BEGIN / COMMIT / ROLLBACK）を用いて整合性を保つ。ROLLBACK に失敗した場合は警告ログ出力。
- OpenAI 統合:
  - モデル: gpt-4o-mini を想定。JSON mode を使い厳格な JSON 出力を期待。
  - リトライ戦略: 指定の例外（RateLimitError, APIConnectionError, APITimeoutError, サーバー5xx）に対して指数バックオフで再試行。非 5xx の APIError やパースエラー時はフェイルセーフ（ゼロスコアやスキップ）。
  - レスポンスのバリデーションとクリッピング（スコアは有限値かつ指定レンジ内に制限）。
- DuckDB 互換性配慮:
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約対策）。
  - 日付値は明示的に date 型へ変換して扱うユーティリティを提供。
- ロギング:
  - 各処理は適切な情報ログ、警告、例外ロギングを行い可観測性を確保。

Changed
- 初版のため無し。

Fixed
- 初版のため無し。

Deprecated
- 初版のため無し。

Removed
- 初版のため無し。

Security
- 初版のため無し。

補足
- 公開 API のうち、AI 系機能は OpenAI API キー（引数もしくは環境変数 OPENAI_API_KEY）が必要。未設定時は ValueError を送出する。
- 一部モジュール（jquants_client 等）の実体はこの差分に依存するが、本リリースではインターフェース呼び出しを前提とした実装になっています。実行に際しては必要な外部クライアント実装と DuckDB スキーマの準備が必要です。