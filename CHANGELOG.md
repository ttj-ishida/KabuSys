# CHANGELOG

すべての注目すべき変更をこのファイルで管理します。フォーマットは Keep a Changelog に準拠します。

なお、以下はコードベースの内容から推測して作成したリリースノートです（自動生成／推測による記述を含みます）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤的な機能群を実装しました。主な追加点、設計方針、フォールバック／フェイルセーフ挙動を以下にまとめます。

### Added
- パッケージの基礎
  - パッケージ初期化: `kabusys.__init__`（バージョン 0.1.0、公開 API: data, strategy, execution, monitoring）
- 環境設定 / ロード
  - `kabusys.config`
    - .env ファイルおよび環境変数の自動読み込み機能（プロジェクトルートの検出: `.git` または `pyproject.toml`）。
    - `.env` / `.env.local` の優先順位、既存 OS 環境変数の保護（protected set）を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート（テスト用途）。
    - 行パーサーはクォート、エスケープ、コメントルールに対応。
    - `Settings` クラスで各種設定値をプロパティ経由で取得（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル 等）。
    - 必須キー未設定時は明確な ValueError を送出。
- AI (NLP) 機能
  - `kabusys.ai.news_nlp`
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送信し、センチメント（ai_score）を算出・`ai_scores` テーブルへ書き込み。
    - タイムウィンドウ（JST 基準の前日 15:00 ～ 当日 08:30）計算ユーティリティ `calc_news_window`。
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄当たりの記事上限と文字トリム、JSON Mode を用いたレスポンス検証。
    - 再試行（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。失敗はログ出力の上スキップし処理継続（フェイルセーフ）。
    - レスポンス検証ロジック（JSON 抽出、results 配列検証、コード照合、スコア数値検証、±1.0 クリップ）。
  - `kabusys.ai.regime_detector`
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ冪等書き込み。
    - マクロ記事抽出のキーワードリスト、OpenAI 呼び出し、再試行ポリシー、API障害時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ参照、datetime.today()/date.today() を計算に直接使わない）。
- 研究（Research）モジュール
  - `kabusys.research.factor_research`
    - モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）等のファクター計算関数を追加。
    - DuckDB 上で SQL を用いて計算し、(date, code) ベースで結果リストを返す。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（horizons: デフォルト [1,5,21]）、IC（Spearman ランク相関）、ファクター統計サマリー、ランク付けユーティリティを実装。
    - pandas 等外部ライブラリに依存しない純 Python 実装。
- データプラットフォーム（Data）モジュール
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理（market_calendar）: 営業日判定、next/prev trading day、期間内営業日取得、SQ 日判定、夜間バッチ更新ジョブ（J-Quants API から差分取得して冪等保存）を実装。
    - カレンダー未取得時の曜日ベースのフォールバック、最大探索日数制限、バックフィル設定、健全性チェックを実装。
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL の概念実装（差分取得、保存、品質チェックのフロー設計）。
    - `ETLResult` データクラスを公開（取得数 / 保存数 / 品質問題 / エラー概要 等）。
    - DuckDB 互換性を意識した設計（executemany の空リスト回避等）。
  - `kabusys.data` から ETLResult を再エクスポート。
- DuckDB を想定した DB 操作と互換性考慮（型変換ユーティリティ、空テーブルチェックなど）。
- OpenAI SDK（chat completions / JSON mode）を使う箇所での抽象化／テスト差し替えポイント（内部 _call_openai_api をモック可能）。

### Changed
- 初リリースのため該当なし。

### Fixed
- 初リリースのため該当なし。

### Security
- 環境変数ロード時に OS 環境変数を保護する仕組み（読み込み時 protected set により既存値を上書きしない）を導入。
- OpenAI API キー未設定時は明示的なエラー（ValueError）で失敗させ、鍵漏れなどの潜在的問題を早期検出可能に。

### Design / Implementation Notes（重要な設計判断）
- ルックアヘッドバイアス防止: AI スコアリング / レジーム判定 / ファクター計算のいずれも、target_date の将来データを参照しないよう明確に設計されています（date 比較は排他条件を多用、datetime.today() を直接用いない）。
- フェイルセーフ設計: 外部 API（OpenAI / J-Quants 等）障害時は部分失敗で全体を停止させず、ログ出力＋フォールバック（例: macro_sentiment=0.0）やスキップで継続する方針を採用。
- 再試行ポリシー: OpenAI 呼び出しは 429/ネットワークエラー/タイムアウト/5xx を対象に指数バックオフで再試行。
- DuckDB 互換性: executemany の挙動や日付型の取り扱いに配慮した実装（空 params の回避、date オブジェクト変換等）。
- レスポンス検証: LLM のレスポンスは厳密に JSON として期待するが、前後テキストが混入することを想定して最外側の {} を抽出して復元する処理などのロバスト化を行っています。
- 設定のデフォルト: DB パス等はデフォルト値を持ち、Settings 経由で取得可能（例: DuckDB デフォルト "data/kabusys.duckdb"、SQLite デフォルト "data/monitoring.db" など）。

### Breaking Changes
- 初リリースのため該当なし。

---

もし詳細なリリース日付や追加で特筆すべき差分（例えばテストカバレッジ、CI、サンプルデータ、DB スキーマ定義ファイルなど）があれば、それに応じて CHANGELOG を拡張します。