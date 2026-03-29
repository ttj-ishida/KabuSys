CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
------------

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース v0.1.0 を追加。
- パッケージ構成（src/kabusys）を実装。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
    - __all__ に主要サブパッケージを公開 (data, strategy, execution, monitoring)
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 既存 OS 環境変数の保護機構（protected set）を実装し .env.local での上書き制御を実現。
  - Settings クラスを実装して環境変数をプロパティで取得：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などをプロパティ化。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）を Path で返す。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパーを追加。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini・JSON mode）で銘柄毎に -1.0〜1.0 のスコアを取得。
    - チャンク処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数上限を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー、型チェック、スコアの数値化とクリップ）。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照せず、呼び出し時の target_date を使用。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム ('bull'/'neutral'/'bear') を判定。
    - マクロニュース抽出用のキーワードリストを実装。
    - OpenAI 呼び出しは gpt-4o-mini、JSON 出力を期待。API エラー時は macro_sentiment = 0.0 にフォールバック。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を利用した営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーが存在しない/未登録日は曜日ベースでフォールバック（週末は非営業日）。
    - next/prev/get の探索に最大探索日数制限 (_MAX_SEARCH_DAYS) を導入して無限ループを防止。
    - calendar_update_job を実装（J-Quants クライアント経由で差分取得→保存）。バックフィル・健全性チェック有り。
  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを実装して ETL 実行結果（取得数 / 保存数 / 品質問題 / エラー等）を構造化。
    - 差分取得・バックフィル・品質チェックの設計方針に基づくユーティリティ関数を追加（テーブル存在チェック、最大日付取得等）。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - jquants_client と quality への依存を想定した設計（実クライアント実装は別モジュール）。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）/ 相対 ATR（atr_pct）/ 20 日平均売買代金/出来高比率を計算。
    - calc_value: 最新財務データ（raw_financials）と株価を組み合わせて PER / ROE を計算。
    - 全関数は DuckDB の prices_daily/raw_financials のみを参照し、本番 API への影響無し。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する SQL 実装。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（結合・欠損排除・最小件数チェック）。
    - rank: 同順位は平均ランクを返すランク変換実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
  - zscore_normalize は kabusys.data.stats から再エクスポート。
- その他
  - 多くのモジュールで DuckDB を前提とした SQL ベースの実装を採用。
  - ロギング（logger）を各モジュールに導入し重要なイベントやフォールバックを記録。
  - テストしやすさを考慮し、外部 API 呼び出し箇所は差し替え可能に設計。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は明示的な ValueError を発生させる設計。

Notes / Migration
- 環境変数自動ロード:
  - プロジェクト配布後の動作安定のため .env 自動ロードは __file__ を起点にプロジェクトルートを探索します。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- OpenAI を利用する機能 (score_news, score_regime) を実行するには OPENAI_API_KEY の設定（または api_key 引数）が必須です。
- DuckDB をバックエンドとして想定しており、テーブル構造（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）に依存します。既存 DB スキーマとの整合に注意してください。
- ai モジュールは厳密な JSON 出力を前提にしているため、LLM のレスポンスが想定外の場合はパース失敗→フェイルセーフ（スコア 0.0 / 対象スキップ）となります。

Known issues
- 初期リリースのため運用上の細かい例外処理・エッジケースに注意。特に DuckDB バージョンや JSON mode の挙動差異が影響する可能性あり。

Contributing
- バグ報告・機能要望はリポジトリの issue へお願いします。開発者向けにテストの書きやすさを意識してモジュール境界を設計しています（API 呼び出し箇所を patch してユニットテスト可能）。

---