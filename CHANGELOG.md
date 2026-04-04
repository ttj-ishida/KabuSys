# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
このファイルは、ソースコード（src/ 以下）から推測される機能追加・設計方針・不具合回避策等をベースに作成した変更履歴です。

## [Unreleased]
- ドキュメント・テスト・API 用意（将来のリリース向けに未実装の strategy/execution/monitoring の補完を予定）
- 追加予定:
  - strategy / execution / monitoring モジュールの実装公開
  - より詳細な運用ドキュメントとサンプル設定ファイル (.env.example 等)

## [0.1.0] - 2026-04-04
初期リリース — 日本株自動売買支援ライブラリ「KabuSys」のコア機能を実装。

### 追加
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開 API として data, strategy, execution, monitoring をエクスポート予定（現時点で data と research, ai 等のサブパッケージを実装）。
- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能（テスト向け）。
  - .env パーサを独自実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス /監視閾値 /環境（development/paper_trading/live）等の取得をプロパティ化。
  - 環境変数未設定時の明確なエラーメッセージ（_require）を採用。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を導入。

- AI 系 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI の Chat Completions（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント（ai_score）を算出。
    - タイムウィンドウ定義（JST 基準: 前日 15:00 ～ 当日 08:30）とそれを UTC naive datetime に変換する calc_news_window を公開。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたりの最新記事トリム（記事数・文字数で制限）。
    - レート制限・接続切断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - API 応答のバリデーションと復元処理（JSON mode でも前後余計なテキストが混ざる場合の復元）、不正レスポンスや失敗時はそのチャンクをスキップするフェイルセーフ設計。
    - DuckDB 互換性配慮（executemany に空リストを送らない等）および ai_scores テーブルへの冪等書き込み（DELETE → INSERT）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のみ使用してルックアヘッドを防止）。
    - マクロニュース抽出（タイトルベースでキーワードフィルタ）→ OpenAI に送信して macro_sentiment を得る。
    - OpenAI 呼び出しは独立実装、リトライ・例外処理を備え、API 失敗時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時はロールバックを試行。

- データ基盤・ETL (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブル）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。DB データを優先し、登録がない日は曜日ベースでフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理。バックフィル・健全性チェック（未来日付の異常検出）を導入。
  - pipeline / etl
    - ETLResult データクラスを実装し、ETL の各数値・品質問題・エラーを集約可能に。
    - ETL 設計方針: 差分取得、jquants_client を介した冪等保存、品質チェックを収集して呼び出し元へ返す（Fail-Fast ではなく全件収集）。
    - jquants_client 依存の差分フェッチ・保存フローを想定。
    - data.etl で pipeline.ETLResult を再エクスポート。

- research（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）などの定量ファクター実装。
    - DuckDB の SQL ウィンドウ関数を活用した実装で、prices_daily / raw_financials のみ参照。欠損・データ不足時の None 扱い。
  - 特徴量探索（feature_exploration）
    - 将来リターン calc_forward_returns（複数ホライズン対応、ホライズンバリデーションあり）。
    - Spearman ランク相関による IC 計算 calc_ic（ties を考慮したランク付け）。
    - ランク関数、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージは関連関数をトップレベルでエクスポート（zscore_normalize を含む）。

### 変更（設計上の決定／注意点）
- ルックアヘッドバイアス回避
  - score_news / score_regime / 各種ファクター計算は datetime.today()/date.today() を内部で参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ動作
  - LLM 呼び出しの失敗時は例外を投げずにスコアを 0.0 とする（regime_detector）や、チャンク単位でスキップして他チャンクに影響を与えない（news_nlp）。
- DB 書き込みの冪等性
  - market_regime / ai_scores 等は既存データを削除して再挿入する方式で冪等性を確保。部分失敗時に他コードの既存スコアを保護するため、書き込み対象コードを絞って DELETE → INSERT を実行。
- OpenAI 呼び出し
  - gpt-4o-mini を想定、JSON Mode（response_format={"type": "json_object"}）を利用。応答パースの堅牢化（例: 前後余計なテキストの除去）を行っている。
- DuckDB 互換性
  - executemany に空リストを渡すと失敗する環境を考慮し、事前に空チェックを行う実装にしている。
- 環境設定の優先順位と保護
  - OS 環境変数は .env による上書きを保護（protected set）する仕組みを導入。

### 修正（期待されるバグ回避）
- .env ファイル読み込みの失敗は警告ログを出して処理を継続（OSError ハンドリング）。
- OpenAI API 呼び出しに対してリトライ／ログ出力を実装し、致命的な外部API障害がシステム全体を停止させないようにしている。
- calendar_update_job の健全性チェックにより、異常に未来の last_date を検出した場合は更新をスキップして安全を確保。

### 既知の制約・留意点
- strategy / execution / monitoring の公開 API 名はパッケージトップで宣言されているが、今回のコードベースでは該当モジュールの実装が含まれていません。今後のリリースで追加予定。
- OpenAI に依存する機能は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）に依存。実行前に期待されるテーブル定義が存在する必要があります。

---

この CHANGELOG はコード内容からの推測に基づいて作成しています。実際の変更履歴やリリースノートとして利用する場合は、リポジトリ履歴（コミットログ）やリリース担当者による確認・追記を行ってください。