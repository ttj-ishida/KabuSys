CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記載します。本ファイルは「Keep a Changelog」の形式に準拠しています。
タグ付けはセマンティックバージョニングに従います。

フォーマットの説明:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py によるパッケージエクスポート（data, strategy, execution, monitoring）。
- 設定管理モジュール
  - src/kabusys/config.py
    - .env ファイルと環境変数を自動で読み込む仕組みを実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - export KEY=val 形式やクォート、インラインコメントを考慮した .env パーサを実装。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須設定取得ヘルパー _require と Settings クラスを提供。
    - サポートする主要環境変数（例）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY,
        DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）, KABUSYS_ENV, LOG_LEVEL。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値の列挙）。
- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチリクエストしてセンチメントスコアを算出・ai_scores テーブルへ書き込む。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ化（最大 20 銘柄）・記事トリム（最大記事数・文字数制限）・レスポンスバリデーション（JSON 抽出/検証）を実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理。失敗時は部分的にスキップして継続するフェイルセーフ設計。
    - テスト容易性のため、OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に保存。
    - OpenAI 呼び出しのリトライ/フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - DuckDB クエリでルックアヘッドバイアスを防止する実装上の配慮（target_date 未満のみ参照、datetime.today() を直接参照しない）。
- データプラットフォーム（ETL / カレンダー）
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを導入し、ETL 実行結果（取得数/保存数/品質問題/エラー）を構造化。
    - 差分取得、バックフィル、品質チェックの設計方針を明確化（品質問題は収集するが ETL を継続）。
    - DuckDB を想定したテーブル存在チェック・最大日付取得ユーティリティを実装。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定・次/前営業日の取得・期間内営業日リスト取得・SQ 判定ロジックを実装。
    - データ未取得時は曜日ベース（土日除外）でフォールバックする仕様。
    - calendar_update_job による J-Quants からの差分取得・バックフィル（直近 N 日の再取得）・健全性チェック（将来日付の異常検出）を実装。
    - DB 登録値優先、未登録日は曜日フォールバックで next/prev と一貫した挙動を提供。
- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB の SQL/ウィンドウ関数で計算する機能を実装。
    - 欠損・データ不足時の None 処理、ログ出力設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、引数検証）を実装。
    - Spearman ランク相関（IC）を計算する calc_ic 実装（NULL/非有限値排除・最小サンプルチェック）。
    - ランク変換（同順位は平均ランク）及び factor_summary（count/mean/std/min/max/median）を実装。
  - src/kabusys/research/__init__.py で主要関数をエクスポート。
- データユーティリティ
  - src/kabusys/data/__init__.py（パッケージ起点、将来の拡張用）
- テスト性・ロバストネス設計に関する共通点
  - 外部 API 呼び出しは retry/backoff とフォールバック（安全なデフォルト値）で扱う。
  - LLM 呼び出し箇所はテストで差し替え可能な設計（内部 _call_openai_api の patch）。
  - ルックアヘッドバイアス回避のため、現在日時を直接参照しない設計が多くの関数で採用（target_date を明示的に受け取る）。
  - DuckDB に対する互換性考慮（executemany の空リスト回避等）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 環境変数に機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を扱うため、
  - .env の読み込みはデフォルトでプロジェクトルートから行うが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - Settings._require で未設定時は ValueError を投げるため、実行環境での適切な秘密情報管理を推奨。

マイグレーション / 注意事項
- OpenAI を利用する機能（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY を必須とする。未指定だと ValueError を送出する。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が必要。ETL とデータ保存処理を使用する前に DB スキーマ準備を行ってください。
- calc_news_window 等の時間ウィンドウは UTC naive datetime を返します。DB 側の raw_news.datetime は UTC 前提で保存されている想定です。
- ai_scores / market_regime への書き込みは冪等性（DELETE→INSERT や ON CONFLICT 相当の保存）を意識した実装になっていますが、DB バージョンや接続設定により動作差が出る可能性があるためテスト環境で動作確認してから本番導入してください。

今後の予定（示唆）
- strategy / execution / monitoring の具象実装追加（現状はパッケージエクスポート地点のみ）。
- jquants_client の実装や DB スキーマ定義・初期ロードスクリプトの追加。
- 監視・発注パイプライン（Slack 通知・発注安全ガード等）の実装強化。