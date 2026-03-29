# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の方針に準拠しています。セマンティックバージョニングを採用しています。

現在のバージョン: 0.1.0

## [Unreleased]

- 今後の予定・改善案（コードから推測）
  - OpenAI 呼び出しの並列化やバッチ最適化
  - モデル選択の外部設定化（現状は gpt-4o-mini 固定）
  - DuckDB のスキーマ検証やマイグレーション仕組みの追加
  - より詳細な品質チェック結果のレポーティング UI / ロギング改善

---

## [0.1.0] - 2026-03-29

初回リリース。以下の主要機能を実装・公開しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを公開。主要サブパッケージとして data, ai, research 等を提供（パッケージレベルの __version__ = 0.1.0）。
- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - .env パーサーは `export KEY=val` 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（必須項目は明示的にエラーを投げる）。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。KABUSYS_ENV と LOG_LEVEL のバリデーションあり。
- AI: ニュース NLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集計して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）へ送ってセンチメント（ai_score）を算出。
  - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算するユーティリティを実装（UTC 変換対応）。
  - バッチ処理（最大 20 銘柄/1 API 呼び出し）・文字数トリム（銘柄当たり最大文字数）を実装。
  - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施し、失敗時は安全にスキップするフェイルセーフ。
  - レスポンスのバリデーション（JSON パース、results キー、型チェック、未知コードの無視、数値性検証）を実装。スコアは ±1.0 にクリップ。
  - ai_scores テーブルへの書き込みは冪等処理（DELETE → INSERT）を行い、部分失敗時に既存スコアを保護する実装。
  - テスト容易性のため _call_openai_api をパッチ差し替え可能（unittest.mock.patch を想定）。
- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）、レスポンスパース、リトライ／バックオフ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
  - 市場レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ参照、datetime.today() を参照しない）。
- データ基盤: カレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダーの取り扱いと営業日ロジックを実装（market_calendar テーブルを参照）。
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB にデータがない場合は曜日ベースのフォールバックを使用。
  - カレンダー夜間更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得し idempotent に保存。
  - 最大探索日数やバックフィル、健全性チェック（将来日付の異常検出）を実装。
- データ基盤: ETL / パイプライン (kabusys.data.pipeline / kabusys.data.etl)
  - ETLResult データクラスで ETL 実行結果を集約（取得数・保存数・品質問題・エラーの記録）。
  - 差分取得・バックフィル・品質チェックを前提としたパイプラインユーティリティ群を実装（DB の最終取得日取得ユーティリティ等）。
  - kabusys.data.etl で ETLResult を再エクスポート。
- リサーチ (kabusys.research)
  - ファクター計算 (calc_momentum, calc_value, calc_volatility) を実装（prices_daily / raw_financials 参照）。
  - 特徴量探索ユーティリティ (calc_forward_returns, calc_ic, factor_summary, rank) を実装。Spearman（ランク相関）による IC 計算、前方リターン・統計サマリー等。
  - zscore_normalize は kabusys.data.stats から再エクスポートする形で公開。
- ドキュメント化
  - 各モジュールに詳細な docstring を追加（処理フロー、設計方針、フェイルセーフの挙動、テストフックなど）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは環境変数（OPENAI_API_KEY）か関数引数で注入する設計で、ソースコードに埋め込まない方針。
- .env 読み込み時に既存 OS 環境変数を保護する仕組み（protected set）を実装。

---

注意事項（実装上の挙動や設計に関する重要メモ）
- ルックアヘッドバイアス防止: AI / リサーチ関連の処理は内部で datetime.today() / date.today() を直接参照せず、必ず外部から与えられた target_date を基準に処理します。
- OpenAI 呼び出しは現状 gpt-4o-mini と JSON Mode を前提に実装されています。レスポンスの堅牢なバリデーションとリトライロジックを持ちますが、モデルや SDK バージョンによる応答形式の変化には注意してください。
- DuckDB に対する executemany 呼び出しの空リスト扱いの挙動（互換性）を考慮した実装を行っています（空リスト時は呼ばないガードを挿入）。
- .env のパース実装は多くのケースに対応していますが、極端なケースのパース差異に注意してください。

以上。