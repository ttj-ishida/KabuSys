CHANGELOG
=========

すべての重要な変更点は "Keep a Changelog" のガイドラインに従って記載しています。
このファイルはコードベースの現在の状態（初期リリース相当）から推測して作成した変更履歴です。

Unreleased
----------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリースを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = "0.1.0"）を追加。
  - トップレベルで公開するサブパッケージ: data, research, ai, execution, monitoring, strategy（__all__ に一部列挙）。

- 環境設定管理機能を追加（src/kabusys/config.py）。
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行う（CWD に依存しない）。
  - .env のパースを細かく実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理等）。
  - Settings クラスを提供し、主要設定に対するプロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL 等
    - DB パスのデフォルト（DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"）
    - 監視用ファイルパス・閾値（PID/KILLフラグ、CPU/MEM/DISK閾値）
    - 環境（KABUSYS_ENV）の検証（development / paper_trading / live）
    - ログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- AI: ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）。
  - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
  - 処理概要:
    - ジャストインタイムでスコアを生成するニュース時間窓（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で定義。
    - 1銘柄あたり最新 n 件（デフォルト10件）、最大文字数（デフォルト3000文字）でトリム。
    - 最大バッチサイズ 20 銘柄/回で API 呼び出し。
    - JSON Mode 応答をバリデートして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
  - レジリエンス設計:
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - 応答パース失敗や API エラー時はそのチャンクをスキップし処理継続（フェイルセーフ）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch での置換を想定）。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書込銘柄数を返す。api_key が未指定かつ環境変数 OPENAI_API_KEY 未設定の場合は ValueError。

- AI: 市場レジーム判定（src/kabusys/ai/regime_detector.py）。
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - 処理概要:
    - prices_daily から 1321 の直近 200 日データを用いて ma200_ratio を算出（データ不足時は中立=1.0 にフォールバック）。
    - raw_news からマクロキーワードに該当するタイトルを抽出（最大件数制限）。
    - OpenAI（gpt-4o-mini）でマクロセンチメントを推定（記事なし時は LLM 呼び出しを行わず macro_sentiment=0.0）。
    - レジームスコアを合成し market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - エラー耐性:
    - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックし、処理を続行。
    - OpenAI 呼び出しロジックは独立実装でモジュール結合を抑制。
  - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。api_key 必須（引数または環境変数 OPENAI_API_KEY）。

- Data: マーケットカレンダー管理（src/kabusys/data/calendar_management.py）。
  - market_calendar テーブルを元にした営業日判定・探索ユーティリティを提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - データがない場合のフォールバック: 曜日ベース（平日を営業日、土日を非営業日）で一貫して動作。
  - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックを含む）。
  - 最大探索日数を設定して無限ループを防止。

- Data: ETL パイプライン基盤（src/kabusys/data/pipeline.py, etl.py）。
  - ETLResult データクラスを実装（ETL の収集・保存件数、品質チェックの問題リスト、エラーリスト等を保持）。
  - pipeline モジュールから ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- Research: ファクター計算・特徴量探索（src/kabusys/research/*）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value: raw_financials と当日の株価を組み合わせて PER / ROE を計算（EPS 無し・0 の場合は None）。
    - DuckDB SQL を活用し、date/code ごとの結果リストを返す。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を LEAD を用いて取得。ホライズンは検証あり（1〜252 日）。
    - calc_ic: スピアマンのランク相関（IC）を計算。利用可能レコードが 3 未満なら None。
    - rank: 平均ランクを用いたランク変換（同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - 研究用 API は外部の取引・発注 API に依存しない設計。

Changed
- （初期リリースのため "Changed" は該当なし）

Fixed
- （初期リリースのため "Fixed" は該当なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーや機密情報は環境変数で扱う設計。自動 .env ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

重要な設計上の注意（移行 / 使用上のポイント）
- OpenAI API:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。未設定時は ValueError が発生します。
  - API 呼び出し失敗は基本的に個別チャンクや macro_sentiment を 0.0 にフォールバックして処理を継続するため、部分的な結果しか得られないことがあります。
  - テスト容易性のため、各モジュール内の _call_openai_api をモックして挙動を制御できます。

- データベース / DuckDB:
  - DuckDB 接続を引数で受け取る設計のため、テストや埋め込み利用が容易です。
  - 一部の実装は DuckDB の executemany の挙動（空リストバインド不可）を考慮しています（空パラメータでの実行を回避）。

- .env パース:
  - 複雑なクォートやエスケープにも対応していますが、.env.example を参考に環境変数を設定してください。

- 時刻・ウィンドウ:
  - news ワインドウなどは JST 基準で定義し、DB 比較用に UTC naive datetime に変換しています。
  - 設計方針として datetime.today() / date.today() を内部で直接参照しない関数設計が多く、ルックアヘッドバイアスを防止しています（呼び出し側で基準日を指定）。

既知の制約
- market_calendar が未登録の場合は曜日ベースでのフォールバックとなるため、祝日等の精密な判定は J-Quants カレンダーの取得が前提です。
- ai/news_nlp の応答パースは堅牢化しているものの、LLM が期待外の形式を返した場合は該当チャンクをスキップします（部分的なスコア欠落が起こり得ます）。

貢献 / バグ報告
- 本リリースはコードベースから推測して作成した初期 CHANGELOG です。実際の要件や API の仕様に合わせて調整してください。バグや改善要望は issue にて報告してください。