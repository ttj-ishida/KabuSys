# CHANGELOG

すべての注目すべき変更を記録します。This project adheres to "Keep a Changelog" の形式と語彙を使用しています。  
※日付はリリース日（このコードベースが確認された日）を使用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ初期化:
  - kabusys パッケージの公開バージョンを設定（__version__ = "0.1.0"）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に追加。
- 設定管理:
  - 環境変数/.env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env ファイルのパースロジックを実装（'export ' プレフィックス対応、クォート文字列とエスケープ処理、行内コメントの扱い）。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数を保護する protected 機構、KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能）。
  - Settings クラスを提供し、各種必須/任意設定（J-Quants、kabuステーション、Slack、DBパス、環境/ログレベル）をプロパティ経由で取得・バリデーション。
  - KABUSYS_ENV、LOG_LEVEL の許容値チェックとヘルパー is_live/is_paper/is_dev を実装。
- AI（自然言語）:
  - kabusys.ai.news_nlp モジュールを実装:
    - raw_news と news_symbols に基づき、記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたり記事数・文字数制限、レスポンスのバリデーション、スコア ±1.0 クリップ、DuckDB の ai_scores テーブルへの冪等書き込み（DELETE → INSERT）。
    - リトライ（429、ネットワーク、タイムアウト、5xx に対する指数バックオフ）とフェイルセーフ（失敗時はスキップして継続）。
    - テストしやすさのため _call_openai_api をパッチ可能に設計。
    - calc_news_window ヘルパー関数（JST 時間窓 → UTC naive datetime）を実装。
  - kabusys.ai.regime_detector モジュールを実装:
    - ETF 1321（225 連動）200 日移動平均乖離とニュース由来マクロセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用）、マクロ記事フィルタリング、OpenAI 呼び出し、スコア合成と market_regime テーブルへの冪等書き込みを実装。
    - API キー解決、再試行、API エラー／パースエラー時の安全なフォールバック（macro_sentiment=0.0）。
- データ基盤（Data）:
  - calendar_management モジュールを実装:
    - market_calendar を基にした営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants からのカレンダー差分取得・夜間バッチ calendar_update_job 実装（バックフィル、健全性チェック、冪等保存）。
    - DB に登録がない日や NULL 値に対する曜日ベースのフォールバック（週末は非営業日扱い）。
  - pipeline / etl / ETLResult:
    - ETLResult データクラス（ETL の実行結果集約、品質チェック結果・エラーの記録、辞書化メソッド）を実装。
    - pipeline モジュールを通じた ETL ワークフローのためのユーティリティ（差分取得、backfill、品質チェックの集約方針を含意）。
  - jquants_client を利用する想定の設計（fetch/save 関数と連携する ETL 処理）。
  - DuckDB を主要なローカル分析 DB として利用する設計（パラメータバインド・executemany の注意点を考慮）。
- リサーチ機能:
  - research パッケージを実装:
    - ファクター計算: calc_momentum、calc_value、calc_volatility（prices_daily / raw_financials を参照し、各種ファクターを計算）。
    - 特徴量探索: calc_forward_returns（任意 horizon に対応）、calc_ic（Spearman ランク相関）、factor_summary（統計要約）、rank（同順位は平均ランク）。
    - zscore_normalize を data.stats から再エクスポート。
  - 全て DuckDB 接続を受け取り、外部 API / 本番発注ロジックに依存しない設計。
- ロギングと設計上の配慮:
  - 多くの箇所で詳細な logger 呼び出しを追加（INFO/DEBUG/WARNING/exception）。
  - ルックアヘッドバイアス回避のために datetime.today()/date.today() を直接参照しない設計（target_date を引数で指定）。
  - OpenAI レスポンスの堅牢なパース（JSON mode に対する余分なテキストの救済など）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の必須チェックを明示（必須トークンやパスワードが未設定の場合は ValueError を送出）し、誤った実行を抑止。
- OS 環境変数の上書きを意図せず防ぐための protected set を導入。

### 既知の制約 / 注意点 (Known limitations / Notes)
- OpenAI SDK の利用:
  - 実装は OpenAI の Chat Completions API（client.chat.completions.create）に依存。SDK の将来の変更により互換性修正が必要になる場合がある。
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY で提供する必要がある。
- DuckDB の互換性:
  - DuckDB の executemany が空リストを受け付けないバージョン（例: 0.10）を考慮して、空リスト時は呼び出しをスキップするガードを実装。
- テストしやすさ:
  - _call_openai_api をモック可能にしているが、実運用時は正しい API レスポンス仕様（JSON mode）を満たす必要あり。
- 一部機能は外部クライアント実装（jquants_client）に依存しており、環境側で fetch/save 実装の提供が必要。
- レスポンスのパース失敗時や API 上流エラー時は「失敗を全体に波及させずにスキップ」する方針のため、部分的に結果が欠けるケースが想定される（ログに詳細出力）。

### 移行メモ（ユーザー向け）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の設定を確認してください。
- .env/.env.local の自動読み込みはデフォルトで有効です。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB と OpenAI API の認証情報を正しく設定してから AI 関連関数（score_news, score_regime）を実行してください。

---

貢献者: 初期実装のコードベースに基づく自動生成の変更履歴（内容はコード注釈・実装に基づいて推測されています）。必要に応じて具体的な実装差分やドキュメント追加を行ってください。