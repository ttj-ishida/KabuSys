# Changelog

すべての変更は Keep a Changelog の慣例に従って記載します。  
このファイルはリポジトリ内のコード内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回公開リリース（推測）。以下の主要機能・モジュールを実装・公開しました。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。__version__ = 0.1.0、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定・環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - 複雑な .env のパース実装を追加（export 形式、クォート、エスケープ、インラインコメント処理）。
  - 環境変数必須チェック用の _require() と Settings クラスを実装。J-Quants / kabu / Slack / DB 等の設定をプロパティで提供。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利プロパティ（is_live / is_paper / is_dev）。
- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）でスコアを取得して ai_scores テーブルへ保存するパイプラインを実装。
    - バッチサイズ制御（最大 20 銘柄）、1 銘柄あたりの記事数・文字数上限、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
    - calc_news_window(target_date) による時間ウィンドウ定義（JST を基準に UTC に変換）を提供。
    - テスト容易化のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込む処理を実装。
    - マクロニュース抽出用のキーワードリストと LLM プロンプト、OpenAI 呼び出しのリトライ/フェイルセーフ設計。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で処理。API失敗時は macro_sentiment=0.0 にフォールバック。
- Research / ファクター計算（kabusys.research）
  - factor_research モジュールで以下ファクターを実装:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - Value: PER、ROE（raw_financials から取得）
    - Volatility / Liquidity: 20 日 ATR、20 日平均売買代金、出来高比率
    - 全関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し副作用なし（本番取引 API へアクセスしない）。
  - feature_exploration モジュールで以下を実装:
    - 将来リターン計算（calc_forward_returns）：複数ホライズン対応、入力バリデーション。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関の実装。
    - 統計サマリー（factor_summary）、rank ヘルパを実装。
  - research パッケージのエクスポートを整備（zscore_normalize 再利用など）。
- Data platform（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を基に営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得／バックフィル／保存処理（健全性チェックあり）を実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開し、差分取得・保存・品質チェックの結果を集約して返却するインターフェースを提供。
    - jquants_client、quality モジュールと連携する設計（API 呼び出しと品質チェックは分離）。
  - 複数ユーティリティ（テーブル存在チェックや日付関連ユーティリティ等）を実装。
- 外部統合の明示
  - OpenAI（OpenAI SDK）を利用する設計（API キーは引数で注入可能、未指定時は OPENAI_API_KEY を参照）。
  - J-Quants / kabu ステーション / Slack と連携する環境変数名を明示（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。
- ロギング・安全設計
  - 詳細なログ出力を適所に追加（info/warning/debug）。
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - API 呼び出し失敗時のフォールバック（LLM失敗→0.0、部分失敗時の DB 保護等）。
  - DuckDB と互換性のある安全な SQL バインディング・実行方法を採用。

### Changed
- （該当なし：初回リリースのため変更履歴は未適用）

### Fixed
- （該当なし：初回リリースのため修正履歴は未適用）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 機密情報（APIキー等）は環境変数で管理する設計。自動 .env ロードを無効化するオプションを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記（実装上の重要ポイント・運用上の注意）
- OpenAI 呼び出しは外部 API に依存するため、API キーの管理と利用制限に注意してください。
- DuckDB executemany に空リストを渡すと問題になるバージョン互換性問題への対処があるため、実行前に空チェックを行っています。
- calendar_update_job や ETL 処理は日次バッチ向けの設計で、バックフィルや健全性チェックを備えています。
- 単体テストや CI で .env の自動読み込みが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 本 CHANGELOG はコードからの推測に基づいて作成しています。実際のリリースノートはリポジトリ履歴やリリース時の決定に従って調整してください。