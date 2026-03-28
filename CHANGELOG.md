# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣例に従います。  

※ 日付はパッケージの初期リリース日を示します。将来の変更は Unreleased セクションに追加してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。パッケージは data / research / ai / monitoring / execution / strategy などのサブモジュールを想定。
- 環境変数・設定管理 (kabusys.config)
  - プロジェクトルートの自動検出機能 (.git または pyproject.toml を基準) を追加。
  - .env / .env.local ファイルの自動読み込み機能を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - export KEY=val 形式への対応、シングル/ダブルクォートでのエスケープ処理、コメント行や行内コメントの適切な処理を備えた .env パーサを実装。
  - 環境変数の保護機能（読み込み時に既存 OS 環境変数を protected として上書きを制御）。
  - Settings クラスを追加し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）など主要設定値をプロパティで取得可能に。
  - 無効な KABUSYS_ENV / LOG_LEVEL の検証とエラー報告機能を追加。
- AI 関連 (kabusys.ai)
  - ニュースNLP (news_nlp)
    - raw_news / news_symbols を元に、銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini, JSON Mode）でセンチメント（-1.0〜1.0）を評価。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数制限 (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK) によるトークン肥大化対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライと、応答の堅牢なバリデーション（JSON 抽出、results フォーマット検証、コードフィルタ、数値検証、±1 でクリップ）を実装。
    - 書き込み処理は部分失敗対策として対象コードのみ DELETE → INSERT（冪等）する実装。
    - テスト容易性のため _call_openai_api の置き換えポイントを提供。
    - calc_news_window ユーティリティを追加（JST 基準のニュース収集ウィンドウ計算）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（Nikkei 連動）の 200 日移動平均乖離（70% 重み）と、マクロニュース LLM センチメント（30% 重み）を組み合わせて日次で market_regime を判定・保存。
    - DuckDB クエリはルックアヘッドを防ぐ条件（date < target_date）で実行。
    - LLM 呼び出しはリトライ・バックオフ・5xx ハンドリングを備え、失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - market_regime への書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理で実装。
    - テスト用の API 呼び出し差し替えポイントを提供（_call_openai_api）。
- データプラットフォーム (kabusys.data)
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を公開し、ETL 実行結果（取得数・保存数・品質チェック・エラー）を集約・辞書化可能に。
    - 差分取得・バックフィル・品質チェック（quality モジュールとの連携）を想定した設計。
  - カレンダー管理（calendar_management）
    - JPX 市場カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・保存）。
    - market_calendar が未取得の場合の曜日ベースのフォールバック（週末除外）を実装し、次/前営業日・期間内営業日・SQ 判定の関数群を提供。
    - カレンダー更新に関するバックフィル・健全性チェック（最大未来日数など）を実装。
- リサーチ・分析 (kabusys.research)
  - ファクター計算（factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - Value: PER / ROE（raw_financials から最新レコードを取得して計算）。
    - 各関数は DuckDB を用いた SQL 実装で、date と code をキーとする dict リストを返す設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（スピアマンランク相関）calc_ic。
    - 値をランクに変換する rank ユーティリティ（同順位は平均ランク）。
    - factor_summary による基本統計（count/mean/std/min/max/median）計算。
- 汎用再エクスポート
  - data.etl にて pipeline.ETLResult を再エクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の制約 (Notes)
- OpenAI API
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を使用します。api_key を引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を発生させます。
- DB スキーマ依存
  - 多くの機能は DuckDB 上の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar 等）を前提としています。これらのスキーマが存在しない場合は例外や 0 件扱いになります。
- ルックアヘッド対策
  - すべての時間関連ロジックは内部で datetime.today()/date.today() を参照しないか、明確に target_date を受け取る実装になっており、ルックアヘッドバイアス低減に配慮しています。
- テスト容易性
  - OpenAI 呼び出し部分はモジュール内で置き換え可能な関数を用意しており、ユニットテスト時にモック差し替えが可能です。
- .env パーサ
  - 複雑な .env のユースケース（特殊なエスケープや複雑なシェル展開）では差異が生じる可能性があります。基本的な export/quoted/value#comment のパターンに対応しています。

### セキュリティ (Security)
- 環境変数の自動ロードはデフォルトで有効ですが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能です。自動ロード時、既存 OS 環境変数は保護され、.env.local は .env を上書きする優先度を持ちます。

---

今後のリリースでは、実運用を想定した監視・実行（execution / monitoring）や追加ファクター・最適化ロジック、より詳細な品質チェックおよび CI 用のテストカバレッジ強化などを予定しています。