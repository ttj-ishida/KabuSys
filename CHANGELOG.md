# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

## [Unreleased]

（無し）

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買・データ基盤・リサーチ向けの基本機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。
  - サブパッケージ群（data, research, ai, monitoring, strategy, execution）を公開インターフェースで想定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。
  - 読み込み挙動:
    - export プレフィックスや引用符を考慮したパース処理。
    - コメント処理（クォート内は除外、未クォート時の '#' の扱い等）。
    - OS 環境変数保護（既存環境変数は上書きされない、.env.local は override=True で上書き可能）。
    - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）をプロパティ経由で取得。未設定時は ValueError を投げる。
  - デフォルト値（API ベース URL や DB パス等）と環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
  - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- AI（自然言語処理）機能（src/kabusys/ai/ 以下）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにテキストを結合し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出する pipeline を実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供する calc_news_window。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、記事トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
    - API 呼び出しに対するエクスポネンシャルバックオフ、429/ネットワーク/タイムアウト/5xx に対するリトライ処理を実装。
    - JSON Mode のレスポンスをバリデーションして ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込む。部分失敗時に他銘柄の既存スコアを保護する実装あり。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - フェイルセーフ設計: API 失敗時は例外を投げず該当チャンクをスキップして継続、ログ出力で通知。
    - 単体テスト用に _call_openai_api をモック差し替え可能な設計コメントあり。
    - パブリック API: score_news(conn, target_date, api_key=None) を提供（src/kabusys/ai/__init__.py で score_news をエクスポート）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - prices_daily から ma200_ratio を算出、raw_news からマクロキーワードでニュースを抽出し OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API 呼び出しのリトライ、エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等書き込み（トランザクション処理、ロールバック対策）を実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - パブリック API: score_regime(conn, target_date, api_key=None)。

- データ基盤（src/kabusys/data/ 以下）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を基に営業日判定、次/前営業日取得、期間内営業日リスト取得、SQ 判定などのユーティリティを実装。
    - DB 登録値優先だが未登録日は曜日フォールバック（土日非営業）で一貫した挙動を提供。
    - カレンダー夜間バッチ（calendar_update_job）: J-Quants クライアントから差分取得し冪等保存、バックフィルと健全性チェックを実装。
  - ETL / パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー などを集約）。
    - テーブル存在確認、最大日付取得などのユーティリティを実装。
    - 差分取得・バックフィル・品質チェック（quality モジュール連携）を想定した設計。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ機能（src/kabusys/research/ 以下）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）を DuckDB SQL ベースで実装。
    - データ不足時は None を返す設計、全関数は prices_daily / raw_financials のみを参照。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部ライブラリに依存しない純粋 Python & DuckDB ベースの実装。
  - research パッケージは主要関数を __all__ で公開。

- DuckDB を中心とした DB 操作
  - 各モジュールは DuckDBPyConnection を受け取り、SQL と Python の組合せで分析・更新を行う設計。

- ロギングと診断
  - 各処理に詳細な logger.debug/info/warning/exception を追加し、失敗時や状況把握が可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security / Ops
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY をフォールバックに使用。
- 環境変数読み込みは OS 環境変数を保護する設計（.env による上書きを制御）。

### Notes / Known limitations
- AI モジュールは OpenAI に依存。API のレスポンス形式変更やモデルの変更によりパース部分の修正が必要になる可能性あり。
- DuckDB executemany に空リストを渡せない点に対する保護ロジックを導入（互換性対策）。
- 一部関数（例: _adjust_to_trading_day の実装続き等）はコード断片により拡張を想定。
- ai/__init__.py では現在 score_news のみを __all__ に含めて公開。regime_detector はモジュールとして存在するが公開エントリポイントの調整が今後必要になる可能性あり。

### Breaking Changes
- なし（初回リリース）

---

（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時にはテスト結果・リリース手順・デプロイ情報を追加してください。）