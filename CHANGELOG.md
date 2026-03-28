# CHANGELOG

すべての重要な変更はこのファイルに記録します。
このプロジェクトは "Keep a Changelog" の慣習に従います。
比較的初期のリリースのため、主に初期実装（機能追加）を記載しています。

フォーマット:
- Unreleased セクションは現時点では空です（将来の変更用）。
- 各リリースは日付と主要な変更カテゴリ（Added / Changed / Fixed / Security）で整理しています。

[Unreleased]

[0.1.0] - 2026-03-28
--------------------
Added
- パッケージ初期リリース。kabusys の基本モジュール群を実装。
  - 公開パッケージ名: kabusys (バージョン 0.1.0)
- 環境変数・設定管理
  - 自動 .env ロード機構を実装（プロジェクトルートの検出は .git または pyproject.toml を基準に実施）。
  - .env / .env.local の読み込みロジック（優先順位: OS 環境変数 > .env.local > .env）。
  - 読み込みの上書き制御（override, protected）と .env パースの堅牢化（コメント・クォート・エスケープ対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、以下の設定プロパティを取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb)、SQLITE_PATH (デフォルト data/monitoring.db)
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - ヘルパープロパティ is_live / is_paper / is_dev
- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数のトリム）、レスポンス検証、スコア ±1.0 クリップを実装。
    - リトライ・エクスポネンシャルバックオフ（429, ネットワーク, タイムアウト, 5xx）を実装。
    - テスト容易性のため _call_openai_api をモック可能に設計。
    - calc_news_window ユーティリティを提供（JST ベースのニュースウィンドウ計算）。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT、部分失敗時に既存スコア保護）。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp 由来のマクロセンチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装（モジュール間の内部関数共有を避ける）。
    - API 呼び出しのリトライ、失敗時のフェイルセーフ（macro_sentiment = 0.0）、および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）の夜間更新ジョブ（calendar_update_job）を実装。
    - 営業日判定ユーティリティを提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB データ優先・未登録日の曜日フォールバック、最大探索日数の制限、バックフィルや整合性チェックを実装。
    - J-Quants クライアント経由での取得・保存処理へ依存（jquants_client を利用）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集計）。
    - ETL パイプライン設計方針の実装（差分取得、backfill、品質チェック連携、idempotent 保存）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディングデイ調整ロジック）を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベースの計算（prices_daily / raw_financials 参照）。結果は (date, code) キーを含む dict のリストとして返却。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン対応、ホライズンバリデーション）、IC（calc_ic: スピアマンランク相関）、rank、factor_summary（基本統計量）を実装。
    - pandas 等に依存せず純粋に標準ライブラリ + duckdb で実装。
- ロギングと設計方針
  - 主要関数はルックアヘッドバイアス回避のために datetime.today()/date.today() を直接参照しない（target_date パラメータ駆動）。
  - OpenAI API 呼び出しはエラーに対して堅牢に振る舞う（リトライ/フェイルセーフ/ログ）。
  - テスト容易性を考慮したフック（_call_openai_api の差し替えなど）を提供。

Changed
- 初期リリースのため「変更」は無し（ベースライン実装）。

Fixed
- 初期リリースのため「修正」は無し。

Security
- 初期リリースのため「セキュリティ」項目は無し。
- 注意: OpenAI API キー等の機密情報は Settings 経由で環境変数により設定する前提。.env の取り扱いはファイル読み込みのみであり、暗号化等は行わない。

Notes / 補足
- DuckDB テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が前提となる実装です。実運用前にスキーマ定義と初期ロードが必要です。
- J-Quants クライアント（kabusys.data.jquants_client）の実装を前提にしている箇所があるため、外部 API クライアントの接続設定やトークン管理を行ってください。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を活用しています。API 仕様や SDK のバージョン変更による影響に注意してください（例: APIError.status_code の有無等に対策済み）。
- パッケージエクスポート: __all__ に data, strategy, execution, monitoring が含まれていますが、本差分で提供されるサブモジュールは data / ai / research 等が中心です。strategy/execution/monitoring の具象実装は今後追加予定。

今後の予定（例）
- strategy / execution / monitoring の実装（実運用向け発注ロジック・モニタリング）
- データ品質チェックモジュールの強化と ETL ワークフローの自動化
- テストカバレッジ拡充と CI 設定

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する際は、リリース日や詳細をプロジェクト実態に合わせて調整してください。）