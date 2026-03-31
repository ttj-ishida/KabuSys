Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。フォーマットは Keep a Changelog に準拠します。
変更は主にコードベースからの実装内容を推測して記載しています（リリースノートの初期版）。

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

Added
- 初回リリース: kabusys パッケージの基本機能群を実装・公開
  - パッケージ公開情報
    - src/kabusys/__init__.py: __version__ = "0.1.0"
    - パッケージの外部公開モジュールとして data, strategy, execution, monitoring を想定してエクスポート

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および環境変数からの設定読み込みを実装
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）
    - 高度な .env パーサ実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメントの扱いに対応
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを停止可能
    - Settings クラスを提供し、アプリ設定（J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境モード・ログレベル）をプロパティで取得
    - 必須値未設定時は明示的な ValueError を発生させる（_require 関数）
    - env / log_level の受け入れ値検証を実装（development / paper_trading / live、DEBUG..CRITICAL）

- AI モジュール（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄単位でニュースを集約し OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出
    - タイムウィンドウ計算（JST 基準）を実装: 前日 15:00 JST ～ 当日 08:30 JST（UTC変換済）
    - 銘柄ごとに記事数・文字数（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム
    - バッチサイズ、リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで処理
    - レスポンスのバリデーションと数値スコアの ±1.0 クリップ
    - スコアの書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）
    - テスト容易性のため _call_openai_api を差し替え可能
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定
    - prices_daily / raw_news を参照して ma200_ratio とマクロ記事タイトルを収集
    - OpenAI（gpt-4o-mini, JSON mode）でマクロセンチメントを評価、フェイルセーフで失敗時は macro_sentiment=0.0
    - スコア合成後 market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス対策: datetime.today() 等を参照せず、クエリに date < target_date を使う設計
    - API 呼び出しの再試行、5xx の扱い、JSON パース失敗時のログ・フォールバックを実装

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム: calc_momentum (1M/3M/6M リターン、ma200 乖離)
    - ボラティリティ/流動性: calc_volatility (20日 ATR、相対 ATR、平均売買代金、出来高比)
    - バリュー: calc_value (PER・ROE を raw_financials から取得)
    - DuckDB を用いた SQL + Python 実装。結果は (date, code) をキーとした dict のリストで返却
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算: calc_forward_returns（horizons をサポート、入力検証あり）
    - IC（Spearman）計算: calc_ic（欠損や ties を考慮）
    - ランク関数・統計サマリー: rank, factor_summary
  - src/kabusys/research/__init__.py
    - 主要関数群を再エクスポート（zscore_normalize は data.stats から）

- データプラットフォーム / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルを用いた営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB データがない場合は曜日ベース（平日＝営業日）でフォールバックする一貫した振る舞い
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新、バックフィルと健全性チェックを実装
    - 最大探索日数やバックフィル日数等の安全策を実装（過度のループ・将来日付異常検出）
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを実装（取得/保存件数、品質チェック結果、エラー一覧）
    - ETL パイプラインの設計方針を反映（差分更新、backfill、品質チェックの扱い、id_token 注入可能性）
    - DuckDB 上でのテーブル存在チェックや最大日付取得等のユーティリティを実装
    - etl.py で ETLResult を公開

- DuckDB / トランザクション / 互換性対応
  - DuckDB 特有の挙動（executemany の空リスト不可、リストバインドの不安定さ等）を考慮した実装
  - DB 書き込み処理は BEGIN / COMMIT / ROLLBACK を適切に使い、ROLLBACK 失敗時のログを記録

- ロギング・堅牢性
  - 主要処理で詳細な logger 出力を追加（info/debug/warning/exception）
  - API 呼び出しの失敗時に例外を投げずフォールバックする箇所を明示（AI 呼び出しのフェイルセーフ等）

Security
- API キー・シークレットは環境変数で扱う設計（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）。設定未入力時は例外を出して明示的に扱う。
- 設定読み込みの自動化を提供するが、明示的に無効化するフラグを持つ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

注意事項（使用者向け / Migration）
- 必須環境変数
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants 連携）
  - KABU_API_PASSWORD（kabuステーション連携）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
- デフォルトのデータベースパス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- 自動 .env ロード
  - パッケージはデフォルトでプロジェクトルートの .env/.env.local を自動ロードします。テストや明示的管理が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しのテスト
  - news_nlp/_call_openai_api や regime_detector/_call_openai_api は unittest.mock.patch で差し替えてテスト可能です。
- ルックアヘッドバイアス対策
  - 多くの関数は date.today() を参照せず、target_date を明示的に受け取る設計です。バッチ実行やバックテストでの安全性を高めています。

互換性破壊（Breaking Changes）
- 0.1.0 は初回リリースのため breaking change はありません。

貢献／今後の予定（推定）
- strategy / execution / monitoring の具象実装（発注ロジック、監視エージェント、実行プロセス管理）
- 品質チェックモジュールの詳細実装と ETL パイプラインの公開 API
- テストカバレッジ拡大（DuckDB モック、OpenAI モック）
- ドキュメント（API リファレンス、運用手順）の充実

問い合わせ
- この CHANGELOG はコードからの推測に基づく初期ドキュメントです。実際の運用上の注意や詳細はソースコードと README を参照してください。