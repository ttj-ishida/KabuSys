CHANGELOG
=========

すべての注目すべき変更点はこのファイルにまとめます。フォーマットは "Keep a Changelog" に準拠しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ情報: src/kabusys/__init__.py により __version__="0.1.0" を公開。
  - パブリック API の想定エントリ: "data", "strategy", "execution", "monitoring" を __all__ に含める（ただし一部は今後実装予定）。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリを探索して .git または pyproject.toml を基準とする自動検索を実装。これにより CWD に依存しない自動 .env 読み込みが可能。
  - .env パーサーを強化:
    - 空行・コメント（#）・export プレフィックスに対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - インラインコメント判定の細かなルール（クォート外かつ '#' の直前が空白/タブの場合にコメントと扱う）を実装。
  - 自動ロード順序: OS 環境 > .env.local（上書き） > .env（非上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - 必須設定を取得する _require() と Settings の各プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を設定。
  - env 値検証（development / paper_trading / live）とログレベル検証を実装。

- AI：ニュース NLP と市場レジーム判定（src/kabusys/ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して、銘柄ごとにニュースを結合し OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出、ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済）。
    - バッチング（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数制限（最大記事数 10、最大文字数 3000）を導入。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他はスキップするフェイルセーフ設計。
    - レスポンス検証: JSON パース、"results" フィールド・型チェック、未知コード除外、数値化・有限性チェック、スコア ±1.0 でクリップ。
    - DuckDB の executemany 空リスト制約（0.10 系）への対応（空の場合は実行しない）。
    - API キーは引数で注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）。テスト用に _call_openai_api を差し替え可能。

  - regime_detector.score_regime:
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離（70% 重み）とニュースマクロセンチメント（30% 重み）を合成して日次市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロセンチメントは OpenAI（gpt-4o-mini）を用いる。記事がない場合や API 失敗時は macro_sentiment=0.0 として継続。
    - API 呼び出しに対するリトライ・エラーハンドリングを実装（5xx はリトライ、非5xx はフォールバック）。
    - トランザクション処理で BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK（ROLLBACK が失敗した場合に警告ログ）。

- データプラットフォーム（src/kabusys/data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）に基づく営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等を実装。DB に登録がなければ曜日ベースのフォールバック（土日除外）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新、バックフィル、健全性チェックを実装。
    - 最大探索日数やバックフィル期間などの安全策を導入。

  - pipeline / ETL:
    - ETLResult データクラスを導入（取得件数、保存件数、品質チェック結果、エラー一覧を保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した ETL パイプライン基盤を実装。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、ターゲット調整などを追加。
    - 設計上の注意点（DuckDB 互換性、idempotent 保存、品質チェックは収集優先で処理継続）を実装文書化。

- Research（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算。
    - すべて DuckDB 上で SQL と標準ライブラリのみで実装（外部 API にはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。ホライズンの検証あり（正の整数 <=252）。
    - calc_ic: スピアマンランク相関（IC）を算出。必要レコード数が足りない場合は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量集計を提供。
    - pandas 等の外部ライブラリに依存しない実装。

Changed
- 設計上の重要方針（ドキュメント化）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を分析/スコア関数内部で参照しない（target_date を明示的に受け取る）。
  - DuckDB 互換性に配慮した executemany の取り扱い（空リストは実行しない）。
  - モジュール結合を避けるため、regime_detector と news_nlp はそれぞれ独立した _call_openai_api 実装を持ち、テストでは patch 可能。

Fixed
- 初版の安定性向上:
  - OpenAI API 呼び出し時の細かな例外処理（RateLimitError/APIConnectionError/APITimeoutError/APIError の扱い）とリトライ方針を実装し、API障害時のフェイルセーフ（0.0 やスキップ）で処理継続を保証。
  - .env ファイル読み込みでのファイル存在チェックと読み込み失敗時の警告機構を追加。

Known issues / Notes
- パッケージ __all__ に "strategy", "execution", "monitoring" が含まれているが、今回のコード一覧では該当モジュールの詳細実装が確認できないため、実装は今後追加予定。
- news_nlp / regime_detector ともに OpenAI への依存を持つため、実行時には OPENAI_API_KEY（または api_key 引数）が必須。テスト用に API 呼び出し関数をモックできる設計になっている。
- DuckDB バージョン差異（特にリストパラメータバインドや executemany の挙動）に注意して運用・テストを行うこと。

Acknowledgements
- 本リリースは、J-Quants / kabu ステーション等の外部データソースを前提とした日本株自動売買システムの基盤実装（データ ETL、カレンダー管理、因子計算、AI ベースのニュース評価、レジーム判定）を提供します。今後のリリースで戦略・実行・監視周りの機能を順次追加予定です。