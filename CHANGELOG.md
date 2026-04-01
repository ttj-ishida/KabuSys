# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」慣例に準拠しています。  
なお、記載内容は提供されたソースコードから推測した実装および設計意図に基づき作成しています。

※ 日付はリリース想定日（このコードベースのスナップショット日）として 2026-04-01 を付与しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回公開リリース。以下の主要機能・モジュールを追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン: 0.1.0

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式やクォート/エスケープ、インラインコメントの扱いに対応するパーサを提供。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数の保護（保護されたキーは上書きしない）を考慮した読み込みロジック。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供。J-Quants / kabuステーション / Slack / DBパス /監視パラメータ / ログレベル / 環境種別（development, paper_trading, live）等の設定プロパティを公開。
  - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、しきい値等）を定義。

- データプラットフォーム関連（src/kabusys/data/*）
  - マーケットカレンダー管理（calendar_management.py）
    - JPX カレンダー管理ロジック（market_calendar テーブル参照/フォールバック、next/prev/get_trading_days、is_sq_day 等）。
    - 夜間バッチ job（calendar_update_job）: J-Quants API から差分取得し冪等保存、バックフィル・健全性チェック実装。
    - DB が未取得の際は曜日ベース（週末除外）でフォールバックする堅牢な動作。
  - ETL パイプライン基盤（pipeline.py / etl.py）
    - ETLResult データクラス（取得/保存件数・品質問題・エラーの集約）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールとの連携）。
    - DuckDB を使ったテーブル存在チェックや最大日付取得等のユーティリティ関数を実装（差分取得ロジック基盤）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究（Research）モジュール（src/kabusys/research/*）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR）、Value（PER, ROE）等の定量ファクター計算機能を提供。
    - DuckDB のウィンドウ関数を活用して効率的に集計。
    - データ不足時は None を返す等、欠損取り扱いあり。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（Spearman ランク相関）とランク変換ユーティリティ。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - research パッケージ初期化で上記関数をエクスポート（zscore_normalize は data.stats から再利用）。

- AI 関連（src/kabusys/ai/*）
  - news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI Chat Completions（gpt-4o-mini）を使って銘柄ごとのセンチメント（ai_score）を取得、ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/チャンク）、トリミング（記事数/文字数制限）、JSON Mode を用いた厳密なレスポンス期待。
    - レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。失敗はログを残してスキップ（フェイルセーフ）。
    - レスポンスのバリデーションと ±1.0 クリップ処理を実装。
    - calc_news_window で JST 時間ウィンドウ（前日15:00〜当日08:30）を UTC naive datetime に変換。
  - regime_detector.py
    - ETF（1321）200日MA 乖離（70%）とマクロ経済ニュースの LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロキーワードフィルタで raw_news からタイトル抽出、OpenAI を用いたマクロセンチメントスコア取得（JSON パース、リトライ、フォールバック）。
    - lookahead バイアス防止のため日付比較は target_date 未満の排他条件を使用。
  - ai パッケージ初期化で score_news をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の扱い:
  - 自動ロード時に OS 環境変数は保護され、.env の値で勝手に上書きされないよう配慮。
  - OpenAI API キーは明示的に api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定で呼び出すと ValueError を送出して明確に失敗する。

### Notes / 設計方針（重要）
- ルックアヘッドバイアス対策:
  - AI スコアやレジーム判定、ファクター計算などは内部で datetime.today() / date.today() を直接参照しない設計。すべて target_date を明示的に渡す設計。
- DuckDB 互換性:
  - executemany に空リストを渡せない DuckDB の制約に配慮した実装（空チェックの上で executemany を呼ぶ）。
  - 一部 SQL で ROW_NUMBER / WINDOW 関数を多用しており、高速集計を意図。
- 冪等性:
  - market_regime / ai_scores 等、DB 書き込みは既存行を削除してから挿入することで冪等性を確保（BEGIN / DELETE / INSERT / COMMIT のパターン）。
- フェイルセーフ:
  - 外部 API 呼び出し（OpenAI, J-Quants）で失敗した場合は可能な限りスキップして処理を継続し、致命的ではない限り例外を上位に伝播しない設計（ただし、DB 書き込み失敗は例外を伝播）。

### Known issues / TODO（ソースコードから判明）
- src/kabusys/data/pipeline.py の末尾に不完全な実装の断片（`return date.fro` のような誤記/途中で切れた行）があり、現状そのままではモジュールのインポートで構文エラー/例外が発生する可能性があります。リリース前に以下を確認・修正する必要があります:
  - _get_max_date の戻り値処理が途中で切れている（typo / 不完全）。
  - pipeline モジュール全体の続き（差分取得や save 呼び出し等）が未完または切断されている可能性。
- OpenAI に依存する箇所は実稼働でのコストやレイテンシ、レスポンス形式の変動に影響を受けます。JSON パース回りは冗長に保護されているが、モデル側の挙動変化による追加対応が必要になる場合があります。
- news_nlp と regime_detector はそれぞれ独自に _call_openai_api を実装しており、意図的に共通化を避けている。このため差分テスト時は別々にモックパッチが必要。
- デフォルトの DB パス（data/kabusys.duckdb 等）はプロジェクト内の相対パスを使うため、本番配置や Docker 環境ではパスの見直しが必要。

---

開発者向け補足:
- 自動環境読み込みはプロジェクトルート検出に __file__ を基点にしているため、パッケージ配布後もカレントワーキングディレクトリに依存せず動作する想定です。ただしパッケージ化・展開時のファイル配置に依存するため、CI/デプロイ設定で .env の配置方法を明確にしてください。
- OpenAI を用いる部分は unit テストで _call_openai_api をモックしやすいように分離されています。

（以上）