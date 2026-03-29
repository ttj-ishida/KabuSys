# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
このプロジェクトの初期リリースを記録しています。

全般
- 日付はリリース日を示します。
- バージョンはパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29

### Added
- 初回公開: 基本パッケージ構成を追加
  - パッケージエクスポートに以下を追加: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
- 環境・設定管理（src/kabusys/config.py）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする仕組みを実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース機能を強化（export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - OS 環境変数を保護する protected 上書き制御（.env.local は override=True として既存値を上書き可能だが OS 環境変数は保護）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境モード（development/paper_trading/live）/LOG_LEVEL の取得とバリデーションを行うプロパティを実装。
- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news, news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出する score_news を実装。
  - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST → UTC 変換）と記事トリム（記事数・文字数上限）の実装。
  - チャンク処理（最大20銘柄/回）、リトライ（429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ）、レスポンス検証、スコアクリッピング、部分失敗時に既存スコアを保護する DB 書き換えロジック（DELETE → INSERT の限定置換）を実装。
  - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次でレジーム（bull/neutral/bear）を判定する score_regime を実装。
  - prices_daily / raw_news からのデータ集約、OpenAI 呼び出し（リトライ・フォールバック）、レジーム合成スコアのクリッピング、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
- 研究用ファクター計算（src/kabusys/research/）
  - factor_research: calc_momentum（1M/3M/6M リターン、200日MA乖離）、calc_volatility（20日ATR、相対ATR、平均売買代金、出来高比率）、calc_value（PER, ROE）を実装。prices_daily / raw_financials のみ参照。
  - feature_exploration: calc_forward_returns（複数ホライズン対応、リード句で将来終値取得）、calc_ic（スピアマンランク相関）、factor_summary（基本統計）、rank（同順位平均ランク）を実装。標準ライブラリのみで実装。
  - 研究ユーティリティ（src/kabusys/research/__init__.py）で主要関数を公開。
- データ基盤（src/kabusys/data/）
  - calendar_management: market_calendar を用いた営業日判定（is_trading_day、is_sq_day、next_trading_day、prev_trading_day、get_trading_days）および J-Quants からの差分取得と保存を行う calendar_update_job を実装。DB 未取得時の曜日ベースフォールバック、検索上限、バックフィルロジック、健全性チェック（過度に将来の日付を検出した場合スキップ）を実装。
  - pipeline / etl: ETLResult データクラス（ETL 実行結果の構造化）とパイプラインユーティリティ（取得日判定、テーブル存在チェック、最大日付取得等）を実装。差分取得、バックフィル、品質チェックフレームワークとの連携設計をコメントで明確化。
  - etl モジュールは ETLResult を公開（src/kabusys/data/etl.py）。
- DuckDB を主要な永続化層として利用する設計に対応（各モジュールは DuckDB 接続を受け取り SQL / executemany を利用）。
- OpenAI / J-Quants / Slack 等の外部サービスとの連携点を環境変数で設定できることを明記（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

### Changed
- （初回リリースのため履歴上の変更はなし。設計上の注記）
  - すべての AI/データ処理で datetime.today()/date.today() の直接参照を避け、target_date 引数ベースでの判定・計算を採用（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しの振る舞い（リトライ対象・非リトライ対象・フォールバック）を統一化。
  - DuckDB のバージョン互換性に配慮した実装（executemany の空リスト禁止への対応、list 型バインド回避のための個別 DELETE 実行など）。

### Fixed
- フェイルセーフ/堅牢性の改善（初期実装段階での安全処理）
  - OpenAI API の失敗（ネットワーク/タイムアウト/レート制限/5xx）やレスポンスパース失敗時に例外を上位に伝播させず、適切にログ出力して安全側の既定値（例: macro_sentiment=0.0）で継続するように実装。
  - DuckDB に対する複数レコード置換の際、部分失敗で他銘柄の既存データを消さない設計（対象コードのみ DELETE → INSERT）。
  - market_calendar の不整合（NULL 値や未登録日）に対するログ出力と曜日ベースのフォールバック処理を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注意事項 / 必要設定
- OpenAI API キーは OPENAI_API_KEY 環境変数または各関数の api_key 引数で指定する必要があります（news_nlp.score_news / regime_detector.score_regime は未指定時に環境変数を参照し、未設定の場合は ValueError を送出します）。
- .env の自動ロードはプロジェクトルートの検出に依存します。配布後やテスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

既知の設計方針（重要）
- ルックアヘッドバイアス防止のため、日次処理はすべて target_date を明示的に受け取り、DB クエリにも target_date 未満 / 排他的条件を用いる等の実装上の配慮があります。
- API 呼び出し失敗時は基本的に継続（フェイルセーフ）する方針で、システムの可用性とデータ保護を優先しています。

（以降のリリースでは各モジュールの機能追加・最適化・バグ修正をここに記載します）
