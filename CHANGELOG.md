# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
各リリースはセクションに分けて、Added / Changed / Fixed / Security 等で整理しています。

※記載内容はソースコードから推測して作成しています。

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。  
主な追加機能、設計判断、既知の動作を以下にまとめます。

### Added
- パッケージ基礎
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"` を公開。
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ で公開。

- 設定管理
  - 環境変数・設定読み込みモジュール `kabusys.config` を追加。
    - .env ファイル自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を探索して決定）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
    - .env パーサはシェル形式の `export KEY=val`、シングル/ダブルクォート、インラインコメントの扱い等に対応。
    - 必須変数未設定時に ValueError を送出する `_require` と Settings クラスを提供。
    - デフォルト設定値（例: `KABU_API_BASE_URL`, `DUCKDB_PATH`, `SQLITE_PATH`, 監視閾値等）を明示。

- データプラットフォーム（Data）
  - `kabusys.data.pipeline`:
    - ETLResult データクラスで ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を表現。
    - 差分更新/バックフィル/品質チェックを想定した設計（J-Quants クライアントと連携）。
  - `kabusys.data.etl`:
    - pipeline.ETLResult を再エクスポート。
  - `kabusys.data.calendar_management`:
    - JPX マーケットカレンダー管理（market_calendar の読み書き、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - DB による優先判定と曜日ベースのフォールバック、最大探索日数制限、バックフィルロジック。
    - `calendar_update_job` による J-Quants からの差分取得と冪等保存の実装（fetch/save は jquants_client を利用）。

- 研究（Research）ユーティリティ
  - `kabusys.research` パッケージを追加。ファクター計算・特徴量探索用の関数群を公開:
    - `calc_momentum`, `calc_value`, `calc_volatility`（kabusys.research.factor_research）。
      - Momentum: 1M/3M/6M リターン、200日MA乖離など。
      - Volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等。
      - Value: PER、ROE（raw_financials / prices_daily を参照）。
    - `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`（kabusys.research.feature_exploration）。
      - 将来リターン（任意ホライズン）、Spearman（ランク）IC、統計サマリー、ランク関数。
    - Z スコア正規化ユーティリティは `kabusys.data.stats` から再利用。

- AI モジュール
  - `kabusys.ai.news_nlp`:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算、記事トリム（最大記事数・最大文字数）やバッチ処理（最大 20 銘柄/回）実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。応答検証（JSON パース・構造検査）とスコアクリッピングを実施。
    - 部分成功時は成功分のみ ai_scores テーブルを置換する（DELETE → INSERT、DuckDB executemany 空リスト回避対応）。
  - `kabusys.ai.regime_detector`:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、OpenAI を用いたマクロセンチメント評価（gpt-4o-mini、JSON 出力）を実行。API エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、例外時は ROLLBACK を行う。

- 設計・実装方針（全体）
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照しない設計（target_date 引数を明示的に受け取る）。
  - DuckDB を主要なローカルデータストアとして想定し、SQL + Python による処理を行う（外部 heavy ライブラリに依存しない）。
  - OpenAI 呼び出しは再利用しやすく、テスト時にモックで差し替えやすいように実装（内部 _call_openai_api を patch 可能）。
  - DB 書き込みは冪等性を考慮（DELETE → INSERT、ON CONFLICT を想定）し、部分失敗時のデータ保護を重視。

### Changed
- （初回リリースのため該当なし）

### Fixed
- DuckDB の executemany が空リストを許容しない点を考慮した実装上の配慮（空リスト時は呼び出しをスキップ）を組み込んでいるため、部分失敗時に他データを誤って削除しないように保護。

### Security
- OpenAI / J-Quants / kabu ステーション等のシークレットは環境変数で注入する設計。
  - 例: `OPENAI_API_KEY`, `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`。
- .env 自動読み込み時、OS 環境変数を保護するため `.env.local` の上書きや .env の上書き挙動に保護ロジックを導入。
- デフォルトで API キー未設定時は明示的に ValueError を送出して安全に停止する箇所がある（AI モジュール等）。

### Known issues / Limitations
- News / Regime を評価する AI 部分は外部 API（OpenAI）に依存するため、API の利用制限や応答形式変更に影響を受ける可能性がある。レスポンスパース失敗時はフェイルセーフとして中立スコア（0.0）にフォールバックする設計。
- raw_financials に依存する PER/ROE 計算では、EPS=0 や欠損時に None を返す（呼び出し側でのハンドリングが必要）。
- calendar_update_job は J-Quants クライアント実装（jquants_client.fetch_market_calendar / save_market_calendar）に依存。API 例外時は 0 を返して処理を継続する。

---

今後のリリースでは以下を予定（例示）
- strategy / execution / monitoring パッケージの実行ロジック（発注呼び出し、監視/再起動機構など）の追加と E2E テストカバレッジ拡充。
- ai モジュールの評価精度向上、事前学習済みルールの導入、バージョンに応じたモデル切替 API の柔軟化。
- DuckDB スキーマ定義・マイグレーションユーティリティの提供。

もし特定の変更点をより詳細に反映したい場合（例: リリース日や追加の修正履歴など）、該当するコミットや変更箇所の情報を提供してください。