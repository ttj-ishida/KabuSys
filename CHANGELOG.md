Changelog
=========
すべての注目すべき変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
------------

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__="0.1.0" と公開モジュール一覧を追加。

- 環境設定 / ロードユーティリティ
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
    - export KEY=val 形式や引用符付き値、コメントの扱いなど堅牢な .env パーサを実装。
    - OS 環境変数の保護（protected set）と override 挙動をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト向け）。
    - 必須環境変数取得用の _require、各種設定プロパティ（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル判定）を提供。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックと is_live / is_paper / is_dev のユーティリティを追加。

- AI 関連（OpenAI を用いたニュース解析・市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄単位のセンチメント（-1.0〜1.0）を算出する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算（calc_news_window）。
    - バッチサイズ、記事数・文字数のトリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密バリデーションを実装。
    - DuckDB への書き込みは部分成功を考慮して対象コードのみ DELETE → INSERT する冪等処理を実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する機能を実装。
    - prices_daily / raw_news を参照して ma200_ratio を算出し、マクロキーワードでフィルタした記事のタイトル群を LLM で評価。
    - API エラー・パースエラー発生時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - 計算結果を market_regime テーブルに冪等に書き込むトランザクション処理を実装。
    - OpenAI クライアント呼び出しをモジュール内独立実装（モジュール結合を避ける）。

- Data / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存。
    - market_calendar がない場合の曜日フォールバック、DB に一部のみ登録されている場合でも一貫した next/prev/get_trading_days の振る舞いを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日関連ユーティリティを提供。
    - 最大探索日数やバックフィル、健全性チェック等の安全策を導入。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの基盤を実装。
    - 差分更新、backfill、保存（jquants_client による冪等保存）、品質チェックの収集を想定した設計。
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティ等を追加。

- Research（因子・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等のファクター計算を実装。
    - DuckDB SQL を利用した高速集計、データ不足時の None 扱い等の設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas に依存せず標準ライブラリと DuckDB で実現。

- 内部ユーティリティ・互換性対策
  - DuckDB 0.10 の executemany 空リスト制約を考慮した実装（空チェックを行ってから executemany 実行）。
  - OpenAI API 呼び出しに対する詳細なエラー判定とリトライロジック（RateLimit, Connection, Timeout, APIError の status_code 判定など）。
  - JSON Mode の出力に対する堅牢なパース（前後の余計なテキストの切り出し）や、LLM が整数コードを返すケースへの対処。

Changed
- 設計方針として、全ての「基準日」は datetime.today()/date.today() に依存しない実装を徹底（ルックアヘッドバイアス防止）。target_date を明示的に渡す API を採用。

Fixed
- （初期リリースにつき該当なし）

Security
- 各種 API キー（OPENAI_API_KEY 等）取得は引数優先かつ環境変数フォールバックとし、未設定時は明示的に ValueError を発生させることで安全性を担保。

Notes / 注意事項
- 必要な環境変数の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（news/regime で必要）など。
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI 呼び出しは外部ネットワークに依存するため、テスト時は各モジュールの _call_openai_api をモックすることを推奨。
- jquants_client（jquants API 用クライアント）は別モジュールとして想定され、calendar/pipeline で利用される（本差分ではクライアント実装ファイルは含まれていない）。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（現状はパッケージ公開名のみ）。
- AI モデルの切替やプロンプト改善、スコアのキャリブレーション。
- ETL の品質チェックルール追加と通知フローの統合。

---- 
（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートはプロジェクト管理ツール／コミット履歴に基づいて正式に記載してください。）