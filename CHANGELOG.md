# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買 / データ基盤 / リサーチ用ユーティリティ群を含むパッケージを追加しました。

### 追加 (Added)
- パッケージ全体
  - kabusys パッケージ初版を追加。公開バージョンは `0.1.0`。
  - パブリックモジュール: data, research, ai, monitoring, strategy, execution（パッケージ定義に含めたエクスポート）。

- 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env パーサの堅牢化（export プレフィックス対応、クォート内のエスケープ対応、コメント扱いのルールなど）。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証ユーティリティ
    - is_live / is_paper / is_dev 判定プロパティ

- データ (kabusys.data)
  - ETL パイプラインの公開型 `ETLResult` を追加（kabusys.data.pipeline）。
  - calendar_management: JPX カレンダーの管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants から差分取得・冪等保存）。
    - カレンダー未取得時の曜日フォールバック、バックフィル、健全性チェックなどを実装。
  - pipeline: ETL 実行のユーティリティを実装（差分取得、保存、品質チェックの統合設計）。ETLResult により実行結果を集約。

- AI（自然言語処理） (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini / JSON Mode）で銘柄別センチメントを算出して ai_scores テーブルへ保存する `score_news` を実装。
    - チャンク処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数 / 文字数のトリム）、リトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ、不正レスポンス時のフォールバック（スキップ）等を実装。
    - テスト用に OpenAI 呼び出し関数の差し替え可能（unittest.mock.patch 対応）。
    - タイムウィンドウ計算ユーティリティ `calc_news_window` を公開。
  - regime_detector:
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する `score_regime` を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（モデル gpt-4o-mini）、再試行ロジック、API失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - LLM 呼び出しは news_nlp とは独立した実装としモジュール結合を避ける設計。

- リサーチ (kabusys.research)
  - factor_research:
    - `calc_momentum`: 1M/3M/6M リターン、200日 MA 乖離率を計算（データ不足時は None を返す）。
    - `calc_volatility`: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
    - `calc_value`: raw_financials から最新財務を取得し PER / ROE を計算。
    - DuckDB SQL を用いた実装で、本番の発注等へのアクセスは行わない。
  - feature_exploration:
    - `calc_forward_returns`: 各ホライズンの将来リターン（デフォルト: 1/5/21 営業日）を計算。
    - `calc_ic`: Spearman ランク相関（IC）を計算。
    - `rank`, `factor_summary`: ランク変換、統計サマリー（count/mean/std/min/max/median）を実装。
  - 研究用途のユーティリティ群をまとめてエクスポート。

### 変更 (Changed)
- 初期リリースのため既存コードからの「変更」はありませんが、設計方針として以下を一貫して採用しています:
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today() / date.today() を直接利用しない（関数に target_date を明示的に渡す）。
  - DuckDB に対する書き込みは冪等性を確保（DELETE→INSERT 等）し、部分失敗時に既存データの不必要な削除を避ける。
  - OpenAI API 呼び出しでのフォールバック（API失敗時に処理を継続）を採用し、単一記事・単一銘柄の障害がシステム全体停止につながらないよう設計。

### 修正・堅牢化 (Fixed / Hardened)
- .env パーサを強化（export プレフィックス、クォート内のバックスラッシュエスケープ、コメントの取り扱いを改善）。
- OpenAI レスポンスのパース耐性を強化（JSON mode でも外側に余計なテキストが混ざるケースから最外の {} を抽出するフォールバック処理）。
- API 呼び出し周りのエラーハンドリングを整理（RateLimit, Connection, Timeout, 5xx をリトライ、それ以外はスキップ／警告）。
- DuckDB に対する executemany 空パラメータの扱い（DuckDB 0.10 の制約）に配慮した防御実装。

### 既知の制約 / 注意点 (Notes)
- OpenAI API:
  - AI 関連関数（score_news, score_regime）は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出します。
  - 使用モデルは gpt-4o-mini（JSON mode）を想定。
  - テスト時は内部の _call_openai_api をモックすることを推奨。
- データベーススキーマ:
  - 各機能は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提とします。初期導入時はスキーマ準備が必要です。
- 自動 .env 読み込み:
  - プロジェクトルート検出は __file__ を基点に親ディレクトリを探索します。配布形態や配置によっては想定通り検出されない場合があるため、必要に応じて環境変数を明示的に設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 互換性:
  - DuckDB のバージョン差異（特に executemany の挙動やリスト型バインド）に配慮した実装を行っていますが、実環境での動作確認を推奨します。

### 互換性に関する注意 (Breaking Changes)
- 初回リリースのため破壊的変更はありません。

### セキュリティ (Security)
- 本リリースで特記事項はありません。API キー等の機密情報は .env か OS 環境変数で管理してください。

---

開発者向け補足（短め）
- 主要パブリック API:
  - 設定: `from kabusys.config import settings`
  - AI: `from kabusys.ai.news_nlp import score_news`, `from kabusys.ai.regime_detector import score_regime`
  - Research: `kabusys.research` の関数群（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
  - Data ETL: `from kabusys.data import ETLResult`、calendar 管理関数 (`is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `calendar_update_job`)

今後の予定（参考）
- モデルやプロンプトの改良、AI 処理のメタデータ保存、ETL のスケジューリング実装、監視 / モニタリングの追加などを予定しています。