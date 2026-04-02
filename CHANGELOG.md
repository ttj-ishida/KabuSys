CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトはセマンティックバージョニングに従います。  
（参考: https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------
（なし）

[0.1.0] - 2026-04-02
-------------------

Added
- 初期リリースを追加（kabusys v0.1.0）。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__="0.1.0"、公開モジュール一覧を定義。

- 環境・設定管理
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする仕組みを実装。
    - .env の堅牢なパーサを実装（export プレフィックス対応、単/重引用符のエスケープ処理、行末コメントの扱いなど）。
    - OS 環境変数保護（protected set）や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などをプロパティ経由で取得。
    - env と log_level の値検証を実装し、不正値時に ValueError を送出。

- AI（ニュース NLP・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントスコアを ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）のユーティリティ calc_news_window を提供。
    - 最大バッチサイズ、1銘柄あたりの最大記事数/文字数等の制約を導入してトークン膨張に対処。
    - API 呼び出しに対する指数バックオフリトライ（429・ネットワーク断・タイムアウト・5xx 対応）を実装。
    - レスポンスバリデーションを強化（JSON 抽出/パース、results リストの整合性、スコア型チェック、未知コードの無視、スコアの ±1.0 クリップ）。
    - 書き込みはトランザクション（BEGIN / DELETE（対象コードのみ） / INSERT / COMMIT）で冪等性と部分失敗時の保護を実現。
    - テスト容易性のため、OpenAI 呼び出しを差し替え可能（内部 _call_openai_api は差し替えを想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio は target_date より前のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）でフォールバック。
    - マクロキーワードで raw_news を抽出し、LLM（gpt-4o-mini）でマクロセンチメントを取得。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 合成は重量付け（MA:70%、マクロ:30%）、スコアを -1.0..1.0 にクリップして閾値でラベル付け。
    - market_regime テーブルへ冪等書き込み（DELETE → INSERT）を実施。
    - OpenAI 呼び出しでのリトライ/バックオフや 5xx の扱いを実装。テストで差し替え可能。

- データプラットフォーム（ETL / カレンダー / クオリティ）
  - src/kabusys/data/pipeline.py
    - ETL パイプライン設計に基づくユーティリティを実装。
    - ETLResult dataclass を定義（取得数・保存数・品質問題・エラー一覧を保持、辞書化メソッド付き）。
    - 差分更新・バックフィル（既存最終日から数日前を再取得）・品質チェックのためのフレームワーク方針を実装。
    - DuckDB へのテーブル存在チェックや最大日付取得ユーティリティを提供（ETL の前処理用）。

  - src/kabusys/data/calendar_management.py
    - market_calendar を利用した営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB にデータが無い、または未登録日の場合は曜日ベースのフォールバック（週末を非営業日）を採用。DB とフォールバックの整合性を保つ設計。
    - カレンダー夜間バッチ calendar_update_job を実装（jquants_client 経由で差分取得し冪等保存、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル日数等の保護パラメータを導入して無限ループや異常データを防止。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポートするシンプルなインターフェースを提供。

  - jquants_client との連携を想定した設計（fetch / save の呼び出し位置を確立）。エラー時は例外をキャッチして安全に処理を中止。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL ウィンドウ関数を用いて効率的に計算。データ不足時は None を返す（安全な欠損扱い）。
    - raw_financials を利用して PER / ROE を算出する calc_value を実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）の算出（calc_ic）、統計サマリー（factor_summary）、ランキング変換（rank）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。ランクは同順位を平均ランクで扱う仕様。
    - 入力検証（horizons の制約や必要最小サンプル数チェック）や数値の有限性チェックを実装。

- 共通設計・運用上の配慮
  - DuckDB を主な一時 DB / 分析 DB として利用することを前提とした実装。
  - ルックアヘッドバイアス防止のため、日付参照は date.today()/datetime.today() に直接依存しない設計（関数に target_date を明示的に渡す）。
  - OpenAI API 呼び出しについては api_key を引数で注入可能にしてテスト容易性を確保（環境変数 OPENAI_API_KEY もサポート）。
  - 多くの箇所でフェイルセーフを採用（API 失敗時はスキップあるいは中立値にフォールバック）して運用時の安定性を優先。
  - DB 書き込みは基本的にトランザクションで行い、部分失敗時に他データを消さないための設計（対象コードを絞った DELETE 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 外部 API キー（OpenAI 等）は環境変数で注入する設計。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動 .env ロードを抑止可能。

Notes / Known limitations
- OpenAI の呼び出しは gpt-4o-mini を想定しており、実運用では API 使用量・料金・レート制限に注意が必要。
- jquants_client（データ取得/保存）はこのコードベースでは外部モジュールとして想定される（実際の実装に依存）。
- monitoring モジュールは __all__ に含まれるが、このリリースにモジュールの詳細実装が含まれていない可能性があります（設定は config で提供）。

Contributing
- バグ報告・機能提案は Issue を通じてお願いします。PR はテストを含めて送付してください。

----- End of CHANGELOG -----