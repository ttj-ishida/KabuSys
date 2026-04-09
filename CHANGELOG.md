Keep a Changelog準拠 — CHANGELOG.md
==================================

すべての変更はこのファイルに記録します。形式は "Keep a Changelog" に従います。
なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パブリック API: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: コメント行、export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメント解析などに対応。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数取得ラッパー Settings を提供。J-Quants / kabu API / LINE トークン / DB パス / Paper Trading 設定 / 監視閾値などをプロパティとして提供。
  - 必須環境変数未設定時は明確なエラーメッセージを投げる _require を実装。
  - 設定値のバリデーションを実装（KABUSYS_ENV の許容値, LOG_LEVEL, PAPER_FILL_MODE の有効値等）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとに記事を抽出。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/チャンク）、JSON Mode を利用した厳密なレスポンス期待。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実行。
    - レスポンスのバリデーション（JSON パース、results リスト、各要素の code/score 型検査、未知コードの無視、数値チェック）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗で既存スコア保護）。
    - テスト用に内部の OpenAI 呼び出し関数をモックできるよう設計。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime テーブルを使用し、DuckDB に書き込み（BEGIN / DELETE / INSERT / COMMIT）して冪等性を確保。
    - マクロセンチメントは OpenAI により JSON を期待して取得。API失敗時は macro_sentiment=0.0 とするフェイルセーフ挙動。
    - OpenAI 呼び出しはリトライ・バックオフ処理を実装。
    - ルックアヘッドバイアス防止のため datetime.today() を参照せず、target_date を明示的に渡す設計。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率などボラティリティ・流動性指標を計算。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算。PBR/配当利回りは未実装。
    - 全関数は DuckDB を受け取り SQL／ウィンドウ関数で計算、外部 API へはアクセスしない安全設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データ不足（有効レコード < 3）の場合は None。
    - rank / factor_summary: ランク化（同順位は平均ランク）と各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。

- Data モジュール (kabusys.data)
  - calendar_management:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを採用。
    - 最大探索日数制限を配置して無限ループを防止。
    - calendar_update_job: J‑Quants からカレンダーを差分取得し market_calendar を冪等的に更新。バックフィル/健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラーリスト等を保持）。
    - ETL の基本設計（差分更新、保存は idempotent、品質チェックはエラーを収集して上位に伝える）を実装方針として定義。
    - DuckDB 互換性への配慮（executemany に空リストを渡さない等）を反映。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数で機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を扱うことを想定。Settings._require により未設定時は明示的にエラーを出す。
- .env 自動ロード時に OS 環境変数を保護する仕組みを導入（既存の OS 環境変数は .env による上書きを防止。override=True の際も protected set に含まれるキーは上書き除外）。

Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止: AI/リサーチ関連機能は datetime.today()/date.today() を参照せず、必ず呼び出し側から target_date を与える設計。
- フェイルセーフ: OpenAI や API 呼び出しが失敗した場合でも処理を中断させず、既定値（例: macro_sentiment=0.0）で続行する設計を優先。
- 冪等性: DB 書き込みは DELETE→INSERT や ON CONFLICT（jquants_client 側）を想定して冪等に行う。失敗時は明示的に ROLLBACK を試み、ロールバック失敗は警告ログ出力。
- テスト容易性: OpenAI 呼び出しや内部ユーティリティを差し替え可能（モック）にしてユニットテストを容易にしている。
- DuckDB 互換性への注意: executemany に空リストを渡すと失敗する制約を考慮してガードを実装。

利用上の注意（環境変数等）
- 必須環境変数（使用機能に応じて）:
  - JQUANTS_REFRESH_TOKEN（データ ETL）
  - KABU_API_PASSWORD（kabuステーション API）
  - OPENAI_API_KEY（kabusys.ai.news_nlp / regime_detector を使う場合）
- 自動 .env 読み込みはプロジェクトルートが検出できる場合に行われる（.git または pyproject.toml が目印）。無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

今後の想定（推測）
- Strategy / Execution / Monitoring に関する実行エンジンやブローカー実装（現在はモジュール公開のみ）。
- さらなる品質チェックルールや logging/monitoring の強化。
- OpenAI 呼び出しのコスト最適化やキャッシュ機構の追加。

----- 

（以上）