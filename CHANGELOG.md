# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-28

### Added
- 初回リリース: KabuSys 日本株自動売買システムのコアライブラリを追加。
- パッケージエントリポイント
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - モジュール公開: data, strategy, execution, monitoring。

- 環境設定・自動 .env ロード（kabusys.config）
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env/.env.local ファイルの自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - 環境変数自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト向け）。
  - .env パーサの強化:
    - export プレフィックス対応（`export KEY=val`）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無しでのインラインコメント認識（直前が空白／タブの場合のみ `#` をコメント扱い）。
  - .env 読み込み時の上書き制御（override）と「保護された」OS 環境変数セット保護を実装。
  - `Settings` クラスを提供し、以下の設定プロパティを環境変数から取得:
    - J-Quants: `jquants_refresh_token` (JQUANTS_REFRESH_TOKEN)
    - kabuステーション: `kabu_api_password` (KABU_API_PASSWORD), `kabu_api_base_url` (デフォルト: http://localhost:18080/kabusapi)
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト data/kabusys.duckdb）, `sqlite_path`（デフォルト data/monitoring.db）
    - システムフラグ: `env`（development/paper_trading/live の検証）、`log_level`（DEBUG/INFO/... の検証）、便宜の `is_live`/`is_paper`/`is_dev` プロパティ
  - 必須環境変数未設定時は明確なエラー（ValueError）を発生させる `_require` を実装。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント: `score_news(conn, target_date, api_key=None)` を実装
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で DB と照合）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1銘柄あたり最大記事数・文字数でトリム）。
    - バッチ処理: 1 API コールで最大 20 銘柄（_BATCH_SIZE）。
    - OpenAI (gpt-4o-mini) の JSON Mode を使ったプロンプト設計とレスポンス検証。
    - API の一時エラー（429/タイムアウト/接続断/5xx）に対して指数バックオフでリトライ。
    - レスポンスの厳格なバリデーション（JSON抽出／results フィールド／コード整合性／数値チェック）。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため `_call_openai_api` をパッチ可能に実装。
    - API キーは引数優先、未指定時は環境変数 `OPENAI_API_KEY` を参照。未設定時は ValueError を送出。
  - 市場レジーム判定: `score_regime(conn, target_date, api_key=None)` を実装
    - ETF 1321（日経225連動）の直近200日終値から MA200 乖離率を計算（lookahead を防止する date < target_date 条件）。
    - マクロキーワードでフィルタしたニュースタイトルを LLM に渡して macro_sentiment を算出（記事がない、または API 失敗時は 0.0 をフォールバック）。
    - レジームスコア = 0.7 * (ma200_dev * scale) + 0.3 * macro_sentiment を clip(-1,1)。
    - 閾値により regime_label を 'bull'/'neutral'/'bear' に分類。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - こちらも API 呼び出しはパッチ可能（テスト容易性）。

- データモジュール（kabusys.data）
  - カレンダー管理（calendar_management）:
    - 営業日判定: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar テーブルが無い場合は曜日ベース（土日除外）でフォールバック。
    - DB 登録値がある場合は DB 値を優先し、未登録日は一貫した曜日フォールバックを利用する設計。
    - 次/前営業日探索は _MAX_SEARCH_DAYS（60 日）以内で打ち切り、見つからない場合は ValueError。
    - 夜間バッチ更新ジョブ calendar_update_job を実装。J-Quants API から差分取得し保存（バックフィルと健全性チェックあり）。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集計・ヘルパーメソッド）。
    - 差分取得/バックフィル/品質チェックを想定した設計（jquants_client と quality モジュールを連携）。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得などを実装。

- Research（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターンと ma200_dev（200日MA乖離）を計算、データ不足時は None。
    - calc_volatility: 20日 ATR（avg true range）および相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務を取得して PER（EPS 有効時）と ROE を計算。
    - DuckDB SQL を主体とした高速集計と lookahead 防止。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン取得（LEAD を利用）。
    - calc_ic: スピアマン（ランク相関）による IC 計算（3 件未満で None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量集計を実装。
  - zscore_normalize を data.stats から再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報（API トークン等）は環境変数経由で扱うことを前提とし、コード内に埋め込まない設計を明示。
- .env 自動ロードはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止: AI モジュール・リサーチ関数はいずれも内部で datetime.today()/date.today() を参照せず、必ず外部から与えられる target_date を基準にデータ抽出（SQL にも date < / date = などの注意を払う）。
- フェイルセーフ: OpenAI API の失敗やレスポンス不整合は局所でフォールバック（例: macro_sentiment=0.0、該当銘柄スキップ）して処理継続する設計。
- DuckDB への書き込みは可能な限り冪等（DELETE→INSERT）かつトランザクションで保護。ROLLBACK を試行し、失敗時はログ出力して例外を伝播。
- テスト容易性: OpenAI 呼び出し部分は内部関数をパッチ可能（unittest.mock.patch）に実装しているためユニットテストが容易。

---

今後のリリースで予定している改善（例）
- strategy / execution / monitoring の実装拡充（現在はパッケージ名だけ公開）。
- より詳細な品質チェックルール（quality モジュール）と自動アラート統合。
- OpenAI モデル選択やプロンプトの改善、レスポンス解析ロバスト化の継続。