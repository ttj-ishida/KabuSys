Keep a Changelog
=================

すべての重要な変更をこのファイルで管理します。  
このプロジェクトはセマンティックバージョニングに従います。

[0.1.0] - 2026-03-28
-------------------

初回リリース。以下の主要機能・モジュールを追加しました。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ定義）。
- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - .env パーサ実装：export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱いなどを考慮した _parse_env_line。
  - .env 読み込み時の override / protected（既存 OS 環境変数保護）オプション。
  - Settings クラスを提供（プロパティ経由で環境変数を型付きに取得）。
    - 必須設定のチェック（_require）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
    - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi"、DUCKDB_PATH="data/kabusys.duckdb"、SQLITE_PATH="data/monitoring.db"。
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）とログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から時間窓（前日15:00 JST〜当日08:30 JST）に基づいて記事を集約。
    - 1 銘柄あたり最大記事数・文字数でトリムし、最大 20 銘柄ずつバッチで OpenAI（gpt-4o-mini）の JSON モードへ送信。
    - 再試行戦略：429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンス検証（JSON 抽出、"results" リスト・各要素の code/score 検証、未知コードの無視、数値変換、有限値チェック）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等（DELETE → INSERT）で書き込み。
    - API キー注入対応（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テスト用に内部の _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime_label（bull/neutral/bear）を算出。
    - マクロ記事はキーワードで抽出（日本・米国に関する候補語リスト）し、最大 20 件を LLM に渡す。
    - LLM 呼び出しは同じく gpt-4o-mini、JSON mode を利用。API の再試行/エラーハンドリングあり。
    - API 失敗時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - 結果は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に書き込み。失敗時は ROLLBACK を試行して例外を再送出。
    - score_regime は成功時に 1 を返す。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定と補助関数: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - market_calendar がない場合は曜日ベース（土日非営業）でのフォールバックを実装。
    - next/prev_trading_day は DB 優先（未登録日は曜日フォールバック）で最大探索日数制限（_MAX_SEARCH_DAYS）。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等保存。バックフィルと健全性チェック（最大未来日数）の実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーの集約、to_dict による出力整形）。
    - 差分取得・保存・品質チェックのフレームワーク設計（J-Quants クライアントの save_* を想定）。
    - テーブル存在チェックと最大日付取得ユーティリティ (_table_exists / _get_max_date)。
    - デフォルトのバックフィル日数、カレンダー先読み等の設定。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供。
    - データ不足時は None を返す設計。結果は (date, code) ベースの dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）によりファクターの説明力を評価。3 レコード未満は None。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク、丸めで ties を安定化。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算する純 Python 実装（外部依存なし）。
  - data.stats の zscore_normalize を再エクスポート（kabusys.research.__init__）。
- 実装上の設計原則（多くのモジュールで共通）
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を直接参照しない実装方針（関数は target_date を受け取る）。
  - 外部 API 呼び出しの失敗はフェイルセーフ（スキップやデフォルト値）で継続可能にする設計。
  - DB への書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 等）を採用。
  - テスト容易性のため一部内部関数（OpenAI 呼び出しなど）をモック差し替え可能に設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記 / 既知の設計制約
- DuckDB の executemany が空リストを受け付けないバージョンへの配慮として、空チェックを行ってから executemany を呼ぶ実装になっています。
- OpenAI SDK の例外型や status_code の有無に対応するため getattr を使った安全なエラーハンドリングを行っています。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計をとっています（結合を避けるため）。

今後の予定（例）
- PBR や配当利回り等のバリューファクター拡張
- ai モデルとプロンプトの改善、カスタムトークン制御の導入
- ETL の並列化・パフォーマンスチューニング
- 監視／アラート周り（Slack 連携等）の追加強化

-------------------

(注) 本 CHANGELOG は現在のコードベースから推測して作成しています。機能の詳細や挙動は実行環境・外部サービス（OpenAI / J-Quants 等）の API バージョンによって変わる可能性があります。