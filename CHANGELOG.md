CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース作成時の想定日です。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコア機能群を追加。
  - パッケージ化:
    - src/kabusys/__init__.py でバージョン (0.1.0) と公開モジュールを定義。
  - 設定・環境変数管理:
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml から探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - export 形式やクォート・エスケープ・インラインコメントを考慮した堅牢な .env パーサ実装。
      - OS 環境変数を保護する protected 機能（.env.local は上書き、.env は既存未設定のキーのみセット）。
      - Settings クラスでアプリ設定をプロパティとして公開（J-Quants / kabu API / LINE / DB パス / 監視閾値など）。
      - KABUSYS_ENV と LOG_LEVEL の値検証・ユーティリティプロパティ（is_live / is_paper / is_dev）。
  - AI（NLP / レジーム判定）:
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを評価して ai_scores に保存。
      - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST の UTC 変換）。
      - バッチ処理（最大20銘柄）、1銘柄あたり記事数 / 文字数制限、レスポンス検証・スコアクリップ（±1.0）。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフとリトライ、API エラーはフェイルセーフでスキップ。
      - テスト容易性のため OpenAI 呼び出し関数の差し替えを想定（unittest.mock.patch）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み70%）＋マクロニュースの LLM センチメント（重み30%）で日次市場レジーム（bull/neutral/bear）を算出。
      - prices_daily と raw_news を参照、calc_news_window と整合したウィンドウでマクロ記事を抽出。
      - OpenAI 呼び出しは独自実装、API障害時は macro_sentiment=0.0 にフォールバック。
      - 結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
  - Research（ファクター / 特徴量探索）:
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離等を計算。データ不足時は None を返す設計。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials から EPS/ROE を参照し PER/ROE を算出。
      - DuckDB を用いた SQL + Python 実装、外部取引 API にはアクセスしない設計。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（ホライズンは検証済み）。
      - calc_ic: Spearman（ランク相関）に基づく IC 計算、データ不足（<3件）は None。
      - rank / factor_summary: ランク変換（同位は平均ランク）と統計要約（count/mean/std/min/max/median）。
    - src/kabusys/research/__init__.py で便利関数の再エクスポートを提供（zscore_normalize 等）。
  - Data（ETL / カレンダー管理 / パイプライン）:
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
      - market_calendar が未登録の場合は曜日ベース（土日非営業）でフォールバック。
      - calendar_update_job: J-Quants から差分取得・バックフィル・保存（健全性チェック、保存は jquants_client 経由）。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラー管理）。
      - 差分更新・バックフィル・品質チェックを想定したパイプライン設計（jquants_client と quality モジュールを利用）。
  - 汎用設計・品質:
    - DuckDB を主要なローカル DB として利用する設計（SQL を含む処理は DuckDB 接続を受け取る形）。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計方針（target_date ベースの処理）。
    - DB 書き込みは冪等・トランザクション制御（BEGIN/COMMIT/ROLLBACK）を採用。
    - ロギング・警告の充実（失敗やフォールバック時に WARN/INFO/DEBUG を出力）。
    - テスト容易性: API キー注入、OpenAI 呼び出し差し替え箇所の用意、sleep の差し替え等。

Fixed
- 初期リリースのため該当なし（設計上フェイルセーフやフォールバックが多く実装されていることを明記）。

Changed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数の取り扱いに配慮:
  - OS 環境変数は protected として .env の上書きを防止。
  - OpenAI API キーは引数から注入可能で環境変数依存を緩和。
- 外部への発注機能はこのリリースの範囲外（データ取得・分析・判定ロジック中心）。

Notes / 補足
- 多くの外部依存（OpenAI、J-Quants、kabuステーション への接続）はクライアントモジュール経由または環境変数で注入する設計です。実運用時は各 API のアクセス情報（トークン・エンドポイント等）を .env に設定してください。
- テストを容易にするため、外部 API 呼び出し箇所は差し替え可能な実装になっています。ユニットテストでは該当関数をモックしてロジックを検証してください。
- DuckDB のバージョンや SQL バインドの仕様差異（executemany の空リスト不可など）を考慮した実装が散見されます。DuckDB のバージョンアップ時は互換性テストを推奨します。