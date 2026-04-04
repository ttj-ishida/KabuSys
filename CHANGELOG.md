# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本履歴はリポジトリ内のコード内容から推測して作成した初期リリース向けの要約です。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。パッケージの基盤となる機能群（データETL / カレンダー管理 / 研究用ファクター計算 / ニュースNLP / 市場レジーム判定 / 環境設定）が実装されています。

### 追加 (Added)
- パッケージ基盤
  - パッケージルートのバージョンを設定: `kabusys.__version__ = "0.1.0"`
  - 主要サブパッケージをエクスポート: `data`, `strategy`, `execution`, `monitoring`（パッケージ構成の公開インターフェース）

- 環境設定 / ロード (src/kabusys/config.py)
  - 環境変数管理クラス `Settings` を実装。
    - 必須値取得 `_require()` により未設定時に明確なエラーを出す。
    - 複数の設定プロパティを提供（J-Quants トークン、kabu API、LINE トークン、DB パス、監視用ファイルパス、閾値、実行環境判定など）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の許容値チェックを実装（不正な値は例外）。
    - `is_live/is_paper/is_dev` のユーティリティプロパティを提供。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト等用）。
    - .env のパーサは `export KEY=val`、クォートやバックスラッシュエスケープ、インラインコメント（条件付き）に対応する堅牢な実装。

- データ / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX マーケットカレンダー管理機能を実装。
    - 営業日判定: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB にデータがない場合は曜日ベースでフォールバック（土日除外）。
    - 最大探索範囲（安全対策）を導入し無限ループを防止。
  - 夜間バッチ更新ジョブ `calendar_update_job` を実装。
    - J-Quants から差分取得し idempotent に保存（保存処理は jquants_client 経由を想定）。
    - バックフィル機能、健全性チェック（極端に未来の日付検知）を実装。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py, etl.py)
  - ETL 実行結果を表す `ETLResult` データクラスを追加（フェイル情報、品質チェック結果、取得/保存件数を含む）。
  - 差分更新・バックフィル・品質チェックを行う設計（jquants_client と quality モジュールを利用する想定）。
  - `etl.py` で `ETLResult` を公開（再エクスポート）。

- ニュース NLP / AI スコアリング (src/kabusys/ai/news_nlp.py)
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）で評価し `ai_scores` テーブルへ書き込む処理を実装。
    - タイムウィンドウ (前日15:00 JST ～ 当日08:30 JST、UTC に変換) を計算する `calc_news_window`。
    - raw_news と news_symbols を結合して銘柄ごとに最新記事を集約する `_fetch_articles`（記事数・文字数のトリム対応）。
    - 1回の API 呼び出しで最大 20 銘柄をバッチ送信（_BATCH_SIZE）。
    - レスポンスは JSON Mode を想定し、厳密なバリデーションを実施（`_validate_and_extract`）。
    - リトライ/バックオフ: 429、ネットワーク断、タイムアウト、5xx サーバーエラーは指数バックスオフでリトライ。
    - スコアを ±1.0 にクリップし、取得成功分のみを DELETE→INSERT で置換して部分失敗時に既存データを保持。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（225連動ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除。
    - マクロニュースは `news_nlp.calc_news_window` と raw_news のフィルタで取得。
    - OpenAI 呼び出しは独立実装、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジーム値は clip(-1,1) 後に閾値判定し、`market_regime` テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。

- 研究（Research）モジュール (src/kabusys/research/)
  - ファクター計算群を実装 (`factor_research.py`)
    - `calc_momentum`: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - `calc_volatility`: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
    - `calc_value`: raw_financials から EPS/ROE を参照して PER/ROE を算出。
    - DuckDB を用いた SQL ベースの計算（外部発注や本番口座アクセスなし）。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - `calc_forward_returns`: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを計算（リード関数を利用、ホライズン検証あり）。
    - `calc_ic`: スピアマンランク相関（IC）計算。
    - `rank`: 同順位は平均ランクを返すランク化ユーティリティ（丸めで ties を安定化）。
    - `factor_summary`: count/mean/std/min/max/median を算出する統計サマリー。

- 共通設計方針（多数のモジュールで共通）
  - ルックアヘッドバイアス対策: ほぼ全ての関数が内部で datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計。
  - DuckDB を主要なローカルDB として利用する前提で実装。
  - idempotent な DB 書き込み（DELETE→INSERT、ON CONFLICT を想定）により再実行可能性を担保。
  - API 失敗時はフェイルセーフ（例外を破壊的に投げない、スコアにフォールバックする等）を原則とする設計。
  - OpenAI 呼び出しに関しては JSON パース失敗や未知データを丁寧に扱う実装（ログ出力を行い処理継続）。

### 変更 (Changed)
- 初回リリースにつき該当なし。

### 修正 (Fixed)
- 初回リリースにつき該当なし。

### 削除 (Removed)
- 初回リリースにつき該当なし。

### セキュリティ (Security)
- 初期リリースにつき特記なし。API キーやシークレットの取り扱いは環境変数/`.env` 経由を想定。

---

注記:
- 実装は各モジュール内に詳細なログ出力とエラーハンドリングを備えており、運用時の観測性を考慮しています。
- 実際の外部連携（J-Quants クライアント、kabu ステーション API、LINE 送信処理など）は別モジュール（参照されているがここに含まれない）に委譲する設計になっています。
- 上記はソースコードから推測した機能一覧と設計方針の要約です。実際のリリースノート作成時はテスト結果や既知の問題点（BUG / TODO）を追加してください。