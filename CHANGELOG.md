CHANGELOG
=========

すべての注目すべき変更点をここに記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]: https://example.invalid/unreleased
[0.1.0]: https://example.invalid/v0.1.0

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム "KabuSys" のコア機能を提供します。以下のモジュールと機能が含まれます。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - パッケージトップで主要サブパッケージをエクスポート: data, strategy, execution, monitoring。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env パース処理の実装（コメント行、省略・export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得ユーティリティ `_require` と、アプリ設定を提供する `Settings` クラス（J-Quants、kabuステーション、LINE、DBパス、監視閾値、環境・ログレベル検証等のプロパティを含む）。
  - デフォルト値（KABU_API_BASE_URL、データベースパスなど）と入力検証（KABUSYS_ENV、LOG_LEVEL の許容値）を用意。

- ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
  - raw_news + news_symbols を用いたニュース集約処理と、OpenAI（gpt-4o-mini）の JSON Mode を用いるバッチセンチメント評価機能。
  - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を行う `calc_news_window`。
  - 1銘柄あたりの記事上限・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - バッチ送信（最大 20 銘柄）とリトライ（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）処理。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列型確認、コード整合性、数値チェック、スコアクリップ）。
  - 書き込み時の冪等性配慮（部分成功時に他銘柄の既存スコアを保持するための削除→挿入フロー、DuckDB の executemany の空配列制約への対応）。
  - 公開 API: `score_news(conn, target_date, api_key=None)` — 書き込んだ銘柄数を返す。

- 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存。
  - マクロキーワードによるニュース抽出、OpenAI 呼び出しの独立実装（モジュール間結合を避ける設計）、リトライとフォールバック（失敗時 macro_sentiment=0.0）を備える。
  - レジームの判定ロジック、スコアのクリップ、DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - 公開 API: `score_regime(conn, target_date, api_key=None)` — 成功時に 1 を返す。

- 研究用ファクター計算 (`kabusys.research`)
  - `factor_research`:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）を計算する `calc_momentum`。
    - ボラティリティ・流動性（20日 ATR、相対ATR、20日平均売買代金、出来高比率）を計算する `calc_volatility`。
    - バリュー（PER, ROE）を raw_financials と株価から算出する `calc_value`。
  - `feature_exploration`:
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン対応、入力検証あり）。
    - 情報係数（IC）計算 `calc_ic`（Spearman ランク相関）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク）。
    - ファクター統計サマリ `factor_summary`（count/mean/std/min/max/median）。
  - いずれも DuckDB に対する SQL + Python 実装で、外部ライブラリ依存を排除。

- データ管理 (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)：
    - market_calendar を参照した営業日判定（is_trading_day）、SQ判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）を実装。
    - DB データがない場合は曜日ベース（土日非営業日）でフォールバック。
    - JPX カレンダーを J-Quants から差分取得して更新するバッチジョブ `calendar_update_job`（バックフィル、健全性チェック、冪等保存を実装）。
  - ETL パイプライン (`pipeline`)：
    - ETL 実行結果を保持する dataclass `ETLResult`（フェッチ数・保存数・品質問題・エラー等）を提供。
    - 差分取得・backfill・品質チェックの方針を実装（実運用向け設計）。
  - `etl` モジュールで `ETLResult` を再エクスポート。

- テスト容易性と設計上の配慮
  - OpenAI 呼び出しをモジュール内で分離（_call_openai_api）して unittest.mock.patch による差し替えを容易にしている。
  - ルックアヘッドバイアス防止のため、すべての処理は明示的な target_date を受け取り、date.today() / datetime.today() を直接参照しない設計。
  - DB 書き込み失敗時の ROLLBACK とログ出力を整備。

### 変更 (Changed)
- 設計方針の明確化（各モジュール）
  - AI モジュール、研究モジュール、データモジュールはいずれも「本番の取引・発注 API にはアクセスしない」ことを明記（分析・研究・スコア生成に限定）。
  - DuckDB を中心に SQL で集計を行い、外部ライブラリへの依存を最小化する方針を採用。

### 修正 (Fixed)
- エラー耐性の向上
  - OpenAI API 呼び出しでのリトライロジック（429/ネットワーク/タイムアウト/5xx）を統一して実装し、全リトライ消費時はフォールバックを行う仕様に。
  - JSON レスポンスのパース失敗時にレスポンス中の最外の {} を抽出して復元を試みるなど、実運用で生じるノイズに対処。
  - DuckDB の executemany が空リストを受け付けない点を考慮した条件分岐を追加。

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーやその他シークレットは環境変数経由で扱う設計。必須環境変数が未設定の場合は明示的に ValueError を発生させるため、誤った公開を防止できる。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI の誤用を防ぐため）。

---

注: 初回リリースのため Breaking Changes はありません。

移行メモ / 使い始めガイド（短縮版）
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（news/regime のスコアリングに必須）
- 自動 .env 読み込み
  - プロジェクトルートに .env/.env.local を配置すると自動で読み込まれます（.env.local は .env を上書き）。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- デフォルトのデータベースパス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- OpenAI を使う関数 (`score_news`, `score_regime`) は api_key を引数で注入可能。テスト時は引数でキーを渡すか unittest.mock により _call_openai_api を差し替えてください。

その他の詳細は各モジュールの docstring やログ出力を参照してください。