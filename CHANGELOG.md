Keep a Changelog に準拠した CHANGELOG.md（日本語）
（コードベースから推測して作成した初期リリースの変更履歴です）

Unreleased
----------
- なし

0.1.0 - 2026-03-31
-----------------
Added
- パッケージ基盤
  - kabusys パッケージ初期実装。モジュール公開: data, strategy, execution, monitoring をパッケージ外部に公開。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索し、配布後の実行でも動作するよう実装。
  - .env パーサ実装（_parse_env_line）：
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理（クォート有無での挙動差）などを考慮。
  - .env の読み込み時に既存 OS 環境変数を保護する protected セットをサポート（.env.local は override=True で上書き可能だが protected は上書き不可）。
  - Settings クラスを提供し、アプリケーション設定キーをプロパティで公開：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルトあり)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - target_date ベースでのニュース収集ウィンドウ calc_news_window を実装（JST基準から UTC naive datetime に変換）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチで問い合わせて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む score_news を実装。
    - バッチ処理 (_BATCH_SIZE=20)、1 銘柄あたりの最大記事数と文字数制限（トリム）の対策、JSON mode を想定したレスポンスバリデーション実装。
    - OpenAI 呼び出しのリトライ/バックオフ戦略（429、タイムアウト、接続断、5xx の扱い）を実装。
    - レスポンス検証 (_validate_and_extract) で結果構造・型の検査、未知コードの無視、スコアのクリップ(±1.0)。
    - テスト容易性のために内部 _call_openai_api を patch で差し替え可能に設計。
    - DuckDB の executemany に関する互換性（空リスト禁止）を考慮した INSERT/DELETE の実行ロジック。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの ma200_ratio 計算（ルックアヘッドバイアス防止のため target_date 未満のみ使用）、raw_news からマクロキーワードでフィルタして記事を取得。
    - マクロセンチメントの LLM 評価に対するリトライ/バックオフ、API 失敗時はフェイルセーフとして macro_sentiment=0.0 を利用。
    - 最終結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。

  - 共通設計方針（AI モジュール）
    - datetime.today() / date.today() を直接参照せず、すべて呼び出し側からの target_date に依存（ルックアヘッドバイアス防止）。
    - OpenAI 呼び出し時は JSON mode を期待し、応答の堅牢なパースと検証を実装。
    - 失敗時は例外を上位へ乱発せず、警告ログを出して処理を継続する方針（フェイルセーフ）。

- リサーチ（kabusys.research）
  - factor_research モジュールを実装：
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を DuckDB SQL によって一括計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から直近財務データを取得して PER / ROE を計算（EPS 0 または欠損時は None）。
    - 全関数は prices_daily / raw_financials 参照のみで外部発注など副作用なし。
  - feature_exploration モジュールを実装：
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括計算（horizons の妥当性検証あり）。
    - calc_ic: Spearman のランク相関（IC）をランク変換して計算。必要最小レコード数チェック（3未満で None）。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（丸めにより ties を安定化）。
    - factor_summary: カウント/平均/標準偏差/最小/最大/中央値を標準ライブラリで計算する統計サマリー。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得／未登録日については曜日ベース（平日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants から差分でカレンダーデータを取得し market_calendar へ冪等的に保存。バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（未来日付の異常検知）を実装。
  - ETL / pipeline:
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）。
    - ETL 実行結果の集約（取得件数・保存件数・品質問題・エラー）とヘルパー（has_errors / has_quality_errors / to_dict）を提供。
    - pipeline モジュール内に差分取得ロジックやテーブル最大日付取得ユーティリティ等を実装（_get_max_date, _table_exists 等）。
  - jquants_client との連携を想定した差分取得・保存・品質チェックの設計（実装は jquants_client 側に委譲）。

- 実装上の注意点・改善点
  - DuckDB の挙動差（executemany に空リスト不可）に対応したコードパスを用意。
  - DB 書き込みは明示的なトランザクション制御（BEGIN/COMMIT/ROLLBACK）を使用して冪等性と障害時の整合性を担保。
  - OpenAI 呼び出しは model=gpt-4o-mini を想定、response_format に JSON object を使用するための取り扱いを実装。
  - ロギングと警告を多用し、フェイルセーフにより部分失敗時でもプロセス全体が継続できる構成にしている。
  - テスト容易性のため、内部 API 呼び出し（OpenAI クライアント呼び出し等）を差し替え可能に設計。

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes
- 本 CHANGELOG はソースコードの実装内容から推測して作成した初期リリース向けの説明です。実際のリリース日や追加されたファイル・変更履歴はリポジトリのコミット履歴に従って調整してください。