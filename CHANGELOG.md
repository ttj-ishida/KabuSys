Keep a Changelog
=================

すべての重要な変更点をこのファイルで記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に自パスから探索するため、CWD に依存しない。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル / ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの場合のインラインコメント処理（'#' の直前が空白/タブのときはコメント扱い）。
  - _load_env_file のオーバーライド保護:
    - OS 環境変数を保護する protected set を導入し、override=True 時でも保護キーは上書きしない。
  - Settings クラスによる型付き設定プロパティを提供:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを用意。
    - DUCKDB_PATH / SQLITE_PATH のデフォルト値（data/kabusys.duckdb, data/monitoring.db）。
    - KABUSYS_ENV の値検証（development, paper_trading, live）。
    - LOG_LEVEL の値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - 必須値未設定時は ValueError を送出する _require ヘルパーを提供。

- AI ニュース・レジーム機能（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとの記事を集約し OpenAI（gpt-4o-mini）でセンチメントを評価。
    - ニュースウィンドウ定義（JST基準）:
      - 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
      - calc_news_window 関数を提供。
    - バッチ処理:
      - 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）。
      - 1 銘柄あたりの最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しの堅牢化:
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ実装。
      - JSON Mode を想定したレスポンス処理と厳密なバリデーション（results リスト、code/score の型チェック）。
      - スコアは ±1.0 にクリップ。
    - DB 書き込み戦略:
      - 成功した銘柄コードのみを DELETE → INSERT で置換することで部分失敗時に既存スコアを破壊しない。
      - DuckDB の executemany の制約（空リスト不可）に対するガードを実装。
    - テスト容易性:
      - _call_openai_api を分離して unittest.mock.patch による差し替えを想定。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      マクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime を更新。
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp.calc_news_window を利用してウィンドウ抽出し、キーワードフィルタでタイトルを取得。
    - OpenAI 呼び出し（gpt-4o-mini）は専用実装を使用。API エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - レジームスコア合成とラベリング（bull/neutral/bear）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装し、例外発生時に ROLLBACK を実行。ROLLBACK 失敗時はログ出力。

- リサーチ/ファクター分析（src/kabusys/research）
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金, 出来高変化率）を計算。
    - DuckDB を用いた SQL ベースの計算。全関数は prices_daily / raw_financials のみ参照（実トレード API には非依存）。
    - データ不足時は None を返す設計。
  - feature_exploration.py:
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）calc_ic、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存を排し標準ライブラリのみで実装。
  - research パッケージの公開 API を __init__ でまとめて再エクスポート。

- データ/ETL とカレンダー（src/kabusys/data）
  - calendar_management.py:
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日）を行う。
    - calendar_update_job: J-Quants API から差分取得→冪等保存（save_market_calendar を呼び出し）。バックフィルと健全性チェックを実装。
  - pipeline.py:
    - ETLResult データクラス（target_date, 各種取得数/保存数, quality_issues, errors）を実装。
    - 差分更新・バックフィル・品質チェックを行う設計（jquants_client と quality モジュールを利用）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、market calendar 用ヘルパー等を実装。
  - etl.py:
    - pipeline.ETLResult を再エクスポート。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Notes / 実装上の設計判断（ドキュメント的補足）
- ルックアヘッドバイアス対策:
  - ニュース集計やレジーム判定、ファクター計算などで datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリでは target_date 未満や半開区間を使用して未来データ参照を防止。
- フェイルセーフ方針:
  - 外部 API（OpenAI / J-Quants）呼び出し失敗時は例外をそのまま上げる場面と、0.0 やスキップで継続する場面を用途に応じて使い分けている（例: マクロセンチメントはフォールバック 0.0）。
- テスト容易性:
  - OpenAI 呼び出しなどはモジュール内プライベート関数を差し替え可能な形（_call_openai_api を patch）で実装。
- DuckDB 互換性対策:
  - executemany に空リストを渡せない制約への対応や、日付値の変換ユーティリティを実装。

今後の予定（例示）
- strategy / execution / monitoring の具象実装（現状はパッケージ公開のみ）。
- ai モジュールのモデル選択・プロンプト改善や、より詳細な品質計測の追加。
- ETL の品質チェックの出力や自動対応ルールの拡充。

-----