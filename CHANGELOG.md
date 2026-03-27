# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

※この CHANGELOG は提供されたコードベースの内容から機能追加・設計方針・注意点を推測して作成しています。

## [Unreleased]
- 今後の変更点やマイナー改善をここに記載します。

## [0.1.0] - 2026-03-27
Initial release — 基本機能の実装を行いました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期バージョン（__version__ = "0.1.0"）。
  - サブパッケージ公開インターフェース: data, research, ai, 等を含むモジュール構成。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して決定（CWD に依存しない）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理を考慮。
  - Settings クラスを提供し、アプリケーションで利用する各種設定値をプロパティ経由で安全に取得可能。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーション、is_live / is_paper / is_dev ヘルパー

- AI（自然言語処理・市場レジーム判定）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存。
    - 1銘柄あたりの最大記事数・文字数制限、バッチ処理（最大 20 銘柄/コール）を実装してトークン肥大化に対処。
    - API リトライ（429 / 接続障害 / タイムアウト / 5xx）を指数バックオフで実行。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、既知コード照合、数値検証）とスコアクリッピング（±1.0）。
    - DB 書き込みは部分原子性を意識し、取得できた銘柄のみ DELETE → INSERT で置換（部分失敗時に既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出し点にパッチ可能な内部関数を採用（_call_openai_api を差し替え可能）。
    - ユーザー向けログ出力あり（対象記事数・チャンク数・書込み銘柄数等）。
  - レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込み。
    - ma200_ratio の計算は target_date 未満のみを参照してルックアヘッドを防止。
    - マクロニュースは kabusys.ai.news_nlp のウィンドウ計算を利用（_MACRO_KEYWORDS に基づくフィルタ）。
    - OpenAI 呼び出しは独立実装（news_nlp の内部関数を共有しないことでモジュール結合を低減）。
    - API 障害時は macro_sentiment=0.0（中立）にフォールバックするフェイルセーフ実装。
    - 書き込み処理は BEGIN / DELETE / INSERT / COMMIT の冪等パターン、失敗時には ROLLBACK を試行。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定・探索ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日を休業日）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を更新（バックフィル、健全性チェックあり）。
    - DB 優先 + 未登録日は曜日フォールバックの一貫した挙動を実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を構造化。
    - 差分更新、backfill、品質チェックの設計方針を実装。DuckDB 接続を前提とした最大日付取得ユーティリティなどを提供。
    - デフォルトのバックフィル日数やカレンダー先読み設定などを定義し、運用上の保護（例: 最小データ開始日）を組み込み。

- リサーチ / ファクター（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（データ不足時は None を返す）。
    - calc_volatility: 20日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 等は None）。
    - DuckDB SQL とウィンドウ関数を活用した計算を実装。外部 API や実取引にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを LEAD を使って一括計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
    - rank / factor_summary: ランク化処理（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を算出するユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結。

### Changed
- （初版のため該当なし）内部設計や API の安定化は今後のリリースで調整予定。

### Fixed
- （初版のため該当なし）

### Security
- AI 機能（score_news / score_regime）は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を必須とします。未設定時は ValueError を発生させます。
- 環境値の必須チェック（_require）により、重要なトークン未設定での誤動作を防止。

### Notes / Implementation details / 運用上の注意
- ルックアヘッドバイアス対策: AI スコアリング・レジーム判定・ファクター計算いずれも内部で datetime.today() / date.today() を直接参照せず、target_date を受け取る設計になっています。
- DuckDB を永続データ層として想定。各処理は prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等のテーブル構造を前提としています。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスの厳密なパース/バリデーションを行っています。API レスポンスや接続エラーに対してはフェイルセーフやリトライ戦略を備えています。
- テストしやすさ: OpenAI 呼び出し点にモック差し替え可能な内部関数を用意しており、単体テストで外部依存を切り離せます。
- DB 書き込みは冪等性（DELETE→INSERT、ON CONFLICT 相当）を意識した実装になっています。部分失敗時の既存データ保護に配慮しています。

---

今後のリリースでは以下を想定しています（例）:
- API エラー時の監視・アラート連携（Slack など）やメトリクス計測の追加
- ai モジュールのモデル切替やプロンプト改善、テストカバレッジの強化
- ETL の並列化・差分戦略の最適化、品質チェックルールの追加

もし特に強調して欲しい変更点や、リリースノートに含めたい追加情報があれば教えてください。