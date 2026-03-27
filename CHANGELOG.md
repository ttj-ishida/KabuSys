CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。
リリース日はコードベースの日付やコメント等から推定しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
  - パッケージ公開情報
    - src/kabusys/__init__.py にてバージョンとサブパッケージ（data, research, ai, ...）を公開。

- 環境設定／自動 .env ロード
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途を想定）。
    - export KEY=val、引用符付き値、インラインコメント等の一般的な .env 記法を堅牢にパースする実装を提供。
    - Settings クラスでアプリケーション設定を型付きプロパティとして公開（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等）。
    - 環境変数の必須チェック（_require）を実装し、未設定時に明示的な ValueError を発生させる。
    - デフォルトの DB パス: DUCKDB_PATH = data/kabusys.duckdb、SQLITE_PATH = data/monitoring.db。

- ニュース NLP（LLM）スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を入力に OpenAI（gpt-4o-mini）を呼んで銘柄ごとのセンチメント ai_score を生成する機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window() で提供。
    - 銘柄ごとに最新記事を集約し、1チャンクにつき最大 _BATCH_SIZE（20）銘柄をバッチ送信する方式。
    - 1銘柄あたりの最大記事数と最大文字数（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトークン肥大化を抑制。
    - OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を使用し、レスポンスのバリデーションを厳格に実施（_validate_and_extract）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライを実装。致命的な失敗はスキップし、全体処理を継続するフェイルセーフ設計。
    - 書き込みは部分的失敗を考慮し、取得した銘柄コードのみ DELETE → INSERT により置換（冪等処理）。DuckDB の executemany 空リスト制約に配慮。
    - パブリック関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - テスト容易性のため OpenAI 呼び出し箇所は _call_openai_api をパッチ可能に設計。

- 市場レジーム判定モジュール
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を用いて計算し、結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT の形）。
    - LLM 呼び出しは個別実装で、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - リトライ／バックオフや JSON パースの堅牢化を実装。パブリック関数: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。
    - 設計上ルックアヘッドバイアス防止のために datetime.today() を参照しない実装ポリシーを採用。

- データプラットフォーム（ETL / カレンダー / パイプライン）
  - src/kabusys/data/calendar_management.py
    - market_calendar の取得・保存・営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といったユーティリティを提供。
    - DB にカレンダーデータがない場合の曜日ベースのフォールバック、DB 値優先・未登録日はフォールバックという一貫した挙動を実装。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を行う（バックフィルと健全性チェック付き）。
    - DuckDB 日付型 ←→ Python date の相互変換やテーブル存在チェック等のユーティリティを実装。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL の結果を表現する ETLResult データクラスを実装（取得件数／保存件数／品質問題／エラー等を保持）。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールと連携する想定）。
    - エラーや品質問題は収集して呼び出し元で取り扱う方針（Fail-Fast ではなく全件収集）。ETLResult.to_dict() により監査ログ用途に変換可能。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - ファクター計算群を実装（momentum / volatility / value）。
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR、ATR/価格比、20 日平均売買代金、出来高比率などを計算。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得して PER、ROE を計算。
    - 全関数は DuckDB を用いた SQL ベース実装で、外部発注やネットワークアクセスは行わない設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)（デフォルト [1,5,21]）を実装。
    - IC（Information Coefficient）計算 calc_ic(...)：スピアマンのランク相関を実装し、レコード不足時は None を返す。
    - rank(values)／factor_summary(records, columns) 等の補助関数を実装。標準ライブラリのみで完結する実装。

- 公開 API の整理
  - 各モジュールでテストや外部利用を想定した明示的なパブリック関数を提供し、モジュール分離（例えば ai/news_nlp と ai/regime_detector は内部 OpenAI 呼び出しを共有しない）を図る。
  - テスト容易性のために OpenAI 呼び出し箇所はパッチ可能に設計。

Security / Reliability / Operational
- 環境変数読み込み時の保護
  - OS 環境変数を protected として .env の上書きを制御する仕組みを実装。
- 冪等性
  - データベースへの書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT などを想定）に実装。
- フェイルセーフ
  - LLM 呼び出し失敗時は零（中立）スコアへフォールバックしてパイプラインを継続。
- ログと警告
  - 異常値やデータ欠損、ロールバック失敗などは logger を通して明示的に記録。

Notes / Requirements
- OpenAI API
  - news_nlp / regime_detector の実行には OPENAI_API_KEY が必要（関数引数で注入可能）。未設定時は ValueError を送出。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須となっている（利用箇所に応じて必要）。
- DB
  - DuckDB を主に想定。デフォルトパスは Settings で設定可能。
- テスト
  - OpenAI 呼び出し箇所（_call_openai_api 等）を unittest.mock.patch 等で差し替え可能に設計。

Breaking Changes
- 初回リリースのため破壊的変更はありません。

Acknowledgements / Design
- ルックアヘッドバイアス防止のため、各処理は datetime.today() / date.today() に依存せず、明示的な target_date 引数を多用する設計を採用しています。
- 外部 I/O（API 呼び出し・DB 書き込み）に対して堅牢性（リトライ・バックオフ・部分的失敗の保護）を重視しています。

--- 

今後のリリースでは `Unreleased` セクションに機能追加・改善・修正を追記してください。