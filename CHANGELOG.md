CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。
リリース日は ISO 形式 (YYYY-MM-DD) で記載しています。

0.1.0 - 2026-03-28
-----------------

Added
- 初回リリース。パッケージ名: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py
    - パッケージのバージョンと公開サブパッケージを定義。
- 環境設定 / 設定読み込み
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD 非依存）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント扱いをサポート。
      - .env 読み込み時、既存 OS 環境変数を保護するため protected キー集合を利用。
    - Settings クラスを提供（settings インスタンス経由で利用）。
      - 必須設定の取得メソッド（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）とパス系設定（DUCKDB_PATH, SQLITE_PATH）。
      - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の値検証。
      - ヘルパー: is_live / is_paper / is_dev。
- AI: ニュース NLP と市場レジーム判定
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出して ai_scores テーブルへ書き込み。
    - 特徴:
      - タイムウィンドウの計算（前日15:00 JST ～ 当日08:30 JST を UTC で変換）。
      - 1 銘柄あたり最大記事数・最大文字数でのトリム（トークン肥大化対策）。
      - 最大バッチサイズ（_BATCH_SIZE=20）で複数銘柄をバッチ送信。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフとリトライ。
      - レスポンスの厳密なバリデーション（results 配列・code/score 検証・スコア有限性検査）。
      - スコアは ±1.0 にクリップ。
      - 書き込みは部分失敗に強い設計（DELETE→INSERT の対象コード絞り込み、トランザクション、ROLLBACK 保護）。
    - 公開 API: score_news(conn, target_date, api_key=None) -> 書込み銘柄数
    - calc_news_window(target_date) ユーティリティを提供。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（"bull"/"neutral"/"bear"）を判定し、market_regime テーブルへ冪等的に保存。
    - マクロニュースは news_nlp.calc_news_window を利用してフィルタ。
    - OpenAI 呼び出しは専用実装。API障害時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - リトライ・バックオフ・HTTP ステータス判定を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) -> 1（成功）
    - 設計上、ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない。
- Research（ファクター計算・特徴量解析）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ（ATR 等）、バリュー（PER, ROE）の計算関数を実装。
    - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials のみ参照。
    - 関数:
      - calc_momentum(conn, target_date) -> 各銘柄の mom_1m/mom_3m/mom_6m/ma200_dev
      - calc_volatility(conn, target_date) -> atr_20, atr_pct, avg_turnover, volume_ratio 等
      - calc_value(conn, target_date) -> per, roe
    - データ不足時の戻り値や NULL 扱いは明示的に設計（例: ma200_dev が行数不足なら None）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算、IC（Information Coefficient）計算、ランク付け、統計サマリーを実装。
    - 関数:
      - calc_forward_returns(conn, target_date, horizons=None) -> 将来リターン（複数ホライズン対応、horizons 検証あり）
      - calc_ic(factor_records, forward_records, factor_col, return_col) -> Spearman ρ（ランク相関）
      - rank(values) -> 同順位は平均ランクを返す（丸め対策あり）
      - factor_summary(records, columns) -> count/mean/std/min/max/median
  - src/kabusys/research/__init__.py
    - 主要関数をパブリックに再エクスポート（zscore_normalize は kabusys.data.stats に依存）。
- Data（ETL・カレンダー・パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの管理と営業日判定ロジックを実装。
    - 提供機能:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - calendar_update_job(conn, lookahead_days=90) : J-Quants からの差分取得・保存処理（バックフィルや健全性チェック含む）
    - 設計:
      - market_calendar がない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
      - 最大探索日数 (_MAX_SEARCH_DAYS) を定義して無限ループを防止。
      - DB 登録値を優先、未登録日は曜日ベースで補完する一貫性。
  - src/kabusys/data/pipeline.py
    - ETL パイプライン用ユーティリティと ETLResult データクラスを実装。
    - ETLResult: ETL 実行の集約結果（取得件数、保存件数、品質問題、エラー等）を保持。has_errors / has_quality_errors / to_dict を提供。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等。
  - src/kabusys/data/etl.py
    - ETLResult を再エクスポート。
- パッケージ公開インターフェース
  - src/kabusys/ai/__init__.py、src/kabusys/research/__init__.py、src/kabusys/data/__init__.py 等で主要 API を再エクスポート。

Security / Notes
- OpenAI API
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を投げる。
  - LLM 呼び出しは gpt-4o-mini を前提に JSON Mode を利用する設計。
  - API の一時的障害（429/ネットワーク/タイムアウト/5xx）はリトライ戦略で扱うが、最終的な失敗はフェイルセーフとして該当スコアに 0.0 を使用（または結果スキップ）する。
- データベースと依存
  - DuckDB に対する SQL 実行が多数あるため、DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を呼び出し元で用意する必要あり。
  - jquants_client（jquants API との通信層）は参照しているがソースに含まれていないため、ETL 実行時は別途実装 / 提供が必要。
- 設定
  - 必須環境変数のサンプル: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 設計方針の明記
  - ルックアヘッドバイアス回避のため、日付計算で datetime.today()/date.today() を直接使用せず、target_date を明示的に渡す設計になっている箇所が多い（AI スコア / レジーム判定 / ファクター計算等）。
  - DB 書き込みは原則トランザクションで行い、部分失敗時に既存データを保護する工夫を入れている（DELETE→INSERT、コード絞り込み等）。

Known issues / TODO
- package 内に execution / monitoring / strategy といった __all__ に含まれるモジュール参照があるが、今回のリリースに該当実装が含まれていません（将来追加予定）。
- jquants_client 実装が別モジュールに依存しているため、ETL を動かすためには外部クライアント実装またはモックが必要です。
- テスト用のモックフックは各所に設けている（例: _call_openai_api を patch してテスト可能）が、ユニットテストは付属していません。

Compatibility / Breaking Changes
- 初回リリースのため破壊的変更はありません。

Contributing
- バグ修正・機能追加は Pull Request を受け付けます。コード品質・ログ出力・DBトランザクション扱いに注意してください。

ライセンス
- ソースコードのライセンス情報はリポジトリのルート（pyproject.toml 等）を参照してください。