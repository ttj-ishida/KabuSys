CHANGELOG
=========

この変更履歴は「Keep a Changelog」仕様に準じて作成しています。  
セマンティックバージョニングを使用しています。  

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys.__init__ にパッケージ情報と __version__ = "0.1.0" を追加。
- 環境設定管理:
  - kabusys.config:
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - export KEY=val 形式のサポート、クォートやバックスラッシュエスケープの取り扱い、インラインコメント処理。
    - override / protected の概念を持つ .env ローダー実装（OS環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム環境などをプロパティで取得（必須環境変数取得時のエラー報告を含む）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
- AI（自然言語）モジュール:
  - kabusys.ai.news_nlp:
    - raw_news テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いたバッチセンチメント分析を実装。
    - JSON Mode（厳密な JSON 出力）を前提にレスポンスをバリデーションして ai_scores テーブルへ書き込み。
    - チャンク処理（最大 20 銘柄/回）、記事・文字数のトリム、最大リトライ（429/ネットワーク/5xx）と指数バックオフ。
    - レスポンスパースの堅牢化（前後テキスト混入時の {} 抽出）、スコア ±1.0 クリップ、部分書き換え（DELETE → INSERT）による冪等性と部分失敗耐性。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルに保存する処理を実装。
    - マクロニュース抽出用のキーワードリスト実装、OpenAI 呼び出しのリトライ・フォールバック（API失敗時は macro_sentiment=0.0）。
    - レジーム計算ロジック、ラベル閾値、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK 処理を実装。
    - ニュース窓は news_nlp.calc_news_window と連携。
- Data（データ基盤）モジュール:
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティ。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar が未取得/部分的な場合の曜日ベースフォールバックと一貫性のある探索ロジック（最大探索日数制限）。
    - calendar_update_job により J-Quants からの差分取得と冪等保存（バックフィル、健全性チェック）を実装。
  - kabusys.data.pipeline / etl:
    - ETL パイプライン用の ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得・バックフィル・品質チェックの方針をコードで反映（jquants_client との連携を想定）。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - 汎用ユーティリティ:
    - DuckDB テーブル存在チェック、日付変換ユーティリティ等を実装。
- Research（リサーチ）モジュール:
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（平均売買代金、出来高比）およびバリュー（PER, ROE）ファクター計算を実装。
    - DuckDB を用いた SQL ベース実装で、prices_daily / raw_financials を参照。
    - データ不足時の None 返却やログ出力を含む仕様。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank / factor_summary 等の統計ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
- パッケージ内部の設計方針・安全対策（全体）:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない（target_date を引数に取る実装）。
  - OpenAI 呼び出し周りにリトライ・バックオフ・タイムアウト・レスポンス検証を組み込み、API障害耐性を確保。
  - DB 書き込みは可能な限り冪等操作（DELETE→INSERT、ON CONFLICT 想定）を行う。
  - テスト容易性を考慮し、内部の API 呼び出し関数を patch できる設計を採用。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / Usage highlights
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（スコア計算系で必要）
- DuckDB を用いるため、各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に受け取る。
- OpenAI クライアント呼び出しは OpenAI SDK（chat.completions.create）を想定して実装されている。テスト時はモック差し替え可能。
- 一部関数は外部 API（J-Quants、OpenAI）呼び出しを伴うため、実運用では API キーやネットワーク設定が必要。

今後の予定（例）
- ai モジュールのモデル切替や評価メトリクスの拡充
- ETL のジョブスケジューリング/監視機能の追加
- 追加のファクター・特徴量探索手法の実装

---
この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに基づいて追記・修正してください。