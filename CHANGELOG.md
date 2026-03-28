# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。セマンティックバージョニングを採用します。

## [Unreleased]

なし

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基礎
  - kabusys パッケージを導入。公開サブパッケージとして data, strategy, execution, monitoring を __all__ で定義（実装は一部別ファイルを想定）。
  - バージョン情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として管理。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能を実装。プロジェクトルートは __file__ を基準に .git または pyproject.toml を探索して特定（CWD 非依存）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護（protected）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動読み込みを無効化可能。
  - .env のパースは export 文、クォート付き値のバックスラッシュエスケープ、インラインコメントの扱い等に対応する堅牢な実装。
  - Settings クラスを公開（settings）。J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル等のプロパティを提供し、必須値未設定時は ValueError を送出。KABUSYS_ENV と LOG_LEVEL の値検証を実装。

- AI（自然言語処理）機能（src/kabusys/ai）
  - ニュースセンチメント（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini・JSON mode）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチサイズ、記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密バリデーション（JSON 抽出・results フィールド検査・コード一致・数値チェック）を実装。
    - スコアは ±1.0 にクリップ。取得したスコアのみ ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込み。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して market_regime テーブルへ日次で書き込み。
    - DuckDB から価格とニュースを参照。ルックアヘッドバイアス防止ロジックを徹底（date 未満のデータのみ使用、datetime.today() を直接参照しない）。
    - OpenAI 呼び出しは gpt-4o-mini を利用。API エラー・パース失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - ai パッケージは score_news, score_regime を外部公開。

- データプラットフォーム（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを前提にした is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB に値がない場合は曜日（平日のみ営業）ベースのフォールバックを使用。DB とフォールバックの一貫性を確保。
    - calendar_update_job を実装し、J-Quants API クライアント（jquants_client）から差分取得 → 冪等保存（ON CONFLICT DO UPDATE）を行う。バックフィル、健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得件数/保存件数/品質問題/エラー一覧等を保持、辞書変換ユーティリティ含む）。
    - 差分更新・バックフィル・品質チェック設計方針を実装するためのヘルパー関数（テーブル存在確認、最大日付取得等）を提供。
    - etl.py で ETLResult を公開。

- リサーチ・ファクター（src/kabusys/research）
  - factor_research モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None、営業日ベースの窓）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS がゼロや欠損時は None）。PBR/配当利回りは未実装。
    - DuckDB SQL を中心に実装し、副作用のある外部 API 呼び出しは行わない。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク化して算出、十分なサンプルがない場合は None）。
    - rank, factor_summary（count/mean/std/min/max/median）などの統計ユーティリティを実装。
  - research パッケージは主要関数を __all__ で再エクスポート。

### Changed
- （初版なので履歴の変更点はなし）

### Fixed
- （初版なので修正履歴はなし）

### Security
- OpenAI API キーの扱いは api_key 引数または環境変数 OPENAI_API_KEY により決定。キーがない場合は ValueError を送出し、誤った実行を未然に防止。

### Notes / Design decisions / Limitations
- DuckDB を主要なローカルストレージとして利用。DuckDB バインドに関して互換性（executemany の空リスト不可など）に配慮した実装を行っている。
- OpenAI API 呼び出しは JSON mode を使い厳密な JSON 出力を期待しているが、現実の応答で前後テキストが混ざる場合に備えて最外の {} を抽出するフォールバックロジックを実装。
- 多くの外部依存（openai パッケージ、jquants_client、DuckDB）を前提としているため、稼働にはそれらの導入・設定（API キー・DB スキーマ準備など）が必要。
- raw_financials に基づく PBR / 配当利回りは現バージョンでは未実装（calc_value に注記あり）。
- ai/regime_detector と ai/news_nlp で内部的に OpenAI 呼び出し用のヘルパー関数を独立実装しており、モジュール間でプライベート関数を共有しない設計（テスト時は個別にモック可能）。
- package __all__ に execution, monitoring を含むが、今回の差分提供ファイル群では直接の実装ファイルは含まれていない。発注・監視関連の実装は別ファイル/将来リリースで提供されることを想定。

もし補足してほしい点（例: モジュール別のより詳細な変更ログ、既知のバグ一覧、リリース手順のテンプレートなど）があればお知らせください。