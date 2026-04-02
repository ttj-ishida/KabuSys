CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の規約に従っています。
Semantic Versioning を採用しています。

[Unreleased]
-------------
（現時点では特定の未リリース変更はありません。新機能追加や修正は次のリリースに記載します。）

[0.1.0] - 2026-04-02
-------------------
初回公開リリース。

Added
- パッケージ初期公開: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数の上書きを防ぐ「protected」機構を実装。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、行内コメント等に対応。
  - Settings クラスを提供し、アプリ固有設定をプロパティとして取得可能:
    - J-Quants: jquants_refresh_token (必須)
    - kabuステーション API: kabu_api_password, kabu_api_base_url (デフォルト http://localhost:18080/kabusapi)
    - Slack: slack_bot_token, slack_channel_id (必須)
    - DB パス: duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
    - 監視設定: pid_file_path, cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct（デフォルト値あり）
    - 実行環境: env（development / paper_trading / live を検証）、log_level（DEBUG/INFO/... を検証）、is_live/is_paper/is_dev

- ニュース NLP モジュール（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None) を公開。
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメントを取得して ai_scores テーブルへ保存。
  - 実装上の特徴:
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄/コール
    - 1銘柄あたり記事トリム: 最大 10 件、最大文字数 3000 文字
    - エラーハンドリング: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他はスキップ。失敗時は部分的にスコアを残す設計（部分失敗で既存スコアを消さない）。
    - レスポンス検証: JSON パース、"results" 配列、code の存在、スコア数値化、スコアを ±1.0 にクリップ。
    - テスト容易性: _call_openai_api をパッチしてモック可能。

- マーケットレジーム判定モジュール（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) を公開。
  - 処理:
    - ETF 1321 の直近 200 日終値から 200 日移動平均乖離（ma200_ratio）を算出（ルックアヘッド防止のため target_date 未満データのみ使用）。
    - raw_news からマクロ経済キーワードでフィルタしたタイトルを抽出し（最大 20 件）、OpenAI でマクロセンチメントを評価。
    - ma200（重み 70%）とマクロ（重み 30%）を合成してレジームスコアを算出し、market_regime テーブルへ冪等的に書き込み。
  - エラーハンドリング:
    - OpenAI API 呼び出し失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - リトライ設定とバックオフを実装。
    - モデル: gpt-4o-mini（JSON レスポンスを期待）。

- データ処理モジュール（kabusys.data）
  - ETL パイプライン用の型およびユーティリティを実装:
    - pipeline.ETLResult を公開（etl 結果の dataclass）。
    - pipeline モジュール: 差分取得、保存、品質チェックのための雛形実装（jquants_client, quality と連携する設計）。
  - カレンダー管理（kabusys.data.calendar_management）:
    - market_calendar を用いた営業日判定・探索ユーティリティの実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL 設計上の考慮:
    - 差分更新、バックフィル、品質チェックの収集（重大度を返す）を行う。

- Research / Factor モジュール（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離など。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、平均売買代金、出来高比率など。
    - calc_value(conn, target_date): PER（EPS が有効な場合）、ROE（raw_financials から最新版を取得）等。
    - DuckDB 上の SQL とウィンドウ関数を多用した実装。データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（horizons デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算、有効レコード数が 3 未満なら None。
    - rank(values): 同順位は平均ランクとする安定したランク変換（丸めで ties の検出漏れを防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出。

Changed
- （初回リリースのため過去変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- 環境変数ロード機構で OS 環境変数の上書きを保護する設計（protected set）。自動ロードは無効化可能。
- OpenAI API キーは引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を送出して明示的にエラー扱い。

Notes / 実装上の重要設計判断
- すべての「日時依存」処理（ニュース集計・レジーム判定など）は date/datetime の直接参照（datetime.today() / date.today()）を避け、明示的な target_date 引数を受け取ることでルックアヘッドバイアスを防止。
- OpenAI 呼び出しは JSON モードを前提とし、レスポンスの堅牢なバリデーションとフォールバック（失敗時は 0.0 やスキップ）を実装。テスト時に置き換え可能なよう内部呼び出しを設計。
- DuckDB をコア DB として想定し、executemany に関する互換性（空リスト不可など）に配慮した実装。
- 外部 API（J-Quants / OpenAI / kabu ステーション）とのやり取りは明確に分離・注入可能にし、ユニットテストやモックが容易な設計を意識。

テーブル / 外部依存の概観
- DuckDB テーブル想定: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など。
- 外部 API: J-Quants（データ・カレンダー取得）、OpenAI（gpt-4o-mini を想定）、kabu ステーション（発注用APIの設定項目を用意）。

問い合わせ / 追記
- 機能追加・バグ修正やリリース日付の更新を行う際は本 CHANGELOG を更新してください。改善提案や API 仕様の変更は Breaking Changes セクションにて明示的に記載してください。