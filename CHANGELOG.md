# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  
配列は安定したバージョン順（最近を上）で記載しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化: `kabusys.__init__` にバージョン情報を追加（0.1.0）および公開モジュール一覧を定義。
- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数の自動ロード機能を実装（優先度: OS 環境 > .env.local > .env）。
  - `.env` パーサの実装。コメント、`export KEY=val` 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - ファイル読み込み時のエラーハンドリング（警告）と、既存 OS 環境変数の保護機能（protected set）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 必須環境変数チェック用 `_require()` と、アプリケーション設定を一元提供する `Settings` クラスを実装。
  - 設定項目例:
    - J-Quants、kabuステーション、LINE API、DB パス（DuckDB / SQLite）、Paper Trading の設定（`PAPER_FILL_MODE` 等）、監視用閾値、ログレベル・環境フラグ（development/paper_trading/live）など。
  - 設定値のバリデーション（有効な enum 値チェックや数値変換、Path 展開）を追加。

- AI 関連 (`kabusys.ai`)
  - news_nlp モジュール
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングを実装。
    - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）を実装（calc_news_window）。
    - raw_news / news_symbols を元に銘柄ごとに記事集約（文字数・記事数上限トリム）。
    - バッチ送信（1 API 呼び出しあたり最大 20 銘柄）・JSON Mode 応答パース・レスポンス検証・スコアクリッピング（±1.0）。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで処理。
    - DuckDB への冪等書き込み（取得した銘柄のみ DELETE → INSERT）を実装。
    - テスト容易化のため OpenAI 呼び出しラッパーを `_call_openai_api` として分離（モック差し替え可能）。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を用いたデータ取得、OpenAI でのセンチメント評価（JSON パース）、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 を採用、リトライ戦略を実装。
    - ルックアヘッドバイアス回避の設計（内部で date.today()/datetime.today() を参照しない、DB クエリは target_date 未満の排他条件など）。
- Data（データ基盤）
  - calendar_management
    - JPX カレンダー管理（market_calendar）の判定ロジックと夜間更新ジョブ `calendar_update_job` を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを実装し、DB 登録値優先かつ未登録日の曜日ベースフォールバックに対応。
    - 更新処理は J-Quants クライアント経由で差分取得し、冪等保存を行う設計（バックフィル・健全性チェックあり）。
  - ETL / pipeline
    - ETL の高レベル仕様に沿った `ETLResult` データクラスを実装（取得数／保存数／品質検査結果／エラー等を集約）。
    - 差分取得・バックフィル・品質チェックのための定数と振る舞いを整備（J-Quants クライアント連携、品質検査は収集して呼び出し元判断）。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - DB 操作・互換性配慮
    - DuckDB を利用する前提で SQL 実装。`executemany` に空リスト渡せない DuckDB 互換性を考慮した処理を実装。
    - 日付ハンドリングで timezone 混入を避けるため date/datetime を明確に扱うユーティリティを提供。
- Research（リサーチ系）
  - factor_research
    - Momentum / Volatility / Value および流動性関連指標の計算関数を実装（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB 内 SQL とウィンドウ関数を駆使して営業日ベースのラグや移動平均、ATR 等を計算。
    - データ不足時は None を返す等の堅牢性設計。
  - feature_exploration
    - 将来リターン計算（`calc_forward_returns`）、IC（Information Coefficient）計算（`calc_ic`）、ランク変換ユーティリティ `rank`、ファクター統計サマリ `factor_summary` を実装。
    - 外部依存を避け、標準ライブラリのみで実装（pandas に依存しない設計）。
  - 研究用ユーティリティの公開（`kabusys.research.__init__` で関数群をエクスポート）。
- その他
  - モジュール間の疎結合を意識した実装（AI 関連で呼び出しラッパーを重複実装し、モジュール間でプライベート関数を共有しない設計）。
  - ロギング出力を各モジュールに配置し、情報／警告／例外時ログを明示。

### Security
- 環境変数に API キー等の機密情報を想定:
  - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` 等（`Settings` のプロパティで検査）。
  - OpenAI を使う機能 (`score_news`, `score_regime`) は `OPENAI_API_KEY` または関数引数で API キーを渡す必要あり。未設定時は ValueError を送出。
- `.env` 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。自動ロードを無効にする環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

### Notes / Implementation Details
- ルックアヘッドバイアス対策:
  - AI/研究モジュールは内部で現在日時を参照せず、必ず引数の target_date を基準に処理します。
  - DB クエリは target_date 未満や半開区間などルックアヘッドを避ける条件で設計。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）で厳密な JSON 応答を期待する。
  - レスポンスパースやスキーマ検証を行い、不正応答はスキップまたはフェイルセーフ値にフォールバック。
  - リトライ（429, ネットワーク, タイムアウト, 5xx）を指数バックオフで処理。
- DB 書き込みは可能な限り冪等性を確保（DELETE → INSERT パターンや ON CONFLICT 層での上書きを想定）。
- テスト容易性:
  - OpenAI 呼び出しやその他外部依存は内部関数をモック差し替え可能にしてユニットテストを容易化。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

---

今後のロードマップ（短期予定）
- AI モデルの入れ替え／設定最適化（温度・system prompt の調整や別モデル対応）
- J-Quants / kabu API クライアント実装の整備（現在は参照箇所あり）
- 追加の品質チェックルールやモニタリング用メトリクス拡充

貢献・報告
- バグ報告や改善提案は Issue を立ててください。セキュリティ上の脆弱性は直接連絡してください。