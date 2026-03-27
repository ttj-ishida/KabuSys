# CHANGELOG

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお本リリースはパッケージ内の実装内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期公開（kabusys v0.1.0）
  - パッケージメタ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に公開。

  - 環境設定 / .env 自動読み込み
    - src/kabusys/config.py
      - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動検出して読み込み（CWD に依存しない）。
      - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - .env パース機能を実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ対応、コメント処理）。
      - .env 読み込み時の上書き制御（override, protected）を実装し OS 環境変数保護に対応。
      - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（必須項目は _require により未設定時に ValueError を送出）。
      - 必須環境変数（例）:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - ログレベル / 環境種別検証（LOG_LEVEL, KABUSYS_ENV）を実装。

  - AI ニュース NLP / レジーム検知
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols テーブルのデータを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理を実装。
      - ニュース収集ウィンドウ計算 calc_news_window を実装（JST 基準前日 15:00 ～ 当日 08:30、DB には UTC naive datetime を使用）。
      - バッチサイズ、記事数上限、文字数トリム、JSON mode を利用した結果バリデーションを実装。
      - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはスキップして継続。
      - レスポンスの堅牢なパースと検証を行い、不正レスポンスは無視（部分成功を許容）。
      - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch 可能）。
      - DuckDB 互換性考慮（executemany に空リストを渡さない等）。

    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む処理を実装。
      - マクロキーワードで raw_news をフィルタして LLM に渡す機能を実装。
      - OpenAI 呼び出しはニュース NLP と別実装でモジュール結合を避ける設計。
      - API エラー時は macro_sentiment=0.0 のフェイルセーフで継続。
      - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と、DB 書き込み失敗時の ROLLBACK 保護。

  - データプラットフォーム（Data）機能
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理機能を実装（market_calendar テーブルの読み書き、祝日/SQ/半日判定、営業日の前後検索、期間内営業日取得）。
      - DB にカレンダーがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。DB 登録ありの場合は DB 値を優先。
      - calendar_update_job 実装: J-Quants API からの差分取得（jquants_client を利用）と冪等保存、バックフィル、防御的な健全性チェックを備える。

    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETL パイプライン基盤を提供。差分取得、保存（jquants_client 経由）、品質チェック（quality モジュール）を組み合わせる設計。
      - ETLResult dataclass を定義し、取得・保存件数、品質問題、エラー情報を集約して返す。
      - 内部ユーティリティ群（テーブル存在確認、最大日付取得、取引日調整など）を実装。

    - src/kabusys/data/__init__.py
      - ETLResult を外部に公開（etl モジュールで再エクスポート）。

  - Research（因子・特徴量探索）
    - src/kabusys/research/__init__.py
      - 主要関数を公開: calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank。

    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高変化率）の計算を実装。
      - DuckDB 上の SQL ＋ Python による実装で外部 API にはアクセスしない。データ不足時は None を返す仕様。

    - src/kabusys/research/feature_exploration.py
      - 将来リターン（複数ホライズン）の計算、IC（Spearman の ρ）計算、rank（平均ランク同順位処理）、factor_summary（count/mean/std/min/max/median）を実装。
      - pandas 等に依存せず標準ライブラリと DuckDB のみで処理。

  - そのほか
    - モジュール公開用の __init__ で ai.score_news をエクスポート（src/kabusys/ai/__init__.py）。
    - OpenAI クライアント利用時のデフォルトモデルは gpt-4o-mini。
    - 各所でログ出力を強化（info/debug/warning を適所で出力）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details / 既知事項
- OpenAI 利用
  - API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出。
  - JSON Mode を使いつつも実際のレスポンスに余分なテキストが混入する可能性に対応するパース耐性を実装。
  - テスト容易性を考慮し、各モジュールの OpenAI 呼び出し点は patch で差し替え可能にしている（ユニットテストでのモック利用を想定）。

- DB 操作と冪等性
  - market_regime / ai_scores 等への書き込みは冪等（DELETE→INSERT や ON CONFLICT 相当の処理）を意識している。
  - DuckDB のバージョン差異（executemany に空リストを渡せない等）に配慮した実装。

- ルックアヘッドバイアス対策
  - 各種処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - prices_daily などへのクエリは target_date 未満／以下の排他条件に注意を払っている。

- フェイルセーフ設計
  - OpenAI API の失敗は基本的に例外で停止させず、既定値（0.0 等）でフォールバックすることでパイプライン全体の停止を防ぐ設計。

- 環境変数自動ロード
  - .env のパースはかなり寛容で多くの shell 形式に対応するが、極端に異なるフォーマットでは期待通り動作しない場合がある。

- デフォルトパス
  - DuckDB Path および SQLite Path のデフォルト値が設定されている（DUCKDB_PATH = data/kabusys.duckdb, SQLITE_PATH = data/monitoring.db）。

- 未実装 / 将来的留意点（コードから推測）
  - Strategy・execution・monitoring パッケージの実体はこの差分に含まれていないため、発注フローや実口座との接続は別モジュールで実装される想定。
  - raw_financials の一部指標（PBR・配当利回り等）は未実装との注記あり。

---  
この CHANGELOG はコード内容の読み取りに基づく推測で作成しています。実際のリリースノートや運用方針はプロジェクトの公式ドキュメントに従ってください。