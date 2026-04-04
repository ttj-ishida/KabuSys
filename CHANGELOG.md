CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※この CHANGELOG はリポジトリ内のソースコードから機能・挙動を推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。

- 環境設定管理
  - src/kabusys/config.py
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能にした。
      - J-Quants / kabu ステーション / LINE / データベース / 監視 / システム設定用のプロパティを提供（例: jquants_refresh_token, kabu_api_password, duckdb_path, pid_file_path, env, log_level など）。
    - .env 自動読み込み機能を追加
      - プロジェクトルートを .git または pyproject.toml から決定する _find_project_root() を実装し、CWD に依存しない自動読み込みを実現。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env のパースは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
      - .env 読み込み時、既存 OS 環境変数を protected として上書きから保護する仕組みを導入。
    - 入力検証
      - 必須環境変数未設定時は _require() が ValueError を投げる（利用者向けに .env.example の参照を促すメッセージ）。
      - KABUSYS_ENV と LOG_LEVEL の値を限定し、不正な場合は ValueError を発生させる。

- AI 関連：ニュース NLP（センチメント）および市場レジーム判定
  - src/kabusys/ai/news_nlp.py
    - score_news(conn, target_date, api_key=None) を提供。
      - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づいて raw_news / news_symbols を集計し、銘柄ごとにニュースを統合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
      - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）。
      - 1 銘柄あたり最大記事数・文字数のトリム(_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK) によりトークン肥大化を抑制。
      - JSON Mode を利用し、レスポンスを厳密に検証。429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ。部分失敗しても他銘柄の結果を保護するよう ai_scores テーブルは対象コードのみ DELETE → INSERT を実施（冪等性）。
      - 成功時は書込んだ銘柄数を返す。APIキー未設定時は ValueError を送出。
      - フェイルセーフ: API エラーやパース失敗時は該当チャンクをスキップして継続。
    - calc_news_window(target_date) を提供（UTC naive datetime を返す）。
    - 内部での実装方針として datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを避ける設計。
  - src/kabusys/ai/regime_detector.py
    - score_regime(conn, target_date, api_key=None) を提供。
      - ETF 1321 の直近 200 日終値から MA200 乖離（ma200_ratio）を計算し（_calc_ma200_ratio）、マクロ経済ニュースの LLM センチメントと重み付けでレジームスコアを合成（MA 重み 0.7、マクロ重み 0.3）。
      - マクロニュースの取得は raw_news に対するマクロキーワードフィルタを実施（_MACRO_KEYWORDS）。
      - OpenAI 呼び出しは JSON レスポンスを期待し、Retry、エラー種別の分岐（RateLimit, Connection, Timeout, APIError）に対応。障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - regime_label を bull/neutral/bear で分類し、market_regime テーブルへ冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込み。
      - API キー未指定時は ValueError を投げる。

  - 共通の設計方針（両モジュール）
    - OpenAI 呼び出しは client.chat.completions.create(..., response_format={"type": "json_object"}) を使用。
    - テスト時に _call_openai_api を patch して差し替え可能な設計。
    - レスポンス検証・パース失敗のロギングとフォールバック挙動が実装されている。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。データ不足時は None を返す。SQL ベースで DuckDB にて高速に計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。NULL 序列に対する扱い（tr の NULL 伝播）を明示的に制御。
    - calc_value(conn, target_date): raw_financials から最新の財務を結合し PER / ROE を算出（EPS が 0またはNULL の場合は None）。
    - DuckDB のウィンドウ関数等を利用した実装で、副作用は無し（prices_daily/raw_financials の参照に限定）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを一度に取得。horizons の検証（正の整数、<=252）を行う。
    - calc_ic(...): factor と forward return の Spearman ランク相関（IC）を計算。有効レコードが 3 件未満のときは None。
    - rank(values): 同順位は平均ランクを与えるランク関数（round(..., 12) により浮動小数の丸め誤差を緩和）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計ユーティリティ。

- データ層（カレンダー管理・ETL）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を提供。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを実装。
      - market_calendar テーブルの有無や未登録（NULL）値に応じた曜日ベースのフォールバックを採用し、一貫性を維持。
      - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得して market_calendar を冪等に更新する（バックフィル・健全性チェックあり）。jquants_client 経由で fetch と save を行う。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを導入し ETL 実行結果（取得数、保存数、品質問題、エラー概要）を表現可能にした。
    - ETL の設計方針（差分更新、バックフィル、品質チェック、idempotent 保存）をコードに反映。
    - 内部ユーティリティとしてテーブル存在確認や最大日付取得などのヘルパー関数を追加。
    - etl モジュールは pipeline.ETLResult を公開再エクスポート。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError で明示的に失敗することで、不意のデータ書き込みや誤動作を防止。

Notes / 実装上の重要点（ドキュメントに反映推奨）
- ルックアヘッドバイアス回避: AI モジュールや ETL/リサーチ系は内部で datetime.today()/date.today() を参照せず、呼び出し側が target_date を渡す設計。再現性のあるバッチ処理を想定。
- DB 書き込みは可能な限り冪等（DELETE → INSERT / ON CONFLICT 形式）にしており、部分失敗時に既存データを不必要に消さない工夫がある（ai_scores や market_regime 等）。
- DuckDB の executemany に関する互換性（空リストを渡せない点）を考慮したガードあり。
- OpenAI 呼び出しは JSON モードを前提にレスポンスの厳密検証を行うが、パース失敗時の回復措置（JSON 抽出）も実装。

補足
- 上記は現行ソースコードから推測して作成した CHANGELOG です。実際のリリースノートとして公開する際は、実際のリリース日・変更履歴（コミットやマージ単位）に基づく追記・修正を推奨します。