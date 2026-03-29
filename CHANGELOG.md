# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
このファイルはコードベースの内容を解析して推測した変更履歴（初期リリース向けのまとめ）です。

※ 注: 以下は提供されたソースコードの内容から推測して作成しています。

## [Unreleased]

### Added
- プロジェクト初期実装を追加（バージョン 0.1.0 相当）。
- パッケージ初期化:
  - パッケージ名: kabusys、__version__ = "0.1.0" を定義。
  - パブリックサブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（kabusys.config）:
  - .env ファイルと環境変数から設定を自動読み込み（プロジェクトルート探索は .git または pyproject.toml ベース）。
  - .env/.env.local 読み込みの優先度制御、OS 環境変数の保護（protected set）に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 強力な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ処理をサポート）。
  - Settings クラスでアプリ設定を公開（J-Quants, kabu API, Slack, DB パス, 環境モード, ログレベルなど）。
  - 必須環境変数未設定時は ValueError を送出する _require 関数。

- AI モジュール（kabusys.ai）:
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON モード）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチサイズ、1銘柄あたりの記事/文字数上限、レスポンス検証、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx 共通）とエクスポネンシャルバックオフ実装。
    - DuckDB の executemany の互換性（空リストチェック）に対応した DB 書込み（DELETE → INSERT の冪等処理）。
    - テスト用に OpenAI 呼び出しの差し替えを想定した設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して daily レジーム判定（'bull'/'neutral'/'bear'）。
    - マクロキーワードフィルタ、OpenAI（gpt-4o-mini）呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジームスコアの閾値、スコア合成、market_regime への冪等書込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。
    - look-ahead バイアスを避ける設計（date 比較は target_date 未満等を採用）。

- データ処理（kabusys.data）:
  - calendar_management
    - JPX カレンダー管理、営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar に冪等保存。バックフィル・健全性チェック実装。
  - pipeline / etl
    - ETLResult データクラスを提供（ETL 実行結果の集約、品質チェック結果やエラーを保持）。
    - ETL パイプライン設計（差分取得、idempotent 保存、品質チェック、バックフィル等）のインターフェースを実装。
    - DuckDB 周りのユーティリティ（テーブル存在チェック、最大日付取得など）。

- 研究用モジュール（kabusys.research）:
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比） を DuckDB ベースで算出する関数（calc_momentum, calc_value, calc_volatility）。
    - データ不足時の挙動（必要データが足りない場合は None を返す）。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ランク機能（rank）、ファクター統計サマリ（factor_summary）。
    - pandas 等に依存しない純粋 Python 実装。ties の扱いに配慮したランク計算。
  - zscore_normalize を data.stats から再エクスポート。

### Changed
- （初期実装のため特記すべき変更履歴なし）

### Fixed
- （初期実装のため特記すべき修正履歴なし）
- 設計上のフェイルセーフを明確化:
  - AI API 呼び出し失敗時に例外を上位に上げずスコアを 0.0 にフォールバックする箇所を実装（news_nlp, regime_detector）。
  - DuckDB の executemany に空リストを渡さないガードを実装して互換性を保護。

### Security
- API キーや機密値は環境変数経由で取得する設計。必須値が未設定の場合は明示的にエラーを出すことで誤設定を早期に検出。

## [0.1.0] - 2026-03-29

このプロジェクトの初期公開相当のリリース（コードベースのスナップショットに基づく想定リリース）。上記「Added」の内容を含む。

- 主要機能:
  - 環境設定管理、AI ベースのニュースセンチメントおよび市場レジーム判定、ETL パイプライン基盤、JPX カレンダー管理、ファクター計算・特徴量探索などを含む一連のモジュールを提供。
  - DuckDB をデータ層として前提とした設計と、OpenAI（gpt-4o-mini）との統合を備える。

備考:
- OpenAI 連携部分は外部 API 呼び出しを行うため、実行時には OPENAI_API_KEY（または api_key 引数）を設定してください。
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等（Settings クラス参照）。

---

もし実際の変更履歴（コミットログやリリースノート）があれば、それに合わせて日付・項目の修正やセクションの細分化を行います。必要であれば英語版や要約版（短縮版）も作成します。