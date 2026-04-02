# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
この CHANGELOG は提供されたコードベースの内容から機能・設計意図を推測して作成しています。

フォーマット:
- すべてのリリースは年月日付きで記載
- セクションは Added / Changed / Fixed / Security を基本とする

## [0.1.0] - 2026-04-02
最初の公開リリース（コードベースから推測）。日本株自動売買プラットフォーム "KabuSys" のコアライブラリを実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = "0.1.0"）と公開モジュール定義。
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env ファイルの堅牢なパーサー実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応）。
  - 環境変数必須チェック関数 _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等のプロパティ含む）。
  - KABUSYS_ENV、LOG_LEVEL の入力検証（有効値制約）および便利プロパティ（is_live / is_paper / is_dev）。
  - デフォルトのデータベースパス（DUCKDB_PATH / SQLITE_PATH）や監視閾値（CPU/MEM/DISK）等の設定プロパティを実装。
- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini / JSON mode）でセンチメントをスコアリングして ai_scores テーブルへ保存する処理を実装。
    - 記事の時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応。UTC へ変換）を提供。
    - バッチ処理（最大 20 銘柄チャンク）、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - API 呼び出しのリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。失敗はフェイルセーフでスキップ。
    - レスポンス検証機構を実装（JSON 抽出・results キー検証・コード整合性・数値チェック・スコアクリップ）。
    - DuckDB に対して冪等に DELETE → INSERT でスコア置換（部分失敗時に既存データを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で market_regime を作成。
    - マクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini / JSON mode）、API 再試行、JSON パースの堅牢化を実装。
    - API 失敗時は macro_sentiment = 0.0 でフォールバック。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作、失敗時は ROLLBACK を試行して例外を伝播。
- データ基盤（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを基に営業日判定 / 次営業日 / 前営業日 / 期間内営業日取得 / SQ日判定を提供。
    - DB にカレンダーがない場合は曜日（土日）ベースのフォールバックを用いる設計。
    - カレンダー更新バッチ（calendar_update_job）を実装（J-Quants API 経由で差分取得、バックフィル、健全性チェック）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラー一覧等）。
    - 差分更新、バックフィル、品質チェックを行うためのユーティリティを実装（jquants_client と quality モジュールに依存）。
  - ETL 公開インターフェース（etl.py）で ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、平均売買代金、出来高比率、バリュー（PER, ROE）などの計算ルーチンを実装。DuckDB 上で SQL と Python を組み合わせて計算。
    - データ不足時の None ハンドリングやログを実装。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク変換（同順位の平均ランク処理）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。
- テスト・運用を意識した設計
  - 外部 API 呼び出し箇所は差し替え可能（ユニットテストで patch できるフックを用意）。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() の乱用を避け、明示的な target_date 引数で処理を行う設計。

### Changed
- 初期リリースのため特別な変更履歴はなし（初回導入）。

### Fixed
- 初期リリースのため特別な修正履歴はなし。

### Security
- 現時点で公開されているコードから明示的なセキュリティ修正はないが、OpenAI API キーや外部トークンは必須環境変数として扱い、.env 自動読み込みは無効化可能（運用環境での誤設定緩和用）。

---

注記（推測）
- 一部関数・モジュールは jquants_client や quality 等の外部モジュールを前提にしており、その実装に依存します。ETL や calendar_update_job 等は外部 API 呼び出しの健全性に依存するため、運用時に API レートや認証設定の確認が必要です。
- OpenAI 呼び出し部分は gpt-4o-mini と JSON mode を想定しているため、モデル・レスポンス仕様が変わった場合は検証が必要です。
- DuckDB に対する executemany の扱いや list 型バインドの互換性に配慮した実装がなされています（互換性対策やバージョン差異への注意）。

（この CHANGELOG はコードベースからの推測に基づくため、実際のコミット履歴や意図と差異がある可能性があります。）