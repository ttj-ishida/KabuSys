# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
このファイルは主にコードベースから推測した初期リリースの変更点をまとめたものです。

注: リリース日・カテゴリはコード内容から推測しています。実際のリリース運用に応じて適宜編集してください。

## [Unreleased]

- 今後の変更点をここに記載します。

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）
  - エクスポート: data, strategy, execution, monitoring

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルートは .git / pyproject.toml を基準に探索）
  - 読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーは quoted 値（シングル/ダブルクォート）、エスケープ、export プレフィックス、コメントの挿入規則に対応
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev のブールヘルパー

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）を用いセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を実装
    - 処理のポイント:
      - JST 時間ウィンドウ（前日15:00〜当日08:30）を UTC に変換して DB クエリを実行
      - 1 銘柄あたり記事数と文字数の上限（トリム）によるトークン肥大対策
      - バッチ送信（最大 20 銘柄 / チャンク）とレスポンスバリデーション
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ
      - レスポンスは JSON Mode を想定し、余計な前後テキスト混入時の復元ロジックを実装
      - 規格外レスポンスや API 失敗時は安全にスキップし、部分成功時は該当銘柄のみ置換（DELETE → INSERT）することで既存データを保護
    - テスト容易性: OpenAI 呼び出し箇所をユニットテストで差し替え可能に設計（_call_openai_api を patch 可）

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装
    - 処理のポイント:
      - prices_daily / raw_news からのデータ抽出はルックアヘッドを防ぐ条件（date < target_date 等）を厳密に指定
      - OpenAI（gpt-4o-mini）への呼び出しは JSON レスポンスをパース、エラー時は macro_sentiment=0.0 としてフェイルセーフに継続
      - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK を試行して例外を上位へ伝搬
      - API 呼び出しはテストで差し替え可能（_call_openai_api を patch 可）

- データモジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を基に営業日判定・次/前営業日の算出・期間内営業日リスト取得・SQ日判定のユーティリティを実装
    - DB 登録がない日については曜日ベース（土日除外）でフォールバック
    - calendar_update_job により J-Quants API からの差分取得・バックフィル・保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を実装
    - 健全性チェック（未来日が極端に先の場合はスキップ）、バックフィル期間の再取得などの安全措置を実装

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約
    - 差分更新・バックフィル・品質チェック（quality モジュール想定）・idempotent な保存フローを設計
    - デフォルト設定（最小データ日、カレンダー先読み、デフォルト backfill 日数）を定義
    - data.etl で ETLResult を再エクスポート

- リサーチ（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）等のファクター計算を実装
    - DuckDB の SQL とウィンドウ関数を組み合わせて効率的に計算
    - データ不足時（必要行数未満）は None を返す設計
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターンの計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを実装
    - pandas 等外部依存なしで標準ライブラリのみで完結する設計
  - research パッケージ __all__ に主要関数をエクスポート（zscore_normalize は data.stats から再利用）

- 共通設計方針・品質面
  - DuckDB を主要なローカル DB として使用
  - ルックアヘッドバイアスを防止するために datetime.today()/date.today() への直接依存を避け、全ての判定は明示的な target_date 引数に基づく
  - OpenAI API 呼び出しや外部 API 呼び出しはリトライ・バックオフ・フェイルセーフ（失敗時ゼロやスキップ）で堅牢化
  - DB への書き込みはトランザクションで冪等性（DELETE→INSERT 等）を確保し、失敗時は ROLLBACK を行う
  - テスト容易性を考慮した差し替えポイント（_call_openai_api の patch 等）を用意

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 機密情報（API キー等）は Settings 経由で環境変数から取得する仕様。必須キーが未設定の際は ValueError を送出して早期発見を促す。

### Notes / Migration
- 必要環境変数（主なもの）:
  - OPENAI_API_KEY（AI 機能利用時）
  - JQUANTS_REFRESH_TOKEN（J-Quants 経由のデータ取得）
  - KABU_API_PASSWORD, KABU_API_BASE_URL（kabu ステーション API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
  - DUCKDB_PATH / SQLITE_PATH（データ保存先の上書き）
- .env の自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードすることを推奨
- OpenAI の呼び出しは gpt-4o-mini を想定、JSON Mode を利用するためレスポンス検証ロジックが組み込まれている。API 仕様変更がある場合はパース・リトライの挙動を見直す必要あり

---

貢献者・詳細な設計ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づく実装が数箇所に言及されています。実運用時はそれらのドキュメントと合わせて参照してください。