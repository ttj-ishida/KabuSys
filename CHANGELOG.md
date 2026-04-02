Keep a Changelog 準拠の CHANGELOG.md

すべての変更は semver に従います。未記載の変更は互換性のない変更（Breaking Changes）として扱います。

## [0.1.0] - 2026-04-02
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージの基本情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py にて設定）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境変数／設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード無効化対応。
  - .env パーサを実装（コメント、export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理を考慮）。
  - Settings クラスを実装して各種設定値をプロパティ経由で取得可能に:
    - J-Quants / kabu API / Slack トークン類（必須チェックあり）
    - DB パス（DuckDB / SQLite）、監視用閾値（CPU/Memory/Disk）
    - 環境 (development/paper_trading/live) とログレベルの検証
    - is_live / is_paper / is_dev ヘルパー
  - 必須設定未定義時は分かりやすい ValueError を送出。

- AI（LLM）モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数制限、JSON Mode の利用。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ実装。
    - レスポンス検証（JSON 抽出、results リスト、code/score の検証、数値の有限性、スコアの ±1.0 クリップ）。
    - スコア取得後は ai_scores テーブルに対して部分置換（DELETE → INSERT）を行い、部分失敗時に既存データを保護。
    - テスト容易化のため _call_openai_api の差し替えが可能。
    - ニュース集計ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC では前日 06:00 ～ 23:30）を利用。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio 計算（target_date 未満データのみ使用してルックアヘッドを防止）、マクロニュース取得、OpenAI 呼び出し（gpt-4o-mini、JSON mode）による macro_sentiment 評価、スコア合成、閾値判定、market_regime へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - OpenAI 呼び出しは専用の内部実装を用い、news_nlp と直接結合しない設計。

- データプラットフォーム（DuckDB ベース）モジュール (src/kabusys/data)
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー概要等を含む）。
    - 差分更新／バックフィル／品質チェック等の設計を実装。J-Quants クライアント（jquants_client）を利用する前提。
    - DuckDB テーブル存在確認ユーティリティ、最大日付取得などの内部ユーティリティを用意。
    - ETL 実行結果の辞書化（品質問題を dict に変換）機能を提供。

  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB の登録値優先、未登録日は曜日ベースのフォールバックを採用（データがまばらでも一貫した動作）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）や健康性チェック（未来日付の異常検知）、バックフィルロジックを搭載。
    - calendar_update_job を実装し、J-Quants API から差分取得して冪等保存（fetch/save の例外はログ化して 0 を返す）。

- 研究用モジュール (src/kabusys/research)
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）および Value（PER、ROE）ファクターを DuckDB 上で SQL と Python を組み合わせて計算。
    - データ不足時の None ハンドリング、ログ出力を実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装（テスト容易性・軽量設計）。
  - data.stats の zscore_normalize を再エクスポート（research パッケージ経由）。

- 共通設計上の注意点（各所で一貫）
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を直接参照せず、関数の引数として target_date を受け取る設計を採用している箇所が複数存在。
  - DuckDB を主要ストレージとして利用し、SQL ウィンドウ関数や executemany の互換性を考慮した実装を行っている。
  - DB 書き込みは基本的に冪等化（DELETE→INSERT や ON CONFLICT による上書き）を意識している。
  - OpenAI 呼び出し部分は JSON mode（response_format）を用いて厳密な JSON 出力を期待し、パース失敗時には安全にフォールバックする実装。

### 変更 (Changed)
- 初回リリースのため変更履歴はなし。

### 修正 (Fixed)
- 初回リリースのため修正履歴はなし。

### 既知の制限 / 注意点
- src/kabusys/data/__init__.py は現状空（将来的に jquants_client 等を再エクスポートする想定）。
- 一部の外部依存（OpenAI / jquants_client / duckdb）の具体的な設定・テスト用フックは実装されているが、実行環境での API キーや DB スキーマ準備は別途必要。
- news_nlp と regime_detector は OpenAI へのアクセスを行うため、API キー未設定時は ValueError を送出する点に注意。
- ETL・カレンダー更新・AI スコアリングはログ出力・例外処理で失敗をサイレントに継続する設計（フェイルセーフ）だが、呼び出し元での結果確認（ETLResult 等）を推奨。

---

今後の予定（例）
- strategy／execution モジュールの戦略実行フローと発注ロジックの実装（現状パッケージ公開名のみ）。
- 監視（monitoring）モジュールの実装と pid/log/リソース閾値を使った自動再起動・Slack 通知等の追加。
- テストカバレッジ強化と CI 設定（OpenAI 呼び出しのモック化を前提）。