# CHANGELOG

すべての重要な変更はこのファイルに記録します。本プロジェクトは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-31

初回リリース

### 追加
- パッケージ基盤
  - pakage: `kabusys` の初期公開インターフェースを追加（`__version__ = "0.1.0"`、`__all__` に data/strategy/execution/monitoring を登録）。
- 設定管理
  - `kabusys.config`:
    - .env ファイル（`.env` / `.env.local`）および環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行うため CWD に依存しない。
    - 行パーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い）を実装。
    - OS 環境変数の保護（`protected`）により自動ロード時の上書きを制御。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
    - `Settings` クラスを追加し、主要な設定項目（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定等）をプロパティで取得可能に。
    - 環境値検証（`KABUSYS_ENV` と `LOG_LEVEL` の許容値チェック）とヘルプ的エラーメッセージを追加。
- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp`:
    - raw_news および news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）により銘柄別センチメント（-1.0〜1.0）を算出して `ai_scores` テーブルへ書き込む処理を実装。
    - チャンク処理（最大20銘柄/回）、1銘柄あたりの記事数・文字数上限（トリム）、レスポンス検証、スコアのクリップ処理を実装。
    - HTTP 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API エラー時のフォールバック（失敗したチャンクはスキップ）を実装。
    - DuckDB の制約に対応した安全な書き込み（部分成功時に既存スコアを保護するため、対象コードのみ DELETE→INSERT）を実装。
    - テスト容易性のため、内部の OpenAI 呼び出しをモック差し替え可能（`_call_openai_api` を patch）。
  - `kabusys.ai.regime_detector`:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（`bull`/`neutral`/`bear`）を判定し `market_regime` テーブルへ冪等書き込みする処理を実装。
    - マクロ記事抽出（キーワードフィルタ）、OpenAI による JSON 出力のパースと検証、リトライ・エラーフォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス対策（date 未満条件、datetime.today() の非参照など）を徹底。
- データ / ETL / カレンダー
  - `kabusys.data.pipeline`:
    - 差分更新、バックフィル、品質チェック、ETL 実行結果を表す `ETLResult` データクラスを実装。品質問題やエラーを収集して呼び出し元で判断可能に。
    - DuckDB のテーブル存在チェックや最大日付取得等のユーティリティを実装。
  - `kabusys.data.etl`:
    - pipeline の `ETLResult` を再エクスポートして公開インターフェースを提供。
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理（`market_calendar`）の夜間更新ジョブ `calendar_update_job` と、営業日判定ロジック（`is_trading_day` / `next_trading_day` / `prev_trading_day` / `get_trading_days` / `is_sq_day`）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動を採用。
    - 最大探索範囲やバッファ・バックフィル・健全性チェック（未来日付の異常検出）を実装。
- リサーチ（ファクター計算・特徴量探索）
  - `kabusys.research.factor_research`:
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）等のファクター計算関数（`calc_momentum`, `calc_volatility`, `calc_value`）を実装。DuckDB SQL を活用し、データ不足時の None 処理を明確化。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算（`calc_forward_returns`）、IC（Spearman ρ）計算（`calc_ic`）、ランク化ユーティリティ（`rank`）、ファクター統計サマリ（`factor_summary`）を実装。
    - pandas 等の外部依存を避け、標準ライブラリのみで実装。
- テスト/開発支援
  - 内部の OpenAI 呼び出し関数（`_call_openai_api`）をユニットテスト時に patch して差し替え可能にしているため、外部 API に依存しないテストが容易。
- ドキュメント/設計注釈
  - 各モジュールに設計方針やフェイルセーフ・ルックアヘッドバイアス防止に関する注釈を豊富に追加。

### 変更
- 該当なし（初回公開）

### 修正
- 環境ファイルパーサの堅牢化:
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い、無効行のスキップ等を実装して .env パースの互換性を向上。
- DuckDB 書き込みの互換性対応:
  - `executemany` に空リストを渡さないガードを追加（DuckDB 0.10 の挙動への対応）。

### 既知の注意点 / 制約
- OpenAI API:
  - ニュース NLP / レジーム判定はいずれも OpenAI（デフォルトモデル: gpt-4o-mini）を利用する。API キーは引数または環境変数 `OPENAI_API_KEY` で提供する必要があり、未設定時は ValueError が発生する。
  - LLM による解析は外部サービス依存であり、API 失敗時はスコアを 0.0 にフォールバックする等のフェイルセーフを実装しているが、完全性は保証できない。
- ルックアヘッドバイアス対策:
  - 各処理は内部で datetime.today()/date.today() を直接参照しない設計（入力として target_date を明示）で、データのルックアヘッドバイアスを低減している。
- DB スキーマ:
  - 本コードは特定の DuckDB テーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提としている。実行前に対応するスキーマ/データが必要。
- 互換性:
  - `jquants_client` 等の外部モジュールは本リポジトリで参照されているが、ここに示したコードスニペットに含まれないため、実行時には該当クライアント実装が必要。

### セキュリティ
- 自動 .env 読み込み時に OS 環境変数を保護（既存キーは上書きされない）する仕組みを導入。
- 機密情報（API トークン等）は環境変数で管理することを推奨。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能。

---

※ 初回リリースのため、以降の変更はこのファイルに逐次追記します。