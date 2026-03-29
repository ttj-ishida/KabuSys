# CHANGELOG

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリース日付は ISO 形式 (YYYY-MM-DD) を使用します。
- 代表的なカテゴリ: Added, Changed, Fixed, Removed, Security, Notes

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。

### Added
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - 主要サブパッケージをエクスポート: data, research, ai, 等。

- 設定・環境変数管理（kabusys.config）
  - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準に探索して `.env` / `.env.local` を読み込む仕組みを実装。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく解釈。
    - コメントの取り扱いを改善（クォート有無での扱いの差別化）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト向け）。
  - OS 環境変数を保護する `protected` ロジック：`.env.local` 等による既存 OS 環境変数の上書きを防止。
  - 必須値取得ヘルパー `_require` と、Settings クラスを提供。Settings は下記プロパティを持つ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - ニュースのタイムウィンドウ計算 `calc_news_window(target_date)` を実装（JST基準 → DB比較用に UTC naive datetime を返す）。
  - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI にバッチ問い合わせし、センチメントスコアを ai_scores テーブルへ書き込む `score_news(conn, target_date, api_key=None)` を実装。
  - チャンク処理（最大 20 銘柄/チャンク）、各銘柄内のテキスト長制限（_MAX_CHARS_PER_STOCK）や記事数制限（_MAX_ARTICLES_PER_STOCK）を導入してトークン肥大化に対処。
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスの堅牢なバリデーションとパースを実装（前後に余分なテキストが混じる場合の復元ロジック含む）。
  - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ実装。リトライ限界超過や解析失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
  - DuckDB の互換性を考慮した書き込み戦略（部分成功を保つために対象コードのみ DELETE → INSERT を実行、executemany の空リスト回避）。

- AI / 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日本225連動型）の 200 日移動平均乖離（_calc_ma200_ratio）とマクロニュースの LLM センチメントを組合せて日次の市場レジーム（bull/neutral/bear）を算出する `score_regime(conn, target_date, api_key=None)` を実装。
  - マクロニュース抽出はキーワードベース（日本・米国等の金融/マクロワードを列挙）で `raw_news` からタイトルを取得。
  - OpenAI 呼び出し（gpt-4o-mini）に対してリトライ、エラー時は macro_sentiment=0.0 へフォールバックするフェイルセーフ設計。
  - 計算結果は冪等に market_regime テーブルへ書き込む（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して上位へ例外を伝播。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m/3m/6m、ma200_dev を算出（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を算出（データ不足時は None）。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPSが0/欠損時は None）。
    - 全関数は DuckDB の prices_daily / raw_financials を参照し、外部 API にアクセスしない安全設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank, factor_summary: ランク付け（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージは主要関数を __all__ で再エクスポート。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）:
    - JPX カレンダーの管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。market_calendar が存在しない場合は曜日（平日/土日）ベースのフォールバックを行う。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に保存。バックフィルや健全性チェック（将来日付の異常検知）を実装。
    - 最大探索日数やバックフィル日数等の定数で無限ループ・過大取得を防止。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult dataclass を追加して ETL 実行結果（取得数／保存数／品質問題／エラー等）を統一して返却・ログ化可能に。
    - 差分更新、バックフィル、品質チェック（quality モジュール）といった ETL の設計方針を実装。
    - jquants_client を利用した差分取得・保存処理に対応。
    - kabusys.data.etl で ETLResult を再エクスポート。

### Changed
- 設計方針・実装上の注意点を明確化（コード内ドキュメンテーションに反映）。
  - ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() を直接参照せず、target_date を受け取る設計に統一。
  - 外部依存を最小化（OpenAI SDK は利用するが、pandas 等の重い外部ライブラリに依存しない実装方針を採用）。

### Fixed
- （初版のため該当なし。実装段階での堅牢化措置を多数導入：例）OpenAI レスポンスのパース失敗時のフォールバック、DuckDB executemany の空リスト回避、NULL 値の扱いに対するログ出力など。

### Security
- 環境変数ロード時の既存 OS 環境変数保護機能を導入し、`.env` による機密情報の誤上書きを防止。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げて誤用を明示。

### Notes / Limitations
- DuckDB のバージョン互換性に配慮した実装（executemany に空リストを渡さない等）。
- OpenAI への呼び出し部はテスト容易性のため内部でラップされており、ユニットテストでは差し替え可能（unittest.mock.patch を想定）。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計。
- ai モジュールは API 呼び出し失敗時に部分的に結果を残す（部分チャンク成功は保存、失敗チャンクはスキップ）設計のため、完全成功を前提としない運用が想定される。
- raw_financials に基づく値（PER 等）は現在 PBR・配当利回り等を実装しておらず、将来拡張予定。

---

今後のリリースでは以下を想定しています:
- 追加指標（PBR・配当利回り等）やリスク管理ロジックの実装
- モデル／戦略モジュール（strategy, execution, monitoring）の実装拡充
- テストカバレッジの強化と CI/CD への統合

（この CHANGELOG はコードの内容から推測して作成しています。実際の変更履歴やリリースノートはプロジェクトのリリースポリシーに従って更新してください。）