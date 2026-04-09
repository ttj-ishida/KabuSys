# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従っています。  

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-09

初回公開リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群をまとめて実装しました。主な追加点と設計上の注意点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報とエクスポートを追加（kabusys.__init__）。
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - パッケージ配布後も動作するよう .git / pyproject.toml を基準にプロジェクトルートを探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env の行パーサ実装（export 形式、クォート/エスケープ、インラインコメント処理対応）。
  - protected オプションを用いた既存 OS 環境変数保護による上書き制御。
  - Settings クラスでアプリ設定をプロパティ提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL 等の取得。
    - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視設定（PID/KILL ファイルパス、閾値）を提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ユーティリティ。
    - is_live / is_paper / is_dev ヘルパー。

- データ関連（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定、次/前営業日取得、期間内営業日列挙、SQ日判定を実装。
    - market_calendar が未取得の際は曜日ベース（土日を非営業日）でフォールバックする一貫したロジック。
    - カレンダーの夜間更新ジョブ（calendar_update_job）を実装（J-Quants から差分取得 → 保存）。
    - バックフィル、先読み、健全性チェック（将来日付異常検出）を実装。
  - ETL パイプライン（pipeline）
    - 差分取得 → 保存 → 品質チェックの ETL フロー設計に対応するインターフェースと ETLResult dataclass を追加。
    - ETLResult に品質検出のまとめ、エラー判定 / 辞書化ユーティリティを実装。
  - etl の公開インターフェースを re-export（kabusys.data.etl → ETLResult）。

- 研究・因子（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン, 200日 MA 乖離を計算（データ不足時は None / 中立扱い）。
    - calc_volatility: 20日 ATR, 相対 ATR, 20日平均売買代金, 出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出。
    - DuckDB を用いた SQL + Python 実装（外部 API へはアクセスしない設計）。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ランク付け、統計サマリーを実装。
    - calc_forward_returns: 指定 horizon の将来リターン（複数ホライズン対応）。
    - calc_ic: factor と将来リターンのスピアマンランク相関を計算（有効レコードが 3 未満なら None）。
    - rank / factor_summary: ランク変換・統計要約ユーティリティ。

- AI / ニュース解析（kabusys.ai）
  - news_nlp: raw_news と news_symbols を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - チャンク単位バッチ（最大 20 銘柄）、1銘柄あたり記事数・文字数トリム制限。
    - JSON Mode 利用（厳密な JSON 出力想定）とレスポンス復元ロジック（前後テキスト混入時の {} 抽出）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフでのリトライ。
    - レスポンスバリデーション（results 配列、code の正規化、数値チェック、クリッピング）。
    - 部分失敗時に既存スコアを保護するため、取得済みコードのみ DELETE → INSERT（冪等性確保）。
    - テスト容易性のため _call_openai_api 等を差し替え可能。
  - regime_detector: ETF 1321（日経225連動型）200日 MA 乖離（重み 70%）とニュースベースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - ma200_ratio 計算、マクロキーワードでのタイトル抽出、LLM 呼び出し（gpt-4o-mini）、スコア合成、冪等書き込みを実装。
    - API 呼び出し失敗時は safe fallback（macro_sentiment = 0.0）で継続。
    - OpenAI 呼び出しは news_nlp とは独立実装（モジュール結合を避ける）。
    - 再試行・バックオフ処理、エラー種別に応じた挙動分岐を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security & Notes
- 環境変数管理
  - 機密値（API キー等）は環境変数経由で取得する設計。必須変数が未設定の場合は明確な ValueError を送出する箇所がある（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - .env 自動ロードはデフォルトで有効。CI/テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
  - .env 読み込み時に既存 OS 環境変数を保護する仕組みを実装（.env.local は上書き可能だが、OS 環境のキーは protected）。

- 外部依存
  - DuckDB を広く使用（prices_daily, raw_news, ai_scores, market_calendar, raw_financials など）。
  - OpenAI Python SDK の Chat Completions（gpt-4o-mini）を利用する前提。API レスポンスは JSON Mode を期待。

- フェイルセーフ設計
  - AI 呼び出しで致命的な失敗が起きても、処理全体が止まらない設計（多くの箇所でフォールバック値・ログ記録・部分スキップを採用）。
  - 日付周りは datetime.today()/date.today() を直接参照しない実装方針（ルックアヘッドバイアス防止）。外部から target_date を注入する設計。

### 既知の制約 / 注意点
- DuckDB の executemany に空リストを渡すとエラーになるバージョン（0.10 等）を考慮して、書き込み前に空チェックを実施。
- OpenAI からのレスポンスが完全な JSON でないケースに備えた復元処理は実装済みだが、長期的にはより堅牢な入出力仕様（プロンプト設計・検証強化）が望ましい。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存するため、実稼働前に API クレデンシャルとクライアント実装を用意してください。

---

詳細な使用法、環境設定例 (.env.example)、および各モジュールの API（関数名・引数・返り値）についてはドキュメントとソースコードの docstring を参照してください。