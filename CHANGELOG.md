Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/）に準拠しています。

バージョン表記は PEP 440 に準拠します。

Unreleased
----------

（現在のリポジトリにはリリース済みバージョン 0.1.0 が設定されています。今後の変更はここに記載してください。）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py で __version__ = "0.1.0" を定義。パッケージトップは data, strategy, execution, monitoring を公開。
- 環境設定/読み込み:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
    - .env の行パースを堅牢化（export 形式対応、シングル/ダブルクォートとエスケープ処理、インラインコメントの扱いなど）。
    - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視/システム関連の設定をプロパティ経由で取得（必須キーは _require で検証）。
    - 環境変数の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
- AI モジュール（OpenAI を用いたニュース解析・市場レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - スコア取得ロジック: ウィンドウ計算、トリム（記事数・文字数制限）、バッチ化（最大 20 銘柄/回）、JSON モード応答のバリデーション、スコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ。
    - テストで差し替え可能な _call_openai_api フックを用意。
  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）、JSON パースとリトライ処理、API 失敗時は macro_sentiment=0.0 のフェイルセーフを実装。
    - ルックアヘッドバイアス回避の設計（date < target_date の排他条件、datetime.today() を参照しない）。
- データプラットフォーム / ETL:
  - src/kabusys/data/pipeline.py
    - ETL の結果を格納する ETLResult データクラス（取得数・保存数・品質問題・エラー情報など）。
    - 差分更新・バックフィルや品質チェックを想定した設計（注: jquants_client や quality モジュールを利用）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。
- マーケットカレンダー管理:
  - src/kabusys/data/calendar_management.py
    - market_calendar に基づく営業日判定・前後営業日の取得・期間内営業日リスト取得・SQ 判定などのユーティリティを提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数で無限ループ防止。
    - calendar_update_job を実装し J-Quants API（jquants_client.fetch_market_calendar）からの差分取得と保存を想定、バックフィルと健全性チェックを行う。
- リサーチ / ファクター計算:
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算。
    - DuckDB SQL を用いた実装で、外部 API や実口座へのアクセスは行わない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括 SQL で算出。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランク変換・基本統計量サマリを提供。
  - src/kabusys/research/__init__.py で主要関数をエクスポート。
- データユーティリティ:
  - src/kabusys/data/calendar_management.py, pipeline.py 等が DuckDB を直接参照する形でデータ操作を行うことを明記。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- 環境変数の自動読み込みにおいて、既に存在する OS 環境変数を保護するため protected set を導入し .env.local の上書き制御を行う仕組みを実装。

Notes / 実装上の設計判断（要点）
- ルックアヘッドバイアス回避:
  - AI 評価・ファクター計算・ニュース集計など、すべての時間判定は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計。
- DB 書き込みの冪等性:
  - market_regime, ai_scores などは BEGIN / DELETE / INSERT / COMMIT のパターンで冪等に更新。エラー時は ROLLBACK を試行し、失敗時はロギング。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提に JSON Mode を利用。429/ネットワークエラー/タイムアウト/5xx に対して指数的バックオフでリトライする実装。レスポンスのパース失敗はフェイルセーフでスコア 0.0 やスキップにフォールバック。
  - テストのために _call_openai_api をモック可能にしている。
- DuckDB 互換性注意:
  - executemany に空リストを渡すと問題となるバージョンの回避処理（空チェック）を実装。
- 外部依存:
  - jquants_client、quality モジュール、kabu API クライアント等は本コードで参照されるが実装は別モジュールとして想定している（利用時に提供が必要）。
- 環境変数/設定:
  - 必須の機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings 経由で取得・検証する設計。未設定時は ValueError を送出する箇所があるため、運用時は .env 等での設定が必須。

既知の制約・今後の TODO（推奨）
- news_nlp / regime_detector の LLM プロンプト・モデル指定は固定（gpt-4o-mini）。将来的にモデル差替えを容易にする設定化が望ましい。
- raw_financials に基づく PBR・配当利回りは未実装（calc_value の拡張ポイント）。
- jquants_client の実装と ETL 実行ワークフロー（スケジューラ・監視）をセットアップする必要あり。
- strategy, execution, monitoring パッケージは __all__ に含まれるが本差分での実装は省略（将来実装予定）。

連絡先・補足
- 実装ログや詳細な動作は各モジュールの docstring / logger 出力に記載されています。運用前には Settings を用いた環境変数の準備（.env/.env.local）と DuckDB スキーマの準備を行ってください。