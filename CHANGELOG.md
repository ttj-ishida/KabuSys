# Changelog

すべての注目すべき変更点を Keep a Changelog の形式で記録します。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。プロジェクトのコア機能（データ ETL、マーケットカレンダー管理、リサーチ用ファクター計算、AI ベースのニュース/レジーム評価、設定管理等）を実装。

### Added
- パッケージ全体
  - 初期パッケージ kabusys を追加。公開モジュール群: data, research, ai, config, などの基盤を実装。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定
  - 自動 .env ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサー実装（コメント行、export KEY= 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、上書き制御）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを追加し、主要な設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等のファイルパス（デフォルト値あり）
    - CPU/MEMORY/DISK のしきい値、環境モード（development/paper_trading/live）とログレベルの検証
    - is_live / is_paper / is_dev の便宜プロパティ

- データプラットフォーム（data）
  - ETL 用のインターフェース ETLResult を実装・エクスポート（kabusys.data.etl）。
  - ETL パイプライン基盤（kabusys.data.pipeline）:
    - 差分取得・バックフィル用定数、品質チェックの集約、idempotent 保存方針（ON CONFLICT 相当の扱いを想定）。
    - DuckDB を使ったテーブル存在チェック等のユーティリティ実装。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを実装。
    - calendar_update_job: J-Quants からカレンダーを差分取得して market_calendar テーブルへ冪等的に保存するジョブ実装。
    - DB 未取得時の曜日ベースフォールバック、バックフィル・健全性チェックの実装。

- リサーチ（research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1/3/6 ヶ月相当のリターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損時は None）。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（範囲チェック、最大ホライズンに応じたスキャンバッファ）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（結合・None除外・有効レコード数チェック）。
    - rank: 同順位は平均ランクで処理、丸め誤差対策あり。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。

- AI / NLP（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）:
    - 記事ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）: calc_news_window。
    - raw_news と news_symbols を集約し、銘柄ごとに最新記事（最大件数／文字数でトリム）をまとめて OpenAI にバッチ送信。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、レスポンスのバリデーション・数値化・±1.0 クリップ。
    - バッチ処理（最大 20 銘柄／チャンク）と指数バックオフリトライ（429・ネットワーク切断・タイムアウト・5xx）を実装。
    - レスポンスパースの堅牢化（余計な前後テキストが混ざる場合に最外の {} を抽出）、整数コードや数値で返されるケースへの対応。
    - 書き込みは部分失敗に備え、取得済みコードのみを DELETE → INSERT で置換（部分冪等処理）。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（Nikkei 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタ、LLM スコアの取得（gpt-4o-mini）、リトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - AI モジュール共通
    - OpenAI 呼び出し関数はテスト容易性のためラップ実装（テストで差し替え可能）。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決（未設定時は ValueError）。

### Changed
- （初回リリースのため「変更」は該当なし。設計方針や既定の挙動はドキュメント化済み。）

### Fixed / Robustness
- DuckDB 周りの互換性対策:
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 の制約回避）。
  - DuckDB から返る日付値の安全な変換ユーティリティ _to_date を実装。
- API レスポンス・パースの堅牢化:
  - JSON パース失敗時にログを出してフォールバック（0.0 やスキップ）することで処理継続を保証。
  - news_nlp で LLM が整数でコードを返すケースに対する正規化処理を追加。
- lookahead バイアス対策:
  - AI モジュール・ETL・その他の処理で datetime.today()/date.today() を直接参照しない実装指針に従い、ターゲット日を明示的に引数で受け取るよう実装済み。
- レスポンス検証
  - news_nlp のレスポンス検証強化（results の存在確認、要素型チェック、スコアの数値性・有限値検査）。

### Security & Requirements
- API キー必須の機能:
  - OpenAI を利用する機能は OPENAI_API_KEY（または関数引数）必須。未設定時は ValueError を送出。
  - J-Quants, kabu-station など外部 API 用の認証情報を環境変数で参照（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- .env の自動読み込みはデフォルトで有効だが、テスト等のために KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を提供。
- .env ロード時に既存 OS 環境変数を保護する protected キーセット実装（上書き制御）。

### Known limitations / Notes
- 実行時に想定される DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が存在することを前提としている。
- AI 呼び出しは gpt-4o-mini（JSON mode）を想定しており、OpenAI SDK のバージョン差異により挙動が変わる可能性がある（status_code 取り扱い等への配慮は実装済み）。
- 一部機能は jquants_client に依存（外部 API クライアントは別モジュールとして想定・参照）。

---

今後のリリースでは、テストカバレッジ・監視/実行モジュールの実装、外部クライアントの抽象化、より詳細な品質チェックレポート出力、ドキュメント（Usage / Deployment / Schema）を追加する予定です。