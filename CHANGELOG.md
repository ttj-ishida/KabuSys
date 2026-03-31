Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に準拠しています。  

フォーマット:
- 変更はセマンティック バージョニングに従います。
- 日付はリリース日を示します。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-31
--------------------

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しています。
主にデータ基盤、リサーチ用ファクター計算、ニュース NLP / レジーム判定の AI 周りの処理、環境設定周りのユーティリティを含みます。

Added
- パッケージ基盤
  - src/kabusys/__init__.py にてパッケージエントリとバージョンを定義（0.1.0）。
  - 主要サブパッケージを公開: data, strategy, execution, monitoring。

- 環境設定
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val 形式、クォート内のエスケープ、インラインコメント等に対する堅牢な .env パーサ実装。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数のサポート。
    - OS 環境変数を保護する protected キー概念（.env.local は .env を上書き、ただし OS の既存キーは保護）。
    - Settings クラス: J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル等のプロパティ、必須変数未設定時の明確なエラーメッセージ。
    - env/log_level のバリデーション（許容値の定義）。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）を calc_news_window で提供。
    - チャンク化(_BATCH_SIZE=20)、1銘柄あたりの記事数と文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトリム。
    - JSON Mode を利用した厳密な JSON レスポンス処理とレスポンスの堅牢なバリデーション（_validate_and_extract）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ・リトライ、失敗時はスキップ（フェイルセーフ）。
    - テスト容易性のため _call_openai_api を patch 可能に実装。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を決定。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足は中立判定）と macro_sentiment の LLM 評価を合成。
    - マクロキーワードによる raw_news フィルタリング、最大記事数制限、OpenAI 呼び出しのリトライロジックを実装。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試行。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を送出。

- データ基盤（Data）
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない／未登録日の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分でカレンダーを取得して market_calendar を冪等更新（バックフィル・健全性チェック付き）。
    - 最大探索日数制限で無限ループ防止、date オブジェクトのみ利用して timezone 混入を防止。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラス（target_date、取得/保存件数、品質問題、エラーリスト等）を提供し、ETL 実行結果の構造化をサポート。
    - 差分更新ロジック、バックフィル、品質チェックの設計方針をコードに反映（jquants_client の save_* を利用して冪等保存を想定）。
    - DuckDB の挙動（executemany の空リスト制約）を考慮した実装。

  - その他 data パッケージ基盤ファイル（__init__.py）を準備。

- リサーチ（Research）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比）およびバリューファクター（PER, ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算する関数を実装。
    - データ不足時は None を返す設計。
    - SQL ウィンドウ関数を利用して効率的に集計。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する汎用処理。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（結合・欠損除外・最小有効レコード判定）。
    - rank: 同順位を平均ランクにするランク化実装（丸めで ties の検出漏れ対策）。
    - factor_summary: count/mean/std/min/max/median を算出する統計要約関数。
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）。

- 研究用再エクスポート
  - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize の re-export 等）。

- 依存とテスト支援
  - OpenAI SDK（OpenAI クライアント）と DuckDB を前提とした実装。
  - テスト時は内部の _call_openai_api を patch して API 呼び出しをモック可能に設計。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キー・他秘密情報は Settings を介して環境変数から取得。.env 自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト/CI 時の誤用を軽減。

Notes / 実装上の設計上の注意点
- ルックアヘッドバイアス防止: news / regime / research 関数群はいずれも datetime.today()/date.today() を直接参照せず、必ず target_date 引数で日付を与える設計。
- DuckDB 互換性: executemany や配列バインドの挙動に配慮した実装（空リストの executemany 回避など）。
- 冪等性: DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT を想定）して再実行耐性を持たせている。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は基本的に処理を継続（0/空辞書/中立値 等でフォールバック）し、致命的なエラーのみ上位へ伝播する方針。

References
- 詳細な設計方針はヘッダーコメントに記載（各モジュール内の docstring を参照）。

---- 

（変更履歴はコードから推測して作成しています。実際のコミット履歴やリリースノートと異なる場合があります。必要であれば差分・コミットログを提供いただければより正確な CHANGELOG を作成します。）