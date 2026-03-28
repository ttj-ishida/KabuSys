Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。
このプロジェクトでは "Keep a Changelog" の形式に準拠しています。

[0.1.0] - 2026-03-28
--------------------

Added
- 基本パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"、公開モジュール一覧を定義。
- 環境設定管理:
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサの堅牢化（export prefix, クォート内エスケープ、インラインコメント扱い等）。
    - 必須環境変数取得ヘルパー(_require) と Settings クラスを提供:
      - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - オプション/デフォルト: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
    - KABUSYS_ENV / LOG_LEVEL の許容値検証、is_live/is_paper/is_dev の便利プロパティ。
- AI（自然言語処理）機能:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄別に集約し OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込み。
    - 処理の特徴:
      - JST ベースのニュースウィンドウ計算 (前日 15:00 ～ 当日 08:30 JST) を calc_news_window で提供。
      - 1 銘柄あたりの記事数 / 文字数制限（過大なプロンプト抑制）。
      - バッチ処理（最大 20 銘柄/コール）、JSON mode を利用。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
      - レスポンスの厳密な検証（JSON 抽出、results リスト、コード整合性、数値検証）。
      - 失敗はフェイルセーフでスキップし、部分成功時は該当コードのみ置換（DELETE → INSERT）して既存データを保護。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次市場レジーム（bull/neutral/bear）判定を行い market_regime テーブルへ保存。
    - 特徴:
      - prices_daily / raw_news からのデータ取得、calc_news_window を利用したウィンドウ選定。
      - マクロキーワードによる記事抽出（最大 20 件）。
      - OpenAI 呼び出し（gpt-4o-mini）への耐障害性（リトライ、5xx の取り扱い、フォールバック macro_sentiment=0.0）。
      - ルックアヘッドバイアス防止（datetime.today()/date.today() を参照しない、SQL に date < target_date を使用）。
      - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため _call_openai_api を独立実装で patch 可能。
- Data（データ基盤）機能:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - 特徴:
      - market_calendar が存在する場合は DB 値優先、未登録日は曜日ベースでフォールバック（土日休場扱い）。
      - 最大探索範囲 (_MAX_SEARCH_DAYS) を設定して無限ループ防止。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック含む）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの骨組みと ETLResult データクラスを提供（etl.py は pipeline.ETLResult を再エクスポート）。
    - ETLResult:
      - 実行結果の構造化（取得件数、保存件数、品質検査結果、エラー一覧など）。
      - has_errors / has_quality_errors プロパティ、辞書変換メソッド to_dict。
    - pipeline モジュールは差分更新、保存（jquants_client 経由で冪等保存）、品質チェック（quality モジュール）を想定した実装方針を含む。
  - src/kabusys/data/__init__.py: パッケージ初期化。
- Research（リサーチ）機能:
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value / Liquidity に関するファクター計算関数:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）。
      - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率。
      - calc_value: EPS/ROE から PER/ROE を計算（最新財務データを raw_financials から取得）。
    - DuckDB SQL ベース実装、外部 API へはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - ファクター評価ユーティリティ:
      - calc_forward_returns: 指定ホライズンに対する将来リターン（デフォルト [1,5,21]）。
      - calc_ic: スピアマンランク相関（Information Coefficient）計算（結合・欠損除外・最小件数チェック）。
      - rank: 同順位を平均ランクとするランク化ユーティリティ（丸めによる ties 対策あり）。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
- パッケージ公開・依存に関する設計上の注記:
  - OpenAI API（OPENAI_API_KEY）を引数で注入可能（api_key 引数を受け取る関数が多い）で、テスト時に環境変数に依存せず呼び出せる。
  - OpenAI 呼び出しの失敗は多くの箇所でフェイルセーフ（0.0 返却やスキップ）を採用。
  - DuckDB を主要 DB として利用する実装（関数は DuckDB 接続を受け取る）。
  - jquants_client / quality / その他外部クライアントは別モジュールとして想定（calendar_update_job や pipeline が利用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Known limitations / Notes
- PBR や配当利回りなどのバリューファクターは現バージョンで未実装（calc_value に記載あり）。
- DuckDB の executemany に関する互換制約への対処（空リストは渡さない等）を考慮した実装となっている。
- JSON mode を前提とした OpenAI のレスポンス処理で、稀に前後テキストが付く場合に備えた復元ロジックを実装しているが、完全なガードは環境による。
- 各種環境変数（JQUANTS_REFRESH_TOKEN など）が未設定の場合、Settings のプロパティが ValueError を投げるため注意が必要。
- 全体設計で「ルックアヘッドバイアス防止」を明示的に守る実装（datetime.today() 等の直接参照回避）を採用。

開発者向け備考
- テスト補助:
  - OpenAI 呼び出し箇所は module._call_openai_api を patch することで外部依存を差し替えられるよう設計されています。
- ログレベルや挙動の調整は環境変数（LOG_LEVEL, KABUSYS_ENV 等）で変更可能です。