Keep a Changelog
=================

すべての重要な変更をこのファイルで記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-29
------------------

Added
- 初回公開: KabuSys パッケージ (バージョン 0.1.0)
  - パッケージトップ: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定、主要サブパッケージをエクスポート。

- 環境設定/ローダ
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
    - .env のパーサは export KEY=val 形式、引用符（シングル/ダブル）とバックスラッシュエスケープ、行内コメント処理に対応。
    - override / protected の概念により OS 環境変数を保護して .env.local を上書き読み込み可能。
    - Settings クラスを提供:
      - 必須環境変数取得時の検証（_require による ValueError）。
      - J-Quants / kabu API / Slack / DB パス等のプロパティ（デフォルト値やパス展開を含む）。
      - 環境（development/paper_trading/live）とログレベルの検証。
      - is_live / is_paper / is_dev の便利プロパティ。

- AI モジュール: ニュース NLP / レジーム判定
  - src/kabusys/ai/news_nlp.py
    - score_news(conn, target_date, api_key=None)
      - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ算出（calc_news_window）。
      - raw_news と news_symbols を結合し、銘柄ごとに最新記事を集約。
      - 1 API コールあたり最大 _BATCH_SIZE(20) 銘柄をバッチ送信。
      - 各銘柄は最大記事数・最大文字数でトリムしてプロンプトに含める。
      - OpenAI（gpt-4o-mini）呼び出しは再試行（429/ネットワーク/タイムアウト/5xx）を行い、指数バックオフを適用。
      - レスポンスの検証とスコアの ±1.0 クリップ、部分成功時は既存スコアを保護する形で ai_scores テーブルへ置換（DELETE → INSERT、トランザクション）。
      - テスト容易性: _call_openai_api をモック可能。
  - src/kabusys/ai/regime_detector.py
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離率（ma200_ratio）を計算（過去データのみを使用してルックアヘッド回避）。
      - raw_news からマクロキーワードに一致するタイトルを抽出、LLM によりマクロセンチメントを評価（重み付け合成: MA70% / Macro30%）。
      - レジームスコアを -1.0〜1.0 にクリップし label を決定（'bull'/'neutral'/'bear'）。
      - API 失敗時は macro_sentiment=0.0 のフォールバック（例外を投げずに継続）。
      - idempotent な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。
      - テスト容易性: _call_openai_api をモック可能。

- Research（因子・特徴量解析）
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。
      - Momentum: 約1/3/6ヶ月リターン、200日 MA 乖離。
      - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
      - Value: PER, ROE（raw_financials の直近レコードを使用）。
    - DuckDB 上の SQL ウィンドウ関数を活用し、(date, code) ベースの結果リストを返す。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル数不足時は None を返す。
    - rank: 同順位は平均ランクを返す実装（丸めにより ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算（pandas 等に非依存）。

- Data プラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理: market_calendar テーブルを用いた営業日判定と夜間更新ジョブ(calendar_update_job)を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB データが無い場合は曜日ベース（週末除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得し保存、バックフィルと健全性チェックを実装（過度に将来の日付が検出された場合はスキップ）。
  - src/kabusys/data/pipeline.py
    - ETL の方針に沿ったユーティリティ群（差分取得, 保存, 品質チェック）の下地を実装。
    - ETLResult データクラスを定義（target_date / fetched/saved カウント / 品質問題 / エラー等）、has_errors / has_quality_errors / to_dict を提供。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/__init__.py
    - パッケージ初期化（現状は空）。

- 共通・実装上の配慮
  - DuckDB を主要な組み込み分析 DB として利用（全モジュールで DuckDB 接続を受け渡す設計）。
  - ルックアヘッドバイアスを避けるため、関数内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的引数として受け取る）。
  - API 呼び出しにおけるフェイルセーフ設計: OpenAI 呼び出し失敗時は可能な範囲で安全にフォールバックし、例外は上位に上げるかログ記録の上で継続。
  - トランザクションとロールバックの適切なハンドリング、DuckDB の executemany の制約に対するガード（空リスト回避）。
  - ログ（logger）を各モジュールに配置し詳細な情報を出力。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。
  - ただし、実装上の堅牢性（APIリトライ、JSONパースのフォールバック、DB ロールバック/保護等）を重視して実装。

Security
- 環境変数ロード時に OS 環境変数を保護する protected 機能を導入（.env.local でも OS 変数を不用意に上書きしない）。
- 必須トークン取得時に未設定であれば明示的に ValueError を投げることで誤設定を早期検出。

Notes / Design decisions
- テスト容易性: OpenAI 呼び出し部分はモジュール内の _call_openai_api を patch して差し替え可能。
- 外部ライブラリ依存を抑え、分析ロジックは標準ライブラリ + DuckDB SQL で実装（Research モジュールは pandas 等に依存しない）。
- AI レイヤー（news_nlp / regime_detector）は JSON Mode を利用し、レスポンスの厳密な検証を行う（余計なテキスト混入時の補正も実装）。
- DB 書き込みは冪等性を重視（DELETE → INSERT のパターンなど）、部分失敗時に既存データを不必要に消去しない方針。

今後の予定（例）
- ai モジュールのレスポンス検証・プロンプト改善、モデル切替の抽象化。
- pipeline の ETL 実行フロー（差分算出→保存→品質チェック）の高レベル API 実装。
- 単体テスト・結合テストの追加（特に OpenAI 呼び出しのモックを用いたテスト群）。

もし CHANGELOG に追記したい特定の変更点やリリース日付の変更、より細かいカテゴリ分け（例: Performance / Documentation）をご希望でしたらお知らせください。