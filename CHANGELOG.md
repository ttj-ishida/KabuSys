# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
日本語での要約はコードベース（src/kabusys 以下）の内容から推測して作成しています。

## [0.1.0] - 2026-04-01 (初回リリース)

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__）。バージョンを "0.1.0" に設定。
  - 公開モジュール群のエクスポート: data, strategy, execution, monitoring。

- 環境・設定管理
  - 環境変数自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env / .env.local を読み込む。
    - .env のパースは export KEY=val 形式、クォートやエスケープ、コメント処理に対応。
    - OS 環境変数を保護する protected 機構を導入し、.env.local による上書きや override を制御。
    - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得可能に：
    - J-Quants / kabu ステーション / Slack / データベースパス（duckdb/sqlite） / 監視閾値 / ログレベル / 実行環境判定など。
    - 必須項目を取得する際は未設定時に ValueError を送出する _require を実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値は定義済み）。

- AI（自然言語処理）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news, news_symbols を集約して銘柄ごとにニュースを統合し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出。
    - バッチ処理（1 API コールあたり最大 20 銘柄）・記事数/文字数トリム・JSON レスポンス検証・スコアのクリップ実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ、失敗時は部分スキップしてフェイルセーフで継続。
    - テスト用に内部の _call_openai_api を差し替え可能（unittest.mock.patch の想定）。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST ベース -> UTC naive datetime）。
    - 成果を ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込む処理を実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュース由来の LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - prices_daily, raw_news を参照し、OpenAI を呼んで macro_sentiment を取得。API エラー時は macro_sentiment=0.0 として継続。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しは独立実装で、news_nlp と内部関数を共有しない設計（モジュール結合を避ける）。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理（calendar_management）
    - JPX カレンダー取得・保存のための calendar_update_job を実装（J-Quants client 想定）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定ユーティリティを実装。DB データがない場合は曜日（週末除外）でフォールバック。
    - 市場カレンダーに対する健全性チェック、バックフィル、最大探索日数制限を導入。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を構造化して返却可能に。
    - 差分更新・バックフィル・品質チェックの設計を文書化（jquants_client 経由で差分取得、save_* による冪等保存、quality モジュールによるチェック）。
    - pipeline モジュールの ETLResult を data.etl から再エクスポート。
  - jquants_client と quality モジュールを想定した設計で、API 呼び出し・保存処理を抽象化。

- リサーチ機能（kabusys.research）
  - factor_research: ファクター計算を実装（prices_daily / raw_financials を利用）。
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - ボラティリティ/流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - バリュー: PER（EPS が無効な場合は None）、ROE（raw_financials から取得）。
    - DuckDB 上で集約 SQL を使用し、(date, code) ベースの結果を返す。
  - feature_exploration: 将来リターン計算（複数ホライズンの fwd_Nd）、IC（Spearman）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - calc_forward_returns は複数 horizon を受け取り、同一クエリでリードを取得する実装。
    - calc_ic はランク相関（Spearman）を実装し、データ不足（有効レコード < 3）時は None。
    - rank と factor_summary を提供（外部依存なしで標準ライブラリのみで実装）。
  - data.stats の zscore_normalize を再エクスポート。

### 変更 (Changed)
- 設計上のポリシーを明確化
  - 機械学習・シグナル算出部分でのルックアヘッドバイアス排除を明記（datetime.today()/date.today() を直接参照しない設計。target_date を明示的引数として受け取る）。
  - OpenAI API 呼び出しに対して堅牢なエラーハンドリングとリトライ戦略を適用（news_nlp, regime_detector）。

### 修正 (Fixed)
- API/外部呼び出し失敗時のフェイルセーフ
  - LLM 呼び出し失敗時に処理を中断させずゼロ値やスキップで継続するためのログ出力とフォールバック実装を多く導入（_score_macro, _score_chunk 等）。
- DuckDB の executemany の制約を考慮して、空リスト渡しによる問題を回避（空時は executemany 呼び出しをスキップ）。

### 既知の問題 (Known issues / Notes)
- pipeline._get_max_date の末尾にファイル切れと思われる不完全なコード断片 ("return date.fro") が見られます。実装漏れ／タイポの可能性があるため、ETL の該当関数を実行する前に確認・修正が必要です。
- 一部の機能は jquants_client / quality / jquants の実装に依存しており、外部クライアント実装が必要（モックでのテストが推奨される）。
- OpenAI API を利用する機能は環境変数 OPENAI_API_KEY の設定が必須。テスト時は内部の _call_openai_api を差し替えることで外部呼び出しを回避可能。

### セキュリティ (Security)
- 機密情報（API トークン等）は Settings 経由で環境変数から取得し、.env ファイル読み込み時にも OS 環境変数を保護する仕組みを導入。自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）あり。

---

将来的な改善案（推奨）
- pipeline モジュールの未完部分修正とユニットテスト追加。
- jquants_client の具体的実装に対する統合テストと、AI 呼び出し部分のエンドツーエンドテスト（レート制限やタイムアウトを想定）。
- エラーメトリクス収集（Sentry 等）や、より細かい observability（監視アラート）の追加。

（以上）