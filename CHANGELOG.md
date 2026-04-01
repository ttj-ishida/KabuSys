# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重要度別に分類しています。日付はこのリリースが作成された日付です。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-01
初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。

### Added
- パッケージ基盤
  - パッケージメタ情報を公開 (kabusys.__init__): バージョン "0.1.0"、主要サブパッケージを __all__ に設定。

- 環境設定
  - 環境変数/_env ファイル自動ロード機能を実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export KEY=val、クォート、バックスラッシュエスケープ、インラインコメント等のパースに対応。
    - 読み込み時に OS 環境変数を保護する protected 機能をサポート。
  - Settings クラスによる型付き設定アクセスを追加:
    - J-Quants / kabu API / Slack / データベースパス (DuckDB/SQLite) / 監視閾値 / ログレベル / 環境 (development/paper_trading/live) 等のプロパティ。
    - 必須変数未設定時に明確なエラーメッセージを投げる _require を提供。
    - env / log_level のバリデーション実装。

- データプラットフォーム
  - ETL インターフェース (kabusys.data.pipeline, ETLResult) を実装。
    - ETLResult: ETL の取得・保存件数、品質チェック結果、エラーを表現するデータクラスとユーティリティ。
  - calendar_management:
    - JPX マーケットカレンダー管理ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job: J-Quants から差分取得して market_calendar に冪等保存するバッチ処理を実装。
    - DB が未取得/不完全な場合の曜日ベースのフォールバック、バックフィル、健全性チェックを導入。

- AI（自然言語処理）モジュール
  - ニュース NLP スコアリング (kabusys.ai.news_nlp) を実装:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini + JSON Mode) にバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（JST: 前日15:00～当日08:30）、1銘柄最大記事数・文字数トリム、バッチサイズ、リトライ（429/ネットワーク/5xx）を実装。
    - レスポンスの厳密バリデーションとスコア ±1.0 のクリップを実装。
    - スコアを ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込む処理を実装。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch する設計）。
  - 市場レジーム判定 (kabusys.ai.regime_detector) を実装:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせ、日次で regime_label（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロニュースはキーワードフィルタで抽出。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを取得、複数回リトライとバックオフを実装。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）する処理を実装。
    - API 失敗時は安全に macro_sentiment=0.0 を採用するフェイルセーフを導入。

- リサーチ / ファクター
  - kabusys.research モジュールを実装（factor_research, feature_exploration, zscore_normalize の再利用）。
  - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算する SQL ベースの実装。
  - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比を計算。
  - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が無効な場合は None）。
  - calc_forward_returns: 将来リターン（翌日・翌週・翌月等）をまとめて取得する可変ホライズン対応実装。
  - calc_ic: Spearman ランク相関（IC）を実装。データ不足時の保護（3 件未満は None）。
  - rank / factor_summary: 平均ランク処理、基本統計量（count/mean/std/min/max/median）を実装。
  - すべて DuckDB 接続を受け取り、外部 API 呼び出しを行わない設計（安全なリサーチ環境）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーはメソッド引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を明示的に発生させることで誤利用を防止。

### Design / Implementation Notes
- ルックアヘッドバイアス対策:
  - AI とリサーチの各処理は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date を基準に排他条件（date < target_date など）を適用。
- テスト容易性:
  - OpenAI 呼び出し関数をモジュール内で独立実装し、テスト時に patch して差し替えられるように実装。
  - .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- DB 書き込みの冪等性とトランザクション制御:
  - market_regime / ai_scores への書き込みは削除→挿入の形で置換し、BEGIN/COMMIT/ROLLBACK を利用して失敗時に既存データ保護とロールバックを行う。
  - DuckDB の executemany に関する互換性（空リスト不可等）に配慮した実装を行っている。
- ロギング:
  - 各主要処理で情報ログ・警告ログを出力し、失敗時のフォールバック（0.0や空結果）をログで明示。

---

今後の予定（例）
- モデルやプロンプトの改良による AI スコア精度向上
- ETL の自動スケジューリング実装（ジョブランナー統合）
- 監視 / 実行 (execution / monitoring) サブパッケージの実装・強化
- テストカバレッジの拡充（ユニット/統合テスト）

もし CHANGELOG に追記して欲しい観点（例: もっと詳細な技術的ポイント、該当ファイルごとの差分要約、将来のマイルストーン等）があれば教えてください。