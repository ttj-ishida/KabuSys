Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

Unreleased
----------
（なし）

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（src/kabusys/config.py）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理などのロバストな解析（_parse_env_line）。
  - 環境変数保護ロジック: OS 環境変数を protected として .env の上書きから保護（.env と .env.local の読み込み順制御）。
  - Settings クラスを提供（settings インスタンス）: J-Quants / kabu API / LINE / DB パス (DuckDB, SQLite) / 監視設定（PID, kill flag, CPU/memory/disk 閾値）/環境（development/paper_trading/live）/ログレベルなどをプロパティで取得。バリデーション（有効な env 値・ログレベルの検査）と必須キー検出で例外を投げる機能を含む。
- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの基本インターフェース実装（ETLResult データクラスの公開、src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - 差分取得・保存・品質チェックを想定した設計（backfill, calendar lookahead などの設定）。
    - ETLResult: 品質問題およびエラーの集約、辞書化（監査ログ用）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar がない場合の曜日ベースのフォールバック、DB 値優先の一貫した挙動、最大探索日数制限による安全対策を採用。
    - calendar_update_job: J-Quants クライアント経由で差分取得し冪等保存する夜間バッチ処理（バックフィル・健全性チェックを含む）。
  - DuckDB 互換性への配慮（executemany の空リスト回避、日付変換ユーティリティ等）。
- 研究用モジュール（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials を用いた PER / ROE 計算（最新財務データを target_date 以前から取得）。
    - 全関数は DuckDB の prices_daily / raw_financials のみを参照し、ルックアヘッドバイアスを避ける設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損・同順位・最小サンプルチェック対応）。
    - rank, factor_summary: ランク化（同順位は平均ランク）と基本統計量の算出を提供。
  - zscore_normalize をデータユーティリティから再公開（src/kabusys/research/__init__.py）。
- AI（自然言語処理）機能（OpenAI を利用）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - calc_news_window: 前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）のウィンドウ計算。
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに最大記事数・最大文字数でトリムしたテキストを gpt-4o-mini（JSON Mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ冪等的に保存。
    - バッチサイズ・トークン肥大化対策、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証（JSON 抽出、results フィールドチェック、コードの正規化、スコア数値検査、クリップ処理）を実装。
    - API 呼び出し箇所はテスト時に差し替え可能（_call_openai_api へのパッチを想定）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次の market_regime テーブルへ書き込む score_regime を実装。
    - マクロニュースのフィルタ（キーワードリスト）・最大記事数・LLM 呼び出し（gpt-4o-mini）・リトライ/フォールバック（API 失敗時 macro_sentiment=0）・クリップ・閾値判定によるラベル化（bull/neutral/bear）を実装。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で行う。
- テスト性・品質への配慮
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を直接参照しない実装方針（一部ロジックで受け渡しの target_date を利用）。
  - API 呼び出し箇所は内部でラップしてあり、ユニットテストで差し替えやモックが可能。
  - 詳細なログ出力（warning/info/debug）を多所に実装し、エラー時のフォールバックや挙動を明瞭化。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 外部 API キーは引数注入または環境変数 OPENAI_API_KEY を参照する設計とし、未設定時は明示的に例外を発生させることで誤設定を早期に検出するようにしています。

Notes / 実装上の重要な設計判断
- DuckDB を主要なデータストアとして想定。executemany の空リストや日付型の取り扱いに関して互換性を考慮した実装を行っています。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスパースに冗長なテキストが混入した場合のリカバリ（{} 抽出）を実装しています。
- いくつかの安全策（最大探索日数・バックフィル期間・健全性チェック）を組み込み、無限ループや過剰取得を防ぐようにしています。
- top-level の __all__ で strategy / execution / monitoring 等を公開していますが、外部 API（実際の発注など）はこのスナップショットには含まれておらず、研究/データ/AI のコア機能に重点を置いた初期リリースです。

今後の予定（例）
- execution / monitoring の詳細実装（実売買連携・プロセス監視）
- 追加のファクター・リサーチツール・バックテスト機能
- OpenAI 以外の NLP バックエンド抽象化・キャッシングやコスト最適化

--- 
この CHANGELOG はコード内のドキュメントと実装から推測して作成しています。実際のリリースノートと差異がある場合は、追加の情報を元に更新してください。