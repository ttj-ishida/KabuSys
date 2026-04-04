Changelog
=========

注記
----
- 以下は提示されたコードベースの内容から推測して作成した変更履歴（CHANGELOG.md）です。実際のリリースノートはプロジェクトの運用方針に合わせて調整してください。

Unreleased
----------
- なし

[0.1.0] - 2026-04-04
--------------------
Added
- パッケージの初期リリース。
  - パッケージ情報:
    - バージョン: 0.1.0
    - パッケージ名: kabusys
    - エクスポート: data, strategy, execution, monitoring（__all__）

- 環境設定 / 初期化 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの判定は .git または pyproject.toml を基準に行い、カレントディレクトリに依存しない実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - コメント行、export 付き行、クォート内のエスケープ、インラインコメントの扱いなどに対応。
  - Settings クラスを提供し、必要な設定値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）や既定値（KABU_API_BASE_URL、データベースパス等）をプロパティで公開。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の値検証ロジックを実装。
  - PID / キルフラグ / 監視閾値（CPU/メモリ/ディスク）等の運用設定を公開。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - 処理の主な仕様:
      - ニュース時間ウィンドウ（JST前日15:00〜当日08:30、内部は UTC naive）を計算する calc_news_window を提供。
      - 1銘柄あたりの記事数／文字数の上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）で入力トリム。
      - 最大バッチサイズ 20 銘柄単位で API 呼び出し。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
      - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score、数値検査、±1.0 でクリップ）。
      - 部分失敗を考慮し、ai_scores テーブルへは取得済みコードのみ DELETE→INSERT で置換（DuckDB の executemany の制約に配慮）。
      - API 呼び出し部分は _call_openai_api を分離しており、テスト時に差し替え可能。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）について直近200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - 処理の主な仕様:
      - ma200 乖離計算（データ不足時は中立 1.0 を採用し警告ログ）。
      - マクロキーワードで raw_news のタイトルを抽出し、OpenAI に渡して macro_sentiment を算出（記事がない場合は LLM 呼び出しを行わない）。
      - LLM 呼び出しはリトライ/バックオフを実装、失敗時は macro_sentiment=0.0 にフォールバック（例外を投げず継続）。
      - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
      - 結果は market_regime テーブルに冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK を試行）。
      - テスト容易性のため API 呼び出し部分は差し替え可能。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理ロジックを提供（market_calendar テーブルの利用、曜日ベースのフォールバック）。
    - 営業日判定 API を提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを実装）。
    - 最大探索日数やバックフィル等の安全性措置を実装。

  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（ETL 実行メタ情報、品質問題、エラー一覧、ヘルパーメソッド to_dict）。
    - 差分取得・保存・品質チェックの方針をコード内に明示。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ等を実装。
    - デフォルトのバックフィル日数やカレンダー先読み等、実運用向けの設定を組込み。

  - etl の公開インターフェースとして ETLResult を再エクスポート (kabusys.data.etl)。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算群:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率など。
    - calc_value: PER / ROE を raw_financials と prices_daily から計算（EPS=0/欠損は None）。
  - 特徴量探索:
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算、3 件未満は None。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出の安定化）。
  - data.stats の zscore_normalize を再エクスポート。

Design / Quality / Safety notes
- ルックアヘッドバイアス回避:
  - AI モジュール（news_nlp, regime_detector）やリサーチ関数は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリは target_date 未満や排他区間を明示してルックアヘッドを防止。
- フェイルセーフ:
  - OpenAI API の失敗時は例外を上位に投げず、ロギングのうえ安全側のデフォルト（ゼロセンチメント等）で継続する実装が多い。
- テスト容易性:
  - OpenAI 呼び出しは _call_openai_api のようなラッパー関数に分離されており、unittest.mock.patch 等で差し替えてユニットテスト実行可能。
- DuckDB 互換性配慮:
  - executemany に空リストを渡せない制約（DuckDB 0.10）を考慮して空チェックを実施。
  - 日付の取り扱いは date オブジェクトで統一し timezone 混入を避ける。

Breaking Changes
- なし（初期リリースのため該当なし）

Security
- 環境変数や秘密情報（OpenAI / API トークン等）の取り扱いは環境変数経由が前提。自動 .env ロードの挙動を理解したうえで運用すること。
- OPENAI_API_KEY が未設定の場合、news_nlp.score_news と regime_detector.score_regime は ValueError を投げる仕様。

Contributors
- コードベースからは明示的な貢献者情報が取得できません（該当情報はリポジトリの AUTHORS / git 履歴を参照してください）。