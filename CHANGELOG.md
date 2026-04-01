# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-01

初回リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ全体
  - パッケージバージョンを 0.1.0 として公開。
  - パッケージのトップレベル __all__ に data, strategy, execution, monitoring を定義（将来の拡張用）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 環境変数の優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - .env のパースは export 文やシングル／ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
    - 読み込み時に既存の OS 環境変数を保護する「protected」取り扱いを実装。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB / 監視 / システム周りの設定プロパティを定義し、必須キー未設定時は明示的なエラーを発生させる。
  - 設定値の検証: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...） の妥当性チェック。

- AI: ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を用いた銘柄別ニュース集約と LLM によるセンチメントスコアリング機能を実装。
  - gpt-4o-mini（OpenAI）を JSON Mode で呼び出し、以下をサポート:
    - タイムウィンドウ: 前日 15:00 JST から当日 08:30 JST（内部は UTC naive datetime）で対象記事を抽出。
    - バッチ処理: 最大 20 銘柄 / API コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出・構造検証・スコアの数値変換と ±1.0 クリップ。
    - 部分成功を許容する安全な DB 書き込み: 取得できたコードのみ DELETE → INSERT（トランザクション）で置換。DuckDB の executemany 制約に配慮。
  - フェイルセーフ設計: API・パースエラー時は例外を投げず該当チャンクをスキップし他銘柄の処理を継続する。

- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
  - 処理のポイント:
    - 1321 の ma200_ratio を DuckDB の prices_daily から計算（ルックアヘッドバイアス回避のため target_date 未満のデータのみ使用）。
    - マクロニュースは news_nlp.calc_news_window で定義したウィンドウから取得、マクロキーワードでフィルタ。
    - OpenAI 呼び出しは独立実装で、API 障害時は macro_sentiment = 0.0 にフォールバック（警告ログ）。
    - 合成スコアはクリップされ閾値によってラベル付与。market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - API キーの解決は引数優先、未指定なら環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルの存在チェック、営業日判定（is_trading_day）、前後の営業日探索(next_trading_day / prev_trading_day)、期間の営業日抽出(get_trading_days)、SQ 判定(is_sq_day) を実装。
    - DB にデータがない場合は土日ベースのフォールバックを使用。DB と曜日フォールバックの組合せでも一貫性を保つ設計。
    - 夜間バッチ job (calendar_update_job): J-Quants API から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックあり。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（対象日・取得数・保存数・品質問題・エラー一覧を保持）。
    - ETL の設計方針に基づく差分取得・バックフィル、保存、品質チェックのインターフェースを用意。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを実装（ETL 内部で利用）。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (research.factor_research)
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER / ROE）等を DuckDB の prices_daily / raw_financials を使って計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None の取り扱いや戻り値のフォーマットは明確化。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns)：任意ホライズンの将来リターンを一括取得する最適化 SQL を実装。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman（ランク相関）を直接実装、少数データの扱い（3 件未満は None）を定義。
    - ランク変換ユーティリティ (rank)：同順位は平均ランクで処理、丸めによる ties を防ぐ工夫あり。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を返すユーティリティを実装。
  - research パッケージは必要な関数群を __all__ で公開。

### 変更 (Changed)
- （初回リリースのため過去変更なし）

### 修正 (Fixed)
- （初回リリースのため過去修正なし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーやその他クリティカルな設定は Settings で必須にしており、未設定時は明示的エラーを発生させることで誤動作を抑止。
- .env 自動ロードでは OS 環境変数を「保護」し、意図しない上書きを防止する設計。

---

注:
- 全モジュールは DuckDB に依存しており、実行には対応するテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）の準備が必要です（ドキュメントや DataPlatform.md / StrategyModel.md に準拠）。
- AI 呼び出しロジックはテスト容易性のため内部の _call_openai_api をモック可能に設計しています。
- 実際の運用前に .env.example を基に .env を用意し、必要な環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。