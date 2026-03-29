# Changelog

すべての重要な変更点をこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従います。
Semantic Versioning を採用します。

※ 日付はリリース日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアライブラリを公開します。以下の主要機能・モジュールを含みます。

### Added
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data / strategy / execution / monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルや環境変数を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env のパース処理を独自実装。以下をサポート:
    - コメント行、export キーワード、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い。
  - OS 環境変数を保護するための protected ロジックを実装（.env.local は override）。
  - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを実装し、アプリ設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値検査）および is_live/is_paper/is_dev 便宜プロパティ。

- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）を用いてセンチメントを算出。
  - バッチ処理（_BATCH_SIZE=20）で複数銘柄を一括評価。
  - JSON Mode を用いた厳格な出力検証とレスポンスパース復元ロジック。
  - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ、非致命的エラー時のスキップ（フェイルセーフ）。
  - DuckDB への書き込みは部分更新（該当コードのみ DELETE → INSERT）で冪等性を確保。DuckDB 0.10 の executemany 空リスト制約に対応するチェックを実装。
  - calc_news_window: ニュース収集ウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）を提供。
  - score_news API:
    - 引数: conn (DuckDB 接続), target_date, api_key (省略時は OPENAI_API_KEY を参照)
    - 戻り値: 書き込んだ銘柄数
    - API キー未設定時は ValueError

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - OpenAI 呼び出しは JSON mode を使用し、失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試みて例外を上位へ伝播。
  - score_regime API:
    - 引数: conn (DuckDB 接続), target_date, api_key（省略時は OPENAI_API_KEY を参照）
    - 戻り値: 成功時 1
    - API キー未設定時は ValueError

- 研究用ファクター・特徴量モジュール (kabusys.research)
  - factor_research 提供:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日MA乖離）を計算
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算
    - calc_value: per, roe を計算（raw_financials と prices_daily を参照）
  - feature_exploration 提供:
    - calc_forward_returns: 任意ホライズンの将来リターン計算（デフォルト [1,5,21]）
    - calc_ic: スピアマン（ランク）相関による IC 計算（rank 関数を使用）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理（丸め処理で ties 判定の安定化）
  - zscore_normalize は kabusys.data.stats から再エクスポート

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar に基づく営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB データが存在しない場合は曜日ベースでフォールバック（週末を休場とする）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル、健全性チェックを実装。
  - ETL / pipeline:
    - ETLResult データクラスを公開（出力・品質チェック・エラー情報を保持）
    - pipeline / etl の設計方針に基づく差分更新、保存、品質チェックの骨組みを実装
  - jquants_client の利用インタフェース（fetch / save 系）を想定した実装（実際の client 実装は別モジュール）

- 実装方針・設計上の注意点（重要）
  - ルックアヘッドバイアス防止:
    - AI・研究・ETL の各処理は datetime.today()/date.today() を内部参照せず、必ず target_date 引数を基準に処理する設計。
    - prices_daily 等のクエリにおいても target_date 未満 / 以降の排他条件を適切に設定。
  - OpenAI 呼び出し:
    - JSON Mode を利用して厳密な出力構造を期待するが、パース復元ロジックを持ち余分なテキストにも耐える。
    - API エラーに対してリトライ・バックオフを実装し、致命的失敗は避ける（フェイルセーフ）。
  - DuckDB 互換性:
    - DuckDB 0.10 の executemany が空リストを受け付けない問題を回避するチェックを導入。
  - ロギング:
    - 各処理で情報・警告・例外ログを適切に出力（デバッグ・監査に利用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは環境変数からのみ取得する設計。Settings が必須変数に対して ValueError を発生させるため、キー管理を注意すること。

### Notes / Known limitations
- OpenAI への依存:
  - AI 機能（score_news, score_regime）は OpenAI API（gpt-4o-mini）に依存します。API キー（OPENAI_API_KEY）または api_key 引数の指定が必須です。
- 自動 .env ロード:
  - プロジェクトルート検出は __file__ の親ディレクトリから .git または pyproject.toml を探す方式です。配布後のインストール状況やサーバ構成により期待通りに検出できない場合は自動ロードがスキップされます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。
- DuckDB のバージョン差異:
  - executemany の挙動やリスト型バインドの互換性に注意（空リストバインドの回避ロジックあり）。
- 部分失敗時の挙動:
  - ai_scores / market_regime などの DB 書き込みは部分置換を行うため、部分的に正常データを保護します。ただし運用ではリトライや監査ログの確認を推奨します。

### Migration / Upgrade notes
- 本バージョンは初回公開版です。将来のマイナーバージョンで API 形状（Settings のキーや関数シグネチャ）に変更が入る可能性があります。外部から呼び出す際は target_date 指定と OpenAI API キーの提供を必ず行ってください。

---

貢献・バグ報告・要望はリポジトリの issue をご利用ください。