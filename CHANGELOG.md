# Changelog

すべての変更は Keep a Changelog の形式に従います。  
リリース日はコードベースから推測して記載しています。

## [0.1.0] - 2026-03-29

初期公開リリース。

### 追加 (Added)
- パッケージの基本構造を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`, 公開 API (`__all__`) を定義。
- 設定 / 環境変数管理機能（kabusys.config）を追加。
  - プロジェクトルート検出 `_find_project_root()` を導入し、配布後も .env 自動読み込みが期待通りに動作するように実装。
  - .env パーサー `_parse_env_line()` を実装（`export` プレフィックス、クォート、インラインコメント、バックスラッシュエスケープ対応）。
  - `.env`, `.env.local` の自動読み込みの仕組みを導入（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - 環境変数未設定時に例外を投げる `_require()` と、型変換・検証を含む `Settings` クラス（J-Quants / kabu / Slack / DB パス / 環境名・ログレベル検証など）を実装。
- AI 関連モジュール（kabusys.ai）を追加。
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - ニュース収集ウィンドウ計算 (`calc_news_window`) を実装（JST 基準で UTC に変換）。
    - raw_news と news_symbols を銘柄毎に集約して OpenAI に送信、バッチ（最大 20 銘柄）で処理する仕組みを実装。
    - トークン肥大化対策（1 銘柄あたり記事数・文字数制限）。
    - OpenAI への再試行（429 / ネットワーク断 / タイムアウト / 5xx）を導入（指数バックオフ）。
    - レスポンスバリデーションとスコアのクリップ、部分成功時の DB 置換ロジック（DELETE → INSERT）を実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードでニュースを抽出する `_fetch_macro_news`、MA200 乖離計算 `_calc_ma200_ratio`、LLM 呼び出しと再試行 `_score_macro` を実装。
    - レジーム結果を `market_regime` テーブルへ冪等的に書き込む処理を実装（BEGIN / DELETE / INSERT / COMMIT）。
    - API 失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフを採用。
- Research / ファクター関連（kabusys.research）を追加。
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金 / 出来高比）、バリュー（PER, ROE）を計算する関数を実装（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB を用いた SQL ベースの計算と欠損時の None 処理。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（`calc_forward_returns`）・IC（Information Coefficient）計算（`calc_ic`）・ランク変換（`rank`）・統計サマリー（`factor_summary`）を実装。
    - pandas 等に依存せず標準ライブラリのみで完結する設計。
  - 研究用ユーティリティ `zscore_normalize` を `kabusys.data.stats` から再エクスポート。
- Data プラットフォーム関連（kabusys.data）を追加。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - 営業日判定 API: `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を実装。
    - DB 登録値優先かつ未登録日は曜日ベースのフォールバックを行う一貫した判定ロジック。
    - 夜間バッチ `calendar_update_job` を実装（J‑Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を表すデータクラス `ETLResult` を追加（品質チェック結果・エラー一覧を含む）。
    - 差分取得・最終日取得などのユーティリティを実装。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - jquants_client を利用した外部データ取得との連携を想定（関数呼び出し箇所を用意）。

### 変更 (Changed)
- 設計方針として共通の注意点を明示（各モジュールの docstring に記載）。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を関数内部で参照しない設計を明確化（target_date を明示的に渡す）。
  - API 呼び出し失敗時は処理を完全停止せずフェイルセーフ（0 やスキップ）で継続するポリシーを採用。
  - DuckDB のバージョン差異に対する互換性（executemany の空リスト禁止など）に配慮した実装。

### 修正 (Fixed)
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント判定の改善を導入。
- OpenAI API 呼び出しのエラー処理強化:
  - RateLimitError / APIConnectionError / APITimeoutError / APIError に対するリトライ戦略とログ出力を追加。
  - レスポンスの JSON パース失敗・期待構造の不正時は安全にフォールバックして処理継続。
- DuckDB 書き込み時の冪等性確保:
  - 部分失敗時に既存の他銘柄データを保護するため、DELETE → INSERT の置換戦略を採用。executemany 前に空リストチェックを入れて DuckDB 0.10 の制約に対応。

### 非推奨 (Deprecated)
- なし（初期リリース）。

### 削除 (Removed)
- なし（初期リリース）。

### セキュリティ (Security)
- 環境変数の自動読み込みで OS 環境変数を保護する仕組みを導入（自動ロード時に既存 OS 環境変数を protected として上書きされない）。
- OpenAI API キーは明示的に引数で注入可能。未設定時は ValueError を発生させるため、キー漏洩のリスクを低くする設計方針を明示。

---

注意事項（既知の利用上のポイント）
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（env: OPENAI_API_KEY）または引数での注入が必須です。未設定時は ValueError が発生します。
- 自動で .env を読み込む動作はデフォルト ON。テストや特殊環境でこれを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のバージョン差分に依存する部分（特に executemany の空リストハンドリング）に注意してください。
- 各モジュールはルックアヘッドバイアスを避けるため target_date を明示的に受け取る設計になっています。利用時は必ず適切な target_date を渡してください。

今後の改善候補（非網羅）
- ai モジュールのテスト用モック/抽象化の強化（現状は内部関数を patch してテストを想定）。
- OpenAI のレスポンススキーマのより厳格なスキーマ検証（型ライブラリや pydantic 等の導入検討）。
- ETL ワークフローの Orchestration（スケジューラ / 監視）導入。