# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
現リリースはバージョン 0.1.0（初回公開）です。

## [Unreleased]

## [0.1.0] - 2026-03-27

Added
- パッケージの初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本構成
  - src/kabusys/__init__.py にてパッケージエクスポートを定義（data, research, ai 等を公開）。
  - src/kabusys/config.py: 環境変数 / .env 管理機能を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の自動読み込み（環境変数優先）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは quote/エスケープ、インラインコメント、export KEY=val 形式等に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等の設定を安全に取得（必須項目は未設定時に ValueError）。
    - ログレベル・環境名のバリデーション実装。

- AI（LLM）関連
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントスコアを算出して ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ計算（JST基準の前日15:00〜当日08:30）、記事トリム（件数/文字数上限）、バッチ処理（最大20銘柄/チャンク）、レスポンス検証、スコアの ±1.0 クリップをサポート。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ、非再試行エラーはフェイルセーフでスキップする実装。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
    - API キー未指定時は ValueError を送出。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動ETF）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装。
    - ma200_ratio 計算（ターゲット日未満のデータのみを使用してルックアヘッドを防止）、マクロニュース抽出、OpenAI 呼び出し、スコア合成、閾値判定、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - テスト用フック: _call_openai_api を差し替え可能。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。API キー未指定時は ValueError。

- Data（ETL / カレンダー等）
  - src/kabusys/data/pipeline.py
    - ETL の公開インターフェースと ETLResult データクラスを実装。
    - 差分取得・バックフィル・品質チェック（quality モジュールを参照）を念頭に置いた設計。
    - ETLResult: フェッチ／保存件数、品質問題リスト、エラーリスト、ヘルパー（has_errors, has_quality_errors, to_dict）を実装。
  - src/kabusys/data/etl.py
    - ETLResult を公開エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理と営業日判定 API を実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（平日のみ営業日）でフォールバック。
    - calendar_update_job により J-Quants から差分取得し market_calendar を冪等に更新（バックフィルと健全性チェック付き）。
    - DB 存在チェックや date 型変換などのユーティリティ実装。
    - jquants_client（jq）を利用した取得/保存処理の呼び出しに対応。

- Research（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - ファクター計算機能を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を利用。
    - calc_volatility: 20日 ATR、ATR/price、20日平均売買代金、出来高比率等のボラティリティ・流動性指標を計算。
    - calc_value: raw_financials の直近財務データと当日の株価から PER / ROE を計算（EPS==0 や欠損時は None）。
    - DuckDB を用いた SQL により効率的に一括計算。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 1日/5日/21日 等の将来リターンを計算（horizons の検証あり）。
    - calc_ic: Spearman のランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ。丸めによる ties の取り扱い考慮。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - 研究用ユーティリティは外部依存を避け、標準ライブラリと DuckDB のみで実装。

Other
- 共通設計方針
  - ルックアヘッドバイアスを避けるため、各処理は datetime.today()/date.today() を内部で参照しない設計（ターゲット日を明示的に受け取る）。
  - DuckDB を主要データストアとして利用する前提の SQL 実装。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT / ON CONFLICT 等）して部分失敗の影響を軽減。
  - OpenAI 呼び出しは JSON mode を利用・レスポンスバリデーションを厳密に行う。
  - ロギングを適切に行い、エラーはフェイルセーフで処理を継続する（致命的な局面は例外を上位へ伝播）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Deprecated / Removed
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI クライアントは openai.OpenAI を直接利用しており、API 仕様変更に対しては将来的な適応が必要。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン依存の挙動を回避するため、空チェックを行っている。
- 一部関数は jquants_client（jq）や quality モジュールに依存しており、これらの実装が必要。

--- 
（この CHANGELOG は提供されたコードベースから機能・設計方針を推測して作成しています。実際のリリースノートや公開日付はプロジェクトの運用に合わせて適宜調整してください。）