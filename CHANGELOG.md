# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
このファイルにはパッケージの主要な機能追加・仕様・重要な注意点を日本語でまとめています。

なお本リリースはパッケージバージョン __0.1.0__ に対応します。

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。主要サブパッケージ・機能を追加。
  - kabusys パッケージの公開エントリ: data, strategy, execution, monitoring（__init__.py でエクスポート）。
- 設定/環境変数管理
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索することで CWD に依存しないロードを実現。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を保護して .env.local で上書き可能）。
    - 複数形式の .env 行パース対応（export プレフィックス、クオート内のバックスラッシュエスケープ、行内コメント等）。
    - 環境変数の必須取得ヘルパー _require と Settings クラスを提供。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- AI（OpenAI）を利用したニュース・レジーム判定
  - kabusys.ai.news_nlp:
    - raw_news, news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）で評価し ai_scores テーブルに書き込む score_news を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数上限、JSON Mode を利用。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とレスポンス検証を実装。
    - テスト容易性のため _call_openai_api をモック可能（unittest.mock.patch）。
    - DuckDB の executemany 空リスト制約に対応した安全な DELETE/INSERT 実装。
  - kabusys.ai.regime_detector:
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - レジーム合成ロジック、OpenAI 呼び出し、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
- データ処理・研究機能
  - kabusys.data.pipeline / ETLResult:
    - ETL パイプライン用結果データクラス ETLResult を公開（取得/保存件数、品質問題・エラー情報を格納）。
  - kabusys.data.calendar_management:
    - 市場カレンダー管理（market_calendar）と営業日判定ユーティリティ。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった関数を実装。
    - calendar_update_job: J-Quants からカレンダーデータを差分取得し保存する夜間バッチ用関数を実装（バックフィル・健全性チェック付き）。
  - kabusys.research:
    - factor_research モジュール:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等のモメンタムファクターを計算。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比等を計算。
      - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（target_date 以前の最新財務レコードを使用）。
    - feature_exploration モジュール:
      - calc_forward_returns: 任意ホライズンの将来リターンを取得（デフォルト [1,5,21]）。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
      - rank: 同順位は平均ランクとするランキングユーティリティ。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - 各研究関数は DuckDB 接続を受け取り、prices_daily/raw_financials 等のテーブルのみ参照する純粋分析ロジックとして実装。
- 設計上の注意点・テストフック
  - ルックアヘッドバイアス防止のため、各スコア関数は date.today()/datetime.today() を直接参照しない（target_date を引数で指定する）。
  - OpenAI 呼び出し部分はモジュール内で _call_openai_api として分離してあり、テスト時に差し替え可能。
  - API 応答のパース失敗や API 停止時は例外を飛ばさずフェイルセーフ値（例: 0.0）で継続する設計が多く採用されている。
  - DuckDB のバージョン差異（executemany に空リストを渡せない等）に対応する実装上の配慮あり。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数の取り扱いに注意:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY などの機密情報は環境変数で供給することを想定。 .env ファイル利用時の保護には注意すること。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テストや CI 用）。

### Notes / 互換性と運用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須扱い（未設定時は ValueError を送出）。
  - OPENAI_API_KEY は news_nlp.score_news / regime_detector.score_regime を呼ぶ際に必須。api_key 引数で明示的に渡すことも可能。
- デフォルト DB パス:
  - DUCKDB_PATH は data/kabusys.duckdb、SQLITE_PATH は data/monitoring.db をデフォルトとする（expanduser を実行）。
- DuckDB テーブル前提:
  - 各モジュールは prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など特定のテーブルが適切に定義・存在することを前提としている。初期データロードやスキーマ準備を行ってから利用すること。
- 時間ウィンドウ・タイムゾーン:
  - news_nlp.calc_news_window / score_news は JST ベースのウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を内部で UTC naive datetime に変換して DB の UTC datetime と比較する。
- 冪等性:
  - ai_scores, market_regime などへの書き込みは既存行を DELETE して INSERT する形で部分失敗時の既存データ保護に配慮している（部分的な更新を行う）。
- OpenAI 関連:
  - モデル: gpt-4o-mini を使用する前提。JSON Mode を利用して厳格な JSON レスポンスを期待するが、パース回復処理（外側の余計なテキストから {} を抽出する等）も実装している。
  - リトライ: レート制限・ネットワーク・タイムアウト・5xx に対する指数バックオフ実装。ただし無限リトライは行わない。
- テスト容易性:
  - OpenAI 呼び出し関数はモック差し替えを想定しており、ユニットテストで実APIを叩かずに検証可能。
- DuckDB 互換性:
  - DuckDB 0.10 系の挙動（executemany に空リスト不可）に関するワークアラウンドを実装しているため、古い/将来の DuckDB でも比較的安全に動作するよう配慮しているが、運用時は使用バージョンでの動作確認を推奨。

## Deprecated
- 初回リリースのため該当なし。

## Removed
- 初回リリースのため該当なし。

## セットアップ / 早見ガイド
- 開発・運用前に最低限以下を設定してください。
  - 環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用する機能を使う場合: OPENAI_API_KEY
  - DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）を準備
  - 自動 .env ロードを望まない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- AI スコアリング関連は外部 API に依存するため、API 使用量やレート制限に注意して運用してください。

---

今後のリリースでは、strategy / execution / monitoring の実装拡充、より詳細な品質チェック・監視機能、Inline ドキュメントや CLI ツールの追加を予定しています。要望やバグ報告があれば issue を作成してください。