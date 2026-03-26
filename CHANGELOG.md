CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-26
------------------

初回リリース。日本株自動売買／リサーチ向けライブラリ「KabuSys」を公開します。
主要な機能、提供 API、設計上の重要な挙動・注意点を以下にまとめます。

Added
-----

- パッケージ基礎
  - src/kabusys/__init__.py
    - 初期バージョンを "0.1.0" として公開。パッケージの public なサブモジュールとして data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイル（および .env.local）と OS 環境変数を統合して読み込む自動ローダを実装。プロジェクトルートは .git または pyproject.toml を探索して決定するため、CWD に依存せずパッケージ配布後も動作。
    - .env のパースは export 文、シングル/ダブルクォート内のエスケープ、コメント（#）処理などに対応する堅牢な実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供（settings）。必須環境変数チェック用の _require を含む。
    - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。DB パスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）も定義。
    - KABUSYS_ENV と LOG_LEVEL の入力検証を実装（許容値を制限）。

- データ関連（Data platform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が不十分な場合は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新。バックフィル、健全性チェック（将来日付の過大検出）を実装。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプライン向けの基礎を提供。ETLResult データクラスを公開（ETL 実行結果、品質チェック結果、エラー集約を保持）。
    - 差分更新、バックフィル、品質チェック方針を実装（jquants_client、quality モジュールと連携する想定）。
    - _get_max_date 等のユーティリティを実装し、DuckDB と互換性のある実装。

  - 軽量の公開 API
    - src/kabusys/data/__init__.py と etl の ETLResult を再エクスポート。

- リサーチ（Research）
  - src/kabusys/research/*
    - factor_research.py
      - モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数を実装:
        - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
        - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR・出来高指標）
        - calc_value: per / roe（raw_financials の最新財務データを利用）
      - DuckDB 上の SQL ウィンドウ関数を活用し、データ不足時の None 処理等を実装。
    - feature_exploration.py
      - calc_forward_returns: target_date から複数ホライズンの将来リターンを同一クエリで取得（horizons 検証あり）。
      - calc_ic: スピアマンのランク相関（IC）を計算する実装（欠損/定数分散は None を返す）。
      - rank: 同順位は平均ランクを返す堅牢なランキング実装（丸めで ties を安定化）。
      - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで提供。
    - research パッケージ __init__.py に関数をエクスポート（zscore_normalize 再利用を含む）。

- AI（LLM）統合
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - JSON Mode を利用し厳密な JSON を要求。最大銘柄数バッチ (_BATCH_SIZE=20)、各銘柄あたり記事数/文字数上限を設ける（トークン肥大化対策）。
    - リトライポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（最大リトライ回数制御）。
    - validate 処理でレスポンス整形・堅牢化（余計な前後テキストから JSON を抽出、スコアの数値チェック、未知の銘柄コードは無視）。
    - スコアは ±1.0 にクリップ。スコア取得銘柄のみ ai_scores テーブルを置換（DELETE → INSERT）して部分失敗時の既存データ保全を実現。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - calc_news_window(target_date) を提供（JST ベースのウィンドウ定義、UTC 変換済み）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を算出。
    - レジームスコア合成式、閾値（BULL/BEAR）、クリップ範囲を定義。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない）でモジュール結合を低減。API 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK して例外を伝播。

- ロギング / 耐障害性
  - 多くの処理で詳細なログ（info/debug/warning/exception）を出力。
  - API 呼び出しの失敗をスキップして継続する設計（フェイルセーフ）、およびロールバック時の警告ログを実装。
  - テスト用フック: OpenAI 呼び出しを行う内部関数（_call_openai_api）を unittest.mock.patch で差し替え可能な設計。

Changed
-------

- （初版のため該当なし）

Fixed
-----

- （初版のため該当なし）

Notes / Migration / Usage notes
-------------------------------

- 必須環境変数
  - AI 機能を利用するには OPENAI_API_KEY（または score_* 関数の api_key 引数）を必ず設定してください。未設定時は ValueError を送出します。
  - ETL や外部 API 連携には JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、Slack 用の SLACK_BOT_TOKEN / SLACK_CHANNEL_ID などが必要です。settings で確認してください。

- 自動 .env ロード
  - パッケージ読み込み時にプロジェクトルートの .env と .env.local を自動で読み込みます。テストなどで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env.local は .env を上書き（override=True）する扱いです。OS 環境変数は上書きされません（保護）。

- LLM 呼び出し挙動
  - OpenAI への問い合わせは JSON Mode を利用し、出力の JSON パースに失敗した場合は復元の試みを行いますが、最終的に失敗したチャンクはスキップされます（空辞書を返す等）。
  - レスポンスの形式・スコア値が想定外だと該当銘柄は無視されるため、スコア取得済み銘柄のみ ai_scores に書かれます（データ整合性保護）。
  - news_nlp と regime_detector の両方で retry/backoff の実装があり、429/ネットワーク/5xx を対象にリトライします。

- ルックアヘッドバイアス対策
  - AI 系関数およびリサーチ関数は datetime.today()/date.today() を内部参照せず、必ず外部から target_date を受け取る設計です。DB クエリでも date < target_date などルックアヘッドを防ぐ条件を明示しています。

- DB（DuckDB）関係
  - DuckDB のバージョン差異に配慮した実装（executemany に空リスト不可への対応や LIST 型バインド回避など）を行っています。
  - トランザクションは手動で BEGIN/COMMIT/ROLLBACK を行い、部分的失敗時の既存データ保護を重視しています。

依存関係
--------

- 実行時に以下が必要（少なくとも利用する機能に応じて）:
  - duckdb
  - openai（OpenAI Python SDK）

Security
--------

- 環境変数や API キーは .env/.env.local または OS 環境変数で管理してください。自動ロードはローカル開発便宜のためのものであり、本番運用時は OS 環境変数またはシークレットマネージャーを推奨します。

Acknowledgements / Design
-------------------------

- 本リリースは「DataPlatform.md」「StrategyModel.md」に基づく設計思想を反映しています（ソース内の docstring に詳細を記載）。
- モジュール間の結合を低く保ち、テスト容易性を考慮して設計しています（例: _call_openai_api をテストで差し替え可能にする等）。

お問い合わせ
------------

不明点や追加してほしい項目があれば教えてください。必要に応じて CHANGELOG に補足・細分化して反映します。