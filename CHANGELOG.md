CHANGELOG
=========
すべての notable な変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」規約に従って管理しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-01
--------------------
Added
- 初期リリース。日本株自動売買プラットフォームのコア機能を追加。
  - パッケージエントリポイント
    - kabusys パッケージ（__version__ = 0.1.0）を追加。
  - 設定管理
    - 環境変数/.env を扱う settings モジュールを追加。
      - .env/.env.local の自動読み込み（プロジェクトルート判定: .git/pyproject.toml を探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - export KEY=val 形式やクォート、インラインコメント等の堅牢なパース処理。
      - OS 環境変数の保護（.env.local の上書き処理など）。
      - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
      - DB/監視/ログなどの既定値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK しきい値、LOG_LEVEL, KABUSYS_ENV 等）。
  - データプラットフォーム（data モジュール）
    - カレンダー管理 (calendar_management)
      - JPX マーケットカレンダーを扱うユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar がない場合の曜日ベースのフォールバック実装。
      - calendar_update_job: J-Quants から差分取得して冪等的に保存するジョブを実装（バックフィル、健全性チェック）。
    - ETL パイプライン (pipeline, etl)
      - ETLResult データクラスを公開し ETL 結果を構造化して返却。
      - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
      - jquants_client を用いた idempotent 保存フローに対応。
  - AI/自然言語処理（ai モジュール）
    - ニュースセンチメント分析 (news_nlp)
      - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を計算。
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）。
      - バッチ処理（最大 20 銘柄／回）、記事数・文字数トリミングによるトークン肥大化対策。
      - 再試行（429・ネットワーク・タイムアウト・5xx）は指数バックオフで実施。失敗はスキップして処理継続（フェイルセーフ）。
      - レスポンス検証ロジック（JSON 抽出、results キー検査、コード整合性、数値検証、±1.0 クリップ）。
      - ai_scores テーブルへの置換的書き込み（DELETE → INSERT）で部分失敗時の既存データ保護。
      - テスト性考慮: _call_openai_api の差し替え（patch）を容易に実装。
    - 市場レジーム判定 (regime_detector)
      - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とニュース由来マクロセンチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
      - LLM は gpt-4o-mini を使用（JSON 出力想定）。記事がない場合は macro_sentiment=0 として扱う（フェイルセーフ）。
      - API リトライ（429・ネット問題・タイムアウト・5xx）と冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
      - ルックアヘッドバイアス防止：datetime.today()/date.today() 参照を避ける設計、prices_daily クエリで target_date 未満を明示。
  - 研究用ユーティリティ（research モジュール）
    - factor_research
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）等の計算関数を実装。
      - DuckDB クエリ中心の実装で prices_daily / raw_financials のみ参照。結果は (date, code) キーの dict リストで返す。
    - feature_exploration
      - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman rank）の計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
      - pandas 等に依存しない純標準ライブラリ実装。
  - 内部ユーティリティ
    - DuckDB 用のテーブル存在チェック、日付変換、堅牢な SQL クエリ設計（空一覧を executemany で扱う制約への配慮等）。

Changed
- 初期リリースにつき該当なし。

Fixed
- 初期リリースにつき該当なし。
- 実装上の堅牢性改善点（.env パーサのエスケープ/クォート処理、OpenAI レスポンスパースの余分な前後テキスト処理など）を導入。

Security
- OpenAI API キーや外部トークンは環境変数で管理する設計。API キー未設定時は呼び出し側で明示的にエラーを返す（誤った無条件呼び出しを防止）。

Deprecated
- 初期リリースにつき該当なし。

Removed
- 初期リリースにつき該当なし。

Notes / 実装上の重要事項
- 環境変数／必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須扱い。
  - OpenAI を利用する ai モジュール（score_news, score_regime）は api_key 引数または OPENAI_API_KEY 環境変数が必須。
- DB 書き込みは原則冪等性を確保（DELETE → INSERT、ON CONFLICT 想定）。
- ルックアヘッドバイアス防止のため、すべての分析・スコアリング関数は target_date を明示的に受け取り、内部で現在時刻を参照しない。
- テスト容易性を考慮し、OpenAI 呼び出しを差し替え可能な内部関数を用意（unittest.mock.patch を想定）。
- DuckDB のバージョン差異（executemany の空リスト扱いなど）に配慮した実装が施されている。

今後の予定（例）
- ai モジュールの出力品質改善（プロンプト改善、より厳密な応答検証）。
- データ品質チェック（quality モジュール）との統合強化と品質レポート出力。
- 監視・実行モジュール（execution, monitoring）の追加実装（現状 __all__ に記載ありが実装は別途）。

--- 
（この CHANGELOG は、提供されたコードベースからの推測に基づいて作成しています。リリースノートとして用いる際は実際の git コミット・リリース内容と照合してください。）