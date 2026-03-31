# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

- リリースノートはセマンティックバージョニングに従います。  
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。本リポジトリが提供する主要機能と設計方針を実装した安定版。

### Added
- パッケージ基盤
  - `kabusys` パッケージの初期公開インターフェース（`__version__ = "0.1.0"`）。
  - `__all__` によるモジュール公開: `data`, `strategy`, `execution`, `monitoring`。

- 設定 / 環境変数管理
  - `.env` / `.env.local` の自動ロード機能を実装（プロジェクトルート自動検出、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - `.env` パーサーの実装: コメント行、export プレフィックス、シングル/ダブルクォート、エスケープを考慮したパース。
  - `Settings` クラスによる型付きアクセサ（J-Quants トークン、kabu API 設定、Slack トークン/チャネル、DB パス等）。
  - 環境値の検証（`KABUSYS_ENV`／`LOG_LEVEL` の許容値チェック、必須変数未設定時に明確なエラー）。

- データプラットフォーム（duckdb ベース）
  - ETL パイプラインの骨組み（`kabusys.data.pipeline.ETLResult` を公開）。
  - DuckDB 用ユーティリティ（テーブル存在チェック、最大日付取得等）。
  - 市場カレンダー管理モジュール（`data.calendar_management`）
    - 営業日判定 API: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - JPX カレンダー差分取得と夜間更新ジョブ: `calendar_update_job`（バックフィル、健全性チェック、J-Quants クライアント経由の保存）。
    - DB 未取得時の曜日ベースフォールバックロジック。

- 研究（Research）モジュール
  - ファクター計算（`research.factor_research`）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、相対ATR、平均売買代金、出来高比率。
    - Value: PER（EPS 利用）、ROE（raw_financials から取得）。
    - DuckDB SQL を活用した効率的な一括計算（営業日窓、ラグ/移動平均等）。
  - 特徴量探索（`research.feature_exploration`）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（Spearman の ρ に相当、ランク処理による ties の平均ランク対応）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - ランク変換ユーティリティ（同順位は平均ランク、丸めによる ties 安定化）。

- AI / NLP 機能（OpenAI 経由）
  - ニュースセンチメント集約（`kabusys.ai.news_nlp.score_news`）
    - ニュース収集ウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - raw_news と news_symbols を用いた銘柄別記事集約（記事数・文字数上限によるトリム）。
    - gpt-4o-mini を用いたバッチ評価（最大 20 銘柄／チャンク）、JSON Mode レスポンスのバリデーションとスコアの ±1.0 クリッピング。
    - リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフォールバック（失敗時はスキップ）。
    - DuckDB との冪等書き込み（該当コードのみ DELETE → INSERT）。DuckDB の executemany の仕様差異への対応。
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出（キーワードベース、最大 20 件）と LLM による -1.0〜1.0 のマクロセンチメント評価。
    - OpenAI 呼び出し独立実装、API リトライ・5xx 処理、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（.env の上書きを制御）。
- 必須トークン・シークレットは `Settings` 経由で取得し、未設定時は明確にエラー（例外）を送出。

### Notes / Design decisions
- ルックアヘッドバイアス回避
  - AI／ETL／研究モジュールは内部で `datetime.today()` や `date.today()` を参照せず、明示的な `target_date` を必須とすることで将来情報の漏洩を防止。
  - DB クエリは target_date 未満や半開区間など、データ選択においてルックアヘッドを避ける条件を明示。
- 冪等性
  - DB 書き込みは可能な限り冪等に設計（DELETE → INSERT、ON CONFLICT など）。
- フォールバックと耐障害性
  - OpenAI API 呼び出しはリトライとフォールバック（スコア 0.0 や該当銘柄スキップ）を実装し、パイプライン全体を壊さない設計。
  - カレンダー未取得時は曜日ベースのフォールバックを採用。
- DuckDB の互換性対策
  - `executemany` の空リストバインド不可などの挙動に対する防御コードを追加。

もし変更履歴に追記したい詳細や、特定のコミット／機能の粒度で分けたい場合は、対象部分（例: news_nlp の retry ロジック、calendar_update_job のバックフィル等）を指定してください。さらに細かく分割したリリースノートを作成します。