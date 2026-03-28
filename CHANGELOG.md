# Changelog

すべての非互換な変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
リリース日付はコードベースから推測して記載しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-28
初回公開リリース。以下の主要機能と実装を含みます。

### 追加
- パッケージ基盤
  - パッケージ初期化とエクスポートを追加（src/kabusys/__init__.py）。
  - バージョン番号を `__version__ = "0.1.0"` として定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 複数形式の .env 行パーサ実装（export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理など）。
  - .env の読み込みで既存 OS 環境変数を保護する protected 機能（上書き制御）。
  - Settings クラスを提供し、必要な環境変数をプロパティで取得:
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティ（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path 等）。
    - env 列挙（development, paper_trading, live）と log_level のバリデーション。
    - is_live/is_paper/is_dev の便利プロパティ。
  - 必須環境変数未設定時は明確な ValueError を送出。

- AI（自然言語処理）関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書込む機能（score_news）。
    - ニュース収集ウィンドウ計算（calc_news_window）（JST基準の時間ウィンドウ変換を実装）。
    - バッチ処理（最大 20 銘柄/呼び出し）、記事・文字数のトリムおよびトークン肥大化対策。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - OpenAI JSON mode 応答の厳密な検証と復元処理（余分な前後テキストが混ざった場合の復元ロジック）。
    - レスポンス検証で未対応・不正値を除外し、スコアを ±1.0 にクリップ。
    - DuckDB executemany の挙動差異を考慮し、空 params の回避（互換性対策）。
    - API キー注入をサポート（api_key 引数または OPENAI_API_KEY 環境変数）。
    - テスト支援のため _call_openai_api を内部で分離し patch 可能に設計。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF（1321）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - ma200_ratio 計算でルックアヘッドバイアスを防ぐ（target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news をフィルタし、OpenAI へ送って macro_sentiment を算出（記事がない場合は LLM 呼び出しをスキップし 0.0 を使用）。
    - LLM 呼び出しにはリトライ・フェイルセーフを実装（失敗時は macro_sentiment=0.0）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - OpenAI クライアント呼び出しも news_nlp とは別実装に分離（モジュール結合の最小化）。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターンと ma200_dev（200日MA乖離）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER, ROE を計算。
    - DuckDB を用いた SQL ベース処理を採用（prices_daily / raw_financials のみ参照）。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）で将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク変換を実装（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリを実装。
    - すべて標準ライブラリのみで実装、外部依存を避ける設計。

- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日ベース（週末除外）でフォールバック。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル期間・先読み期間などのパラメータ化。
  - ETL / pipeline モジュール
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分取得・保存・品質チェックの設計に準拠したユーティリティ（jquants_client, quality を使用する設計）。
    - 内部ユーティリティとしてテーブル存在チェックや最大日付取得関数を提供。
  - データモジュールの public 再エクスポート（etl から ETLResult を再公開）。

### 変更（設計上の注意・挙動）
- DuckDB 互換性考慮
  - DuckDB の executemany とリストバインドの挙動差異に対応するため、DELETE/INSERT を個別実行する実装を含む（空パラメータリストは実行しない）。
- API キーとエラー処理
  - OpenAI API キー未設定時は ValueError を送出する（明示的なエラー）。
  - LLM 呼び出し失敗時は多くの箇所でフェイルセーフ（0.0 を用いる、空スコア扱いでスキップ）とし、例外の全体伝播を抑える実装。
- ルックアヘッドバイアス対策
  - 各種日付処理（news/window, regime, factor, forward return 等）は内部で datetime.today()/date.today() を参照せず、呼び出し側が target_date を与える設計を徹底。

### 修正（実装上の堅牢化）
- .env パーサの厳密化：クォート内のエスケープ処理、インラインコメントの検出条件などを改善。
- OpenAI レスポンスのパース強化：JSON-mode でも前後の余計なテキストを復元してパースするロジックを追加。
- market_calendar が欠損／NULL の場合のフォールバックと警告ログを強化。

### 既知の問題 / 注意点
- data/__init__.py や monitoring モジュールは初期案内に参照があるが（__all__）、一部モジュール実装が必須の関数群は別ファイルでまだ未提供・未公開となっている可能性があるため、導入時はパッケージ内の全モジュールの有無を確認してください。
- OpenAI SDK の将来の仕様変更（例: APIError の属性名等）に対して一部互換性処理を入れているが、SDK 大幅変更時は追加対応が必要になる可能性があります。
- DuckDB のバージョン差異（特にリスト型バインド挙動）に依存するため、利用環境の DuckDB バージョンで動作確認を行ってください。

### セキュリティ
- API キーや機密情報は環境変数経由で管理する設計。`.env` 自動読み込みは便利だが、本番環境では KABUSYS_DISABLE_AUTO_ENV_LOAD や OS 環境変数の使用を推奨。
- .env 読み込み時に OS 環境変数を保護する仕組みを実装（上書き制御）。

---

今後のリリース案（想定）
- 0.2.0: モニタリング・実行モジュール（execution / monitoring）の実装と統合、Slack 通知機能の実装。
- 0.3.0: 発注インターフェース（kabu ステーションとの統合）と end-to-end テスト、CI ワークフロー整備。

ご要望があれば、各モジュールごとに詳細な変更点や利用例（コードサンプル）を追記します。