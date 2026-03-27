# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

なお、この CHANGELOG はリポジトリ内のコードから機能追加・設計方針・既知の挙動を推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初期公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンは `0.1.0`。
  - パッケージの公開 API として `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。

- 環境設定・ローダー
  - `kabusys.config.Settings` を実装し、環境変数経由で各種設定を取得（J-Quants、kabuステーション、Slack、DBパス、実行環境判定等）。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を起点）。
  - .env / .env.local の自動読み込みを実装（読み込み順: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーを実装（コメント行、export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 必須環境変数未設定時に分かりやすい例外メッセージを出す `_require` を提供。
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の値検証を実装。ユーティリティプロパティ `is_live`, `is_paper`, `is_dev` を追加。

- AI モジュール
  - ニュース NLP（`kabusys.ai.news_nlp`）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）に送って銘柄ごとのセンチメント（-1.0〜1.0）を算出し `ai_scores` テーブルへ書き込む `score_news` を実装。
    - バッチサイズ、最大記事数・文字数制限、タイムウィンドウ（前日15:00 JST〜当日08:30 JST）といったパラメータを定義。
    - API リトライ（429/接続断/タイムアウト/5xx に対する指数バックオフ）・レスポンス検証・スコアのクリップ・部分的な DB 上書き（部分失敗時に他コードを保護）を実装。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能に設計（内部 _call_openai_api をパッチ可能）。
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次の市場レジーム（bull / neutral / bear）を算出する `score_regime` を実装。
    - マクロニュース抽出のキーワードリスト、LLM へのプロンプト（JSON 出力必須）を定義。API 呼び出し時のリトライやフェイルセーフ（API 失敗時は macro_sentiment=0.0）が組み込まれている。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - ルックアヘッドバイアス回避のため、target_date 未満のデータのみを参照し、date.today() 等に依存しない設計。

- データ基盤（Data）
  - カレンダー管理（`kabusys.data.calendar_management`）
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job` を実装（J-Quants API 経由で取得 → `market_calendar` に冪等保存）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 最大探索範囲・バックフィル・健全性チェック（将来日付の異常検知）などの安全策を実装。
  - ETL パイプライン（`kabusys.data.pipeline`, `kabusys.data.etl`）
    - ETL 実行結果を表す `ETLResult` データクラスを追加（取得数・保存数・品質問題・エラー一覧などを格納）。
    - 差分取得、backfill、品質チェック（quality モジュール）を想定した設計。J-Quants クライアントを利用して idempotent に保存する方針を明示。
    - 内部ユーティリティとしてテーブル存在チェックや最大日付取得ロジックを追加。

- リサーチ（Research）
  - `kabusys.research` 名前空間にファクター計算・特徴量探索ツールを追加。
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）、Liquidity（20 日平均売買代金、出来高比率）等の計算関数を実装: `calc_momentum`, `calc_volatility`, `calc_value`。
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時の None ハンドリングを行う。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 `calc_ic`（Spearman 的なランク相関、欠損/小サンプル対応）。
    - ランキング関数 `rank`（同順位は平均ランク）、統計サマリー `factor_summary` を実装。
  - z-score 正規化ユーティリティを `kabusys.data.stats.zscore_normalize` から再エクスポート（research.__init__で公開）。

### 変更 (Changed)
- 設計上の重要ポイント（ドキュメント化）
  - ルックアヘッドバイアス防止のため、各種処理は datetime.today() / date.today() に依存しない設計とした点を明記。
  - OpenAI 呼び出しについてはモジュール間で内部関数を共有しない（news_nlp と regime_detector で別実装）方針によりテスト性とモジュール結合度低減を図った。

### 修正 (Fixed)
- 自動 .env ロードの堅牢化
  - .env 読み込み時のファイルエンコーディング、存在確認、読み込み失敗時の警告発行を実装。
  - OS 環境変数を保護するため .env 読み込み時に既存環境変数を上書きしない（`.env.local` は override=True で上書き可能）。

### 既知の挙動 / 注意点 (Known issues / Notes)
- OpenAI API キーは必須（news_nlp.score_news / regime_detector.score_regime の api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する。
- DuckDB を前提とした SQL 実装のため、DuckDB のバージョン差異（例: executemany の空リストの扱い・配列バインドの互換性）に注意が必要。
- AI モジュールのレスポンスは JSON モード想定だが、稀に前後に余計なテキストが混ざることを想定してパースの救済処理を実装している（最外の {} を抽出してパース）。
- .env の解析は多くのケースをカバーしているが、極端に複雑なシェル構文には対応していない。
- market_calendar が未取得の場合は曜日ベースのフォールバックを行うため、完全なカレンダー精度を求める用途では事前に calendar_update_job を実行しておくことを推奨。

---

この CHANGELOG はソースコードの実装内容に基づき作成しています。実際のコミット履歴や意図と異なる可能性があるため、正式なリリースノートを作成する際は Git 履歴・リリース担当の確認をお願いします。