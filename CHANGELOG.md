# Changelog

すべての注記は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠します。  
このファイルは、ソースコードの内容から推測して作成した初期の変更履歴です。

## [Unreleased]
- 開発中の変更や未リリースの改善点をここに記載します。

## [0.1.0] - 2026-03-28
初回リリース（推定）。以下はコードベースから推測できる主要な追加点・設計方針・注意事項です。

### Added
- パッケージのエントリポイント
  - kabusys パッケージを公開。__version__ = "0.1.0"。
  - サブパッケージ群を __all__ で公開: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パーサ実装（export 形式 / クォート / インラインコメント処理対応）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開（必須値チェック付きプロパティ）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得。
    - KABUSYS_ENV と LOG_LEVEL の妥当性検証（許容値チェック）。
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）を提供。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）を用いてセンチメントを算出。
    - バッチ処理（最大20銘柄 / チャンク）、トークン肥大対策（記事数・文字数制限）。
    - JSON 出力を厳密に検証し、スコアを ±1 にクリップして ai_scores テーブルへ冪等書き込み（DELETE→INSERT）。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx）、フェイルセーフ（失敗時は無視して継続）。
    - テスト用に _call_openai_api を patch 可能にしてモックしやすく設計。
    - 公開関数: score_news(conn, target_date, api_key=None)。
    - タイムウィンドウ計算ユーティリティ: calc_news_window(target_date)。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - OpenAI 呼び出し、リトライ、失敗時フォールバック（macro_sentiment=0.0）。
    - DuckDB を用いた冪等な market_regime 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定や next/prev_trading_day、get_trading_days、is_sq_day を提供。
    - DB データ優先、未登録日は曜日ベースのフォールバック。最大探索日数で無限ループ防止。
    - 夜間バッチジョブ calendar_update_job(conn, lookahead_days=...) により J-Quants API から差分取得 → 保存（バックフィル・健全性チェックあり）。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを定義して ETL の取得件数・保存件数・品質問題・エラーを収集。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を考慮した設計方針。
    - jquants_client との連携を想定した保存ロジック（Idempotent 保存）。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - Value: PER、ROE（raw_financials + prices_daily を組合せ）。
    - 全関数は DuckDB を受け取り SQL ベースで計算。返り値は (date, code) を含む dict のリスト。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。
    - 統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）。
    - 外部ライブラリに依存せず、標準ライブラリ + DuckDB で完結。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数で API キー等を扱う設計。必須環境変数が未設定の場合は明確な ValueError を発生させる。
- .env 自動ロード時に既存 OS 環境変数を保護するため protected ロジックを導入。
- KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）。

### Notes / Implementation details / 開発者向け補足
- ルックアヘッドバイアス防止:
  - 多くの処理（score_news, score_regime, factor 計算等）は datetime.today() / date.today() を直接参照せず、呼び出し元から target_date を渡す設計。
  - DB クエリでも date < target_date のように排他条件を使い、将来データの参照を回避。
- OpenAI 呼び出し:
  - gpt-4o-mini と JSON mode を利用する想定。レスポンスパースやバリデーションを厳格に実施。
  - 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフリトライ。その他はフェイルセーフでスキップ。
  - テスト容易性のため _call_openai_api をモック可能に実装。
- DuckDB 依存:
  - 多数のクエリ・ウィンドウ関数（OVER, LAG, LEAD, ROW_NUMBER）を活用。
  - executemany に関する DuckDB の制約（空リスト不可）を考慮したガードあり。
- DB 書き込みは冪等性を重視（DELETE→INSERT のパターンや ON CONFLICT を利用する想定）。
- ロギング:
  - 各モジュールで詳細な logger.debug / info / warning / exception を出力するよう設計されている。

---

変更履歴はコードの現状からの推測に基づき作成しています。将来的なコミット履歴やリリースノートと合わせて更新してください。