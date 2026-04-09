Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-09
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を導入。
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義
    - パブリック API: data, strategy, execution, monitoring をエクスポート想定

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは以下に対応:
    - コメント行、export KEY=val 形式、シングル/ダブルクォート（エスケープ対応）、インラインコメントの扱い（クォートあり/なしでの差別処理）。
  - _load_env_file で OS 環境変数を保護する protected 機能を実装（.env.local による上書きも可能）。
  - Settings クラスでアプリケーション設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目チェック（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL, LINE 関連トークン、データベースパス（duckdb/sqlite）、Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）等のデフォルト値と妥当性チェック。
    - 監視用設定（pid ファイル, kill flag, CPU/メモリ/ディスク閾値）をサポート。
    - 環境（KABUSYS_ENV）および LOG_LEVEL の妥当性検査、is_live/is_paper/is_dev ヘルパー。

- データ基盤（src/kabusys/data/*）
  - calendar_management:
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 夜間バッチ: calendar_update_job により J-Quants から差分取得／冪等保存（fetch/save の呼び出しと健全性チェック）。
    - 最大探索日数やバックフィル、健全性チェック（未来日付の異常検出）を導入。
  - pipeline / etl:
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー集計など）。
    - ETL フロー設計に基づく差分取得、バックフィル、品質チェック（quality モジュール連携想定）。
    - jquants_client 経由の idempotent 保存（ON CONFLICT を想定）を前提とした処理。
  - etl モジュールは ETLResult を公開再エクスポート。

- AI（src/kabusys/ai/*）
  - news_nlp:
    - score_news: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄単位にセンチメントを算出し、ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/API コール）、1 銘柄あたりの記事数/文字数制限、JSON Mode を想定したレスポンスバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。致命的でない失敗時はスキップして継続するフェイルセーフ設計。
    - レスポンス検証で未知コードや数値以外のスコアを無視し、スコアは ±1.0 にクリップ。
    - テスト用フック: _call_openai_api を patch で差し替え可能。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる原文記事フィルタ、OpenAI 呼び出し（gpt-4o-mini）、API リトライ/フォールバック（失敗時 macro_sentiment=0.0）、およびスコア合成ロジックと閾値実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を用いた冪等操作。失敗時は ROLLBACK および上位へ例外伝播。
    - テスト可能性のため news_nlp と異なる _call_openai_api 実装に分離。

- Research（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時の None 処理、DuckDB SQL 実装）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（NULL 伝播に注意した true_range 計算）。
    - calc_value: raw_financials から過去最新の財務指標を取得して PER/ROE を計算。
    - 全関数は prices_daily / raw_financials のみ参照し、本番発注には影響しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン後の将来リターン（複数ホライズン対応、入力検証あり）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算（None や ties を考慮）。
    - rank: 平均ランク（同順位は平均ランク）実装（丸めによる ties 対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median 計算。
  - research パッケージは主要関数を再エクスポート（zscore_normalize を含む）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- 環境変数の自動ロードにおいて OS 環境変数を保護する仕組み（protected set）を導入し、.env による意図せぬ上書きを防止。

Notes / 実装上の設計方針（要点）
- ルックアヘッドバイアス防止: 日付計算は datetime.today()/date.today() を直接参照せず、外部から与えた target_date に依存する実装が多い（AI モジュール・リサーチモジュールなど）。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は例外で即停止せず、可能な範囲で安全に継続（ログ出力とゼロ値フォールバック）する方針。
- 冪等性: DB への書き込みは既存行の置換（DELETE→INSERT、または ON CONFLICT を想定）で冪等性を確保。
- テスト容易性: OpenAI 呼び出し等は内部関数を patch で差し替えられるように設計。

既知の制限
- 一部の外部モジュール（jquants_client, quality, strategy, execution, monitoring 等）はこの差分では実装詳細を含まずインターフェース前提で記述されている。
- DuckDB のバージョン差異により list 型バインド等で振る舞い差があるため、executemany を用いた互換性対策が入っている。

作者 / 貢献
- 初期実装（コードベースの追加）に基づく初回公開。

---