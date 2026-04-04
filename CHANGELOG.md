# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買システムの基盤機能を実装しました。主な追加点と設計上の特徴は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ定義（kabusys）とバージョン管理（__version__ = "0.1.0"）。
  - __all__ による公開サブパッケージの宣言（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読込する機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - OS環境変数は保護され、.env の上書きを制御。
  - .env ファイル行の詳細なパーサ実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート）。
  - 必須環境変数チェック機能（_require）と Settings クラスを提供。
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム設定向けのプロパティを定義。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値検証を実装。
    - デフォルト値の提供（例: KABU_API_BASE_URL, DUCKDB_PATH 等）。

- AI モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ問い合わせしてセンチメント（ai_score）を生成。
    - 時間ウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC では前日 06:00 ～ 23:30）を正確に計算する calc_news_window を提供。
    - 1 銘柄あたりのトークン過大化対策（最大記事数・最大文字数トリム）。
    - 最大バッチサイズ、チャンク処理、リトライ（429/ネットワーク断/タイムアウト/5xx：指数バックオフ）を実装。
    - レスポンスのバリデーション処理（JSON パース復元、results 配列、code/score 検証、数値化、±1.0 でクリップ）。
    - DuckDB へ冪等的に書き込む実装（取得済みコードのみ DELETE → INSERT、empty executemany を回避するチェック）。
    - テスト用に OpenAI 呼び出し箇所を差し替え可能（内部 _call_openai_api を patch 可能に設計）。
  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを防止）。
    - raw_news からマクロ指標キーワードでタイトルを抽出し、OpenAI により macro_sentiment を取得（記事がない場合は LLM 呼び出しを行わず 0.0 を返す）。
    - LLM 呼び出しに対してリトライ/バックオフを実装し、API 失敗時はフェイルセーフとして macro_sentiment = 0.0 を採用。
    - 計算結果を market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。
    - テスト容易性のため OpenAI 呼出し箇所は差し替え可能。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー（market_calendar）管理機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバック。
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した挙動を保証。
    - 最大探索日数による無限ループ防止や健全性チェック（未来日付が極端な場合のスキップ）、バックフィル（直近数日を再取得）を実装。
    - calendar_update_job による夜間差分取得処理（jquants_client を利用して差分取得→保存）を実装。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を etl モジュールで再エクスポート）。
    - ETL パイプライン設計方針に沿ったユーティリティ群を実装（差分取得、冪等保存、品質チェックの収集と継続処理、バックフィル等）。
    - ETLResult は品質問題やエラーの集約、辞書化変換（監査ログ用）をサポート。
    - DuckDB を主要なデータストアとして想定し、テーブル存在チェックや最大日取得等のユーティリティを用意。

- リサーチ／特徴量（kabusys.research）
  - factor_research
    - モメンタム（1/3/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、
      バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials のみ参照し、外部発注や外部 API を呼ばない設計。
    - データ不足時の None ハンドリングや、営業日ベースのスキャン設計（カレンダーバッファ）を採用。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、rank、factor_summary を実装。
    - スピアマンランク相関（ランクの処理は同順位を平均ランクで扱う）や基本統計量計算を提供。
    - 外部ライブラリに依存せず、標準ライブラリのみで実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 設計上の重要事項
- ルックアヘッドバイアス防止:
  - AI モジュール・リサーチ関数は datetime.today() / date.today() を参照せず、必ず引数として渡された target_date に基づいて処理します。
  - DB クエリは target_date 未満 / 目標日の排他条件を適切に使用しています。
- フェイルセーフ / 冗長性:
  - OpenAI 呼び出しでの失敗（ネットワーク、429、タイムアウト、5xx）はリトライやスコア 0.0 フォールバック等の安全策を備え、処理中に致命的例外を起こさない設計（ただし DB 書込みなど重大失敗は上位に伝播）。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数を patch することで差し替え可能に実装（ユニットテストでのモック化が容易）。
- トランザクションと冪等性:
  - market_regime / ai_scores 等への書込みは DELETE→INSERT をトランザクションで行い、部分失敗時の既存データ保護や冪等性に配慮。
- DuckDB 前提:
  - コアの集計・保存は DuckDB 接続を前提としています。特定の DuckDB バージョン（executemany の空リスト制約など）への互換性対応が含まれます。

---

今後のリリースでは、strategy / execution / monitoring の具象実装や実運用での発注ロジック、追加の品質チェック・モニタリング、より細かなメトリクスや可観測性の強化を予定しています。