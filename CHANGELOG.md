# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースポリシー: 初期バージョンとして v0.1.0 を公開。

## [Unreleased]

（現在のブランチに対する未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初回公開 (初期実装)。以下の主要機能・モジュールを実装しました。

Added
- パッケージ基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定/読み込み機能 (src/kabusys/config.py)
  - Settings クラスを実装し、アプリケーション設定を環境変数から取得するプロパティを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV の既定値とバリデーションを実装。
    - env 判定用プロパティ: is_live, is_paper, is_dev を提供。
  - .env 自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - .env の上書きロジックには protected（既存 OS 環境変数）保護を実装。

- AI（自然言語・レジーム判定）機能 (src/kabusys/ai/)
  - ニュースセンチメントのバッチ処理 (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から対象記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で扱い、calc_news_window 関数を提供）。
    - バッチサイズ上限: _BATCH_SIZE = 20、1 銘柄あたり最大記事数 _MAX_ARTICLES_PER_STOCK = 10、文字トリム _MAX_CHARS_PER_STOCK = 3000。
    - リトライ/バックオフ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大 _MAX_RETRIES）。
    - レスポンス検証: JSON パース、"results" リスト構造検証、コードの整合性、数値検証、スコア±1.0 クリップ。
    - テーブル書き込みは部分置換（該当コードのみ DELETE → INSERT）を行い、部分失敗時に既存スコアを保護。
    - テスト向けフック: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタ、最大記事数は _MAX_MACRO_ARTICLES = 20。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）で、失敗時は macro_sentiment = 0.0 にフォールバック。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - API 呼び出しのエラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError）に基づく挙動とログ出力を整備。

- データ基盤（DataPlatform）関連 (src/kabusys/data/)
  - ETL インターフェース (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装し、ETL 実行結果（取得件数・保存件数・品質問題・エラー一覧）を表現。
    - 差分取得・バックフィル・品質チェックの想定設計を実装方針として定義（実際の jquants_client 呼び出しを行うユーティリティ群と連携）。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの存在チェック、営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダー情報がない場合は曜日ベース（週末を除外）でフォールバック。
    - calendar_update_job を実装: J-Quants API から差分取得して market_calendar に冪等更新（バックフィルや健全性チェックも実装）。
    - 探索上限 (_MAX_SEARCH_DAYS) による無限ループ防止と各種安全チェック。
  - その他
    - jquants_client を介した外部 API 呼び出しを想定するモジュール設計（実装はクライアント実装に依存）。

- リサーチ・ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - モメンタム、ボラティリティ（ATR/出来高/売買代金）、バリュー（PER, ROE）などの定量ファクター計算関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB 上の prices_daily / raw_financials を用いた SQL ベースの実装。欠損データ時の None 扱い・ログを適切に実装。
    - 長期 MA、スキャン範囲、ATR 期間などの定数とバッファ条件を明確化。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力バリデーション付き）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランクベースで算出、最小有効サンプル数チェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め処理で tie を安定化）。
    - 統計サマリー function factor_summary（count/mean/std/min/max/median を計算）。
  - research パッケージ __init__.py にて公開 API を定義（calc_momentum 等と zscore_normalize の再エクスポート）。

Other notable design/quality points
- ルックアヘッドバイアス対策
  - 各 AI / リサーチ関数は内部で datetime.today() や date.today() を参照しない設計（target_date 引数に依存）。
  - DB クエリは target_date 未満または target_date に基づく排他条件で将来データを参照しない。
- リトライ/フェイルセーフ
  - OpenAI 呼び出しにはエラー分類に基づくリトライ/バックオフを実装し、最終的に失敗しても例外を投げずフォールバック（0.0 等）して処理を継続する箇所を用意。
- データベース操作の冪等設計
  - market_regime / ai_scores 等の書き込みは既存行を削除してから挿入することで冪等性を確保（トランザクション制御: BEGIN/COMMIT/ROLLBACK）。
- テスト容易性
  - OpenAI API 呼び出し点はモジュール内の private 関数を patch しやすくしており、ユニットテストで置換可能。
- DuckDB をメインのデータレイヤとして利用する設計（SQL を多用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げて明示的に失敗。
- .env 自動読み込み時に既存の OS 環境変数を保護する機構を実装。

Notes / Limitation
- gpt-4o-mini を想定したプロンプトと JSON mode を利用する実装になっているため、将来の OpenAI SDK/API 変更に対して互換性確認が必要。
- jquants_client の実装（fetch/save 関数）が外部に依存するため、実環境ではクライアント実装と API トークンの準備が必要。
- performance: 大規模データでのパフォーマンスは DuckDB クエリの最適化やバッチ設計（_BATCH_SIZE 等）の調整が必要な場合がある。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装と統合テスト
- CI における .env 自動ロード無効化フロー整備（KABUSYS_DISABLE_AUTO_ENV_LOAD の活用）
- ドキュメント（Usage、Architecture、ETL 操作手順）の拡充

もし特定モジュールについてより詳細な変更点（関数ごとの仕様やサンプル利用法）をCHANGELOG に追記したい場合は、対象のモジュール名を指定してください。