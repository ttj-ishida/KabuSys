CHANGELOG
=========

すべての注目する変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のパッケージバージョン: 0.1.0

Unreleased
----------

（なし）

0.1.0 - 2026-04-09
------------------

Added
-----

- 全体
  - 初回リリース。パッケージ名: kabusys。モジュール群（data, research, ai, execution, strategy, monitoring など）を公開。

- バージョニング・パッケージ初期化
  - src/kabusys/__init__.py: パッケージの __version__ を "0.1.0" に設定し、主要サブパッケージを __all__ で公開。

- 設定・環境変数管理
  - src/kabusys/config.py を実装。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ実装（export 句対応、クォート内のバックスラッシュエスケープ、行内コメント処理など）。
    - Settings クラスを提供。主要プロパティ:
      - jquants_refresh_token, kabu_api_password（必須。未設定時は ValueError を送出）
      - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
      - LINE 関連（line_channel_access_token, line_user_id）
      - DB パス（duckdb_path: data/kabusys.duckdb、sqlite_path: data/monitoring.db、paper_sqlite_path）
      - Paper Trading 設定（paper_fill_mode: instant|partial|never|reject のバリデーション）
      - 監視関連（pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/MEM/DISK の閾値）
      - 環境・ログレベル検証（KABUSYS_ENV は development/paper_trading/live、LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データプラットフォーム（Data）: カレンダー管理
  - src/kabusys/data/calendar_management.py を実装。
    - market_calendar を参照する営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - カレンダーデータが存在しない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS = 60）で無限ループ防止。
    - calendar_update_job: J-Quants クライアント経由で差分取得 → 冪等保存（fetch / save を呼び出し、健全性チェック・バックフィル処理あり）。
    - market_calendar における NULL 値や極端な未来日付に対する警告ログ出力などの堅牢性チェックを実装。

- データプラットフォーム（Data）: ETL パイプライン
  - src/kabusys/data/pipeline.py を実装。
    - ETLResult データクラスを公開（ETL の取得数・保存数、品質チェック結果、エラー一覧などを格納）。
    - ETL ジョブの方針（差分更新、バックフィル、品質チェックの収集と続行）を実装設計に反映。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- 研究（Research）: ファクター計算・特徴量解析
  - src/kabusys/research/factor_research.py を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算（データ不足時は None を返す、DuckDB のウィンドウ関数を活用）。
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio を計算（NULL の取り扱いに注意）。
    - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算（EPS が 0 や欠損の際は None）。
    - 設計方針: DuckDB 接続のみを使用、外部 API にアクセスしない、(date, code) キーの辞書リストで結果返却。
  - src/kabusys/research/feature_exploration.py を実装。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（ホライズン検証あり）。
    - calc_ic: ファクターと将来リターン間の Spearman ランク相関（IC）を計算。十分なサンプルがない場合は None。
    - rank: 同順位は平均ランクで処理（round(v, 12) により浮動小数の丸め誤差に対処）。
    - factor_summary: count/mean/std/min/max/median を計算。None 値は除外。
  - src/kabusys/research/__init__.py で主要関数を公開。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py を実装。
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - ニュース収集ウィンドウの計算（JST: 前日15:00〜当日08:30 → UTC に変換）を calc_news_window として公開。
    - バッチサイズ、記事数上限、文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）などを実装。
    - レスポンスは厳密な JSON を期待するが、前後ノイズがある場合は最外の {} を抽出して復元を試みる処理を実装。
    - バリデーションを行い、有効なコードのみ ai_scores テーブルへ置換（DELETE → INSERT）で書き込み。部分失敗時に既存スコアを保護する実装。
    - score_news は書き込んだ銘柄数を返す。また API キー未設定時は ValueError。
    - OpenAI 呼び出し箇所はテスト時に差し替え可能（_call_openai_api を patch 可能）。
  - src/kabusys/ai/regime_detector.py を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を統合して market_regime（'bull'/'neutral'/'bear'）を日次判定。
    - ma200_ratio の計算、マクロキーワードによるニュース抽出、OpenAI による macro_sentiment 評価（gpt-4o-mini、JSON Mode）を実装。
    - OpenAI 呼び出し失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）、API 呼び出しはリトライ/バックオフを行う。
    - レジームスコアはクリップされ、閾値に基づきラベル化。結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。API キー未設定時は ValueError。
    - OpenAI 呼び出しは news_nlp とは独立実装（モジュール結合を避ける設計）。テスト時の差し替えも可能。

- テスト性・堅牢性
  - OpenAI 呼び出しを関数単位で差し替え可能にしてユニットテスト容易化。
  - 各所でリトライとログ出力を実装し、API 異常時に処理を継続するフェイルセーフ方針を採用。
  - DuckDB に対する executemany の空パラメータ問題を考慮し、空時は実行をスキップするガードを追加。

Changed
-------

- 初回リリースのため該当なし。

Fixed
-----

- 初回リリースのため該当なし。

Deprecated
----------

- 初回リリースのため該当なし。

Removed
-------

- 初回リリースのため該当なし。

Security
--------

- 現時点で既知のセキュリティ修正はありません。API キー等の機密情報は Settings 経由で環境変数から取得する設計です。自動 .env 読み込み動作は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能です。

Notes / 今後の改善候補
--------------------

- OpenAI モデルや挙動（タイムアウト/バッチサイズ等）は将来の運用でチューニングされる想定です。
- news_nlp/regime_detector のプロンプトやキーワードリストは運用に合わせ改善の余地あり。
- ETL/カレンダー関連は J-Quants クライアントの挙動や API 変更に依存するため、API 仕様変更時に適宜対応が必要です。

--- 

このリリースに関する質問や追記したい点があれば教えてください。