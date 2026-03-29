# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベースから推測できる機能追加・設計方針・修正点をまとめた初期リリースの変更履歴です。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

※ 日付はパッケージの __version__=0.1.0 に合わせて記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムのコアライブラリを実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポインタを追加: kabusys/__init__.py（data, strategy, execution, monitoring を公開）。
  - バージョン情報: __version__ = "0.1.0"。

- 設定/環境管理
  - 環境変数読み込み・設定管理モジュールを追加（kabusys.config）。
    - .env / .env.local の自動読み込み機能（優先順: OS環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - OS 環境変数を保護（上書き禁止）する protected 設定。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得可能:
    - J-Quants / kabu API / Slack / データベースパス（DUCKDB_PATH, SQLITE_PATH）等を扱う。
    - KABUSYS_ENV の検証（development/paper_trading/live）とログレベル検証（DEBUG/INFO/...）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（自然言語処理）
  - ニュース NLP スコアリングモジュール（kabusys.ai.news_nlp）を追加。
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）で一括評価。
    - チャンク処理（最大 20 銘柄/API 呼び出し）、1 銘柄あたりの記事枚数上限・文字数トリム制御。
    - JSON Mode を用いたレスポンス検証と頑健なパース処理（余分な前後テキストの復元処理含む）。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - スコア ±1.0 のクリップ、失敗時は該当チャンクをスキップして他の銘柄を保持。
    - ai_scores テーブルへの冪等的な置換（DELETE → INSERT）を実装。
    - テスト容易性のため内部 API 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。
  - マクロレジーム判定モジュール（kabusys.ai.regime_detector）を追加。
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - OpenAI（gpt-4o-mini）を利用したマクロセンチメント算出、API リトライ/フォールバック（失敗時 macro_sentiment = 0.0）。
    - レジームスコアの閾値設定（BULL/BEAR）および market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。ROLLBACK ハンドリングあり。
    - prices_daily のクエリでルックアヘッドを防止する設計。
  - kabusys.ai パッケージの公開 API: score_news, score_regime（news_nlp.score_news を news で公開）。

- データプラットフォーム（DuckDB ベース）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録がない場合は土日フォールバックを使用する一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）: jquants_client からの差分取得、バックフィル、健全性チェック、冪等保存。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、backfill、jquants_client による保存、品質チェックの収集を行う設計。
    - ETLResult dataclass を導入（target_date, fetched/saved counts, quality issues, errors 等を保持）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取引日調整。
  - ETL のインターフェース再エクスポート（kabusys.data.etl: ETLResult）。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Value（PER、ROE）等を計算する関数を実装。
    - DuckDB の prices_daily / raw_financials のみを参照し、外部 API にはアクセスしない設計。
    - データ不足時は None を返すことで堅牢に処理。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン）、IC（Spearman rank）計算、rank ユーティリティ、factor_summary の統計サマリー機能を提供。
    - 外部ライブラリに依存せずに標準ライブラリのみで実装。
  - research パッケージの公開 API を整理して再エクスポート。

### 変更 (Changed)
- 設計方針の明確化（ソースにコメント・ドキュメント追加）
  - ルックアヘッドバイアス防止のため、date.today()/datetime.today() をスコアリング関数内部で参照しない実装（すべて target_date を明示的に受け取る）。
  - DuckDB 互換性確保のため executemany の空リストバインドを避ける処理を追加。
  - OpenAI SDK のエラー型（status_code の有無）を考慮した堅牢なエラーハンドリング。

### 修正 (Fixed)
- フォールバック/フェイルセーフ実装
  - AI API の失敗（ネットワーク・5xx 等）をシステム全体の致命的失敗にしない（スコアを 0 でフォールバックする等）。
  - DuckDB 操作失敗時に ROLLBACK を試みるロジックを追加（ROLLBACK 失敗時は警告ログ出力）。
  - .env ファイル読み込み失敗時に警告を出して処理継続する仕様（例外を投げない）。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- 環境変数の必須チェックを明示（OpenAI API キー、Slack トークン、J-Quants リフレッシュトークン等）。未設定時は ValueError を発生させることで誤動作を防止。

---

開発・運用上の注記（実装からの推測）
- DuckDB を中心としたローカル分析・ETL を想定しており、本番環境でも同じ DB スキーマを利用可能な設計。
- OpenAI の呼び出しは JSON Mode（厳密な JSON 応答）を期待するが、実運用を想定して余計な前後テキストが混入した場合のリカバリ処理を備える。
- テスト容易性を考慮し、内部の API 呼び出し関数はテスト時に差し替え可能なよう設計されている（モック化を前提）。
- 日付/時間の扱いは timezone を排し naive datetime/date を採用し、JST/UTC の変換範囲が明示されている（ニュースウィンドウ等）。

もし必要であれば、各モジュール（ai/news_nlp, ai/regime_detector, data/pipeline, data/calendar_management, research/*）ごとにより詳細な変更点の分割や、将来のリリースノート用のテンプレート（Unreleased セクションの雛形）を作成します。どの粒度で記載するか指定してください。