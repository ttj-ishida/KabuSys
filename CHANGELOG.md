# Changelog

すべての変更は "Keep a Changelog" の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加（Added）
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - パッケージバージョンを `0.1.0` として設定。

- 環境設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - .env パーサーの強化:
    - コメント行・空行の無視
    - export 構文のサポート（例: export KEY=val）
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント判定の改善（未クォート値の '#' 前の空白でのみコメント扱い）
  - .env 読み込み時に OS 環境変数を保護する機能（protected set）を実装。
  - 必須環境変数取得時に未設定なら ValueError を投げる `_require` を提供。
  - 各種設定プロパティを提供（J-Quants, kabuステーション, Slack, DB パス, 環境判定, ログレベルなど）。
  - 有効値検証（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI 関連（kabusys.ai）
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini）の JSON mode を用いたバッチセンチメントスコアリングを実装。
    - タイムウィンドウ計算（JST基準）と DuckDB からのニュース／銘柄集約処理を実装。
    - 銘柄ごとの記事トリム（最大記事数・最大文字数）やバッチサイズ制御を実装。
    - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスの厳密なバリデーションとスコアのクリップ（±1.0）。
    - DuckDB に対して部分置換（DELETE → INSERT）で冪等性を確保（部分失敗時に既存データ保護）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能な内部関数を提供（unittest.mock.patch に対応）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、リトライ・フェイルセーフ処理（API障害時は macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - ルックアヘッドバイアス防止のため日付参照は引数ベースで実装（datetime.today() を直接参照しない）。

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client 経由）、品質チェックの骨組みを実装。
    - ETL 実行結果を格納する dataclass `ETLResult` を公開（kabusys.data.etl 経由で再エクスポート）。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
    - backfill・カレンダー先読み等の設定を組み込み。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装（J-Quants API 経由）。
    - 営業日判定・前後営業日取得・期間内営業日列挙（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar がない場合の曜日ベースのフォールバック処理を提供。
    - 最大探索日数制限やバックフィル、健全性チェックを実装。

  - jquants_client への依存箇所（fetch/save 呼び出し）を想定した設計。

- 研究用解析（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）の計算を DuckDB SQL ベースで実装。
    - データ不足時は None を返すなど堅牢な設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）を汎用ホライズン対応で実装。
    - IC（Spearman の ρ）計算（calc_ic）、ランク化関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純 Python 実装。

### 変更（Changed）
- （初回リリースのため履歴なし）

### 修正（Fixed）
- （初回リリースのため履歴なし）

### 非推奨（Deprecated）
- （初回リリースのため履歴なし）

### 削除（Removed）
- （初回リリースのため履歴なし）

### セキュリティ（Security）
- 環境変数の必須チェックを導入し、未設定の場合は明示的にエラーを返す（機密情報の誤設定に備える）。
- .env 読み込み時に OS 環境変数を保護（上書き防止）するデフォルトの挙動を採用。

---

注記:
- OpenAI の利用は API キーが必要です。各 AI 関数は引数で api_key を受け取るか環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError を送出します。
- DuckDB 互換性のため executemany に空リストを渡さない等の実装上の注意を組み込んでいます。
- 多くの箇所で「ルックアヘッドバイアス防止」の方針に従い、日時は引数ベースで扱う設計になっています。