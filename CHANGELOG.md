Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

0.1.0 - 2026-04-09
------------------

Added
- 初回リリース。KabuSys のコア機能を追加。
- パッケージバージョンを `__version__ = "0.1.0"` として公開。
- 環境設定:
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
    - 自動ロードのオフ切り替え: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
    - export 形式やクォート、インラインコメントに対応した .env パーサを実装。
    - 必須設定取得用の `_require()` と Settings クラスを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等のプロパティを提供。
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）、監視関連（PID_FILE_PATH, KILL_FLAG_PATH 等）、閾値（CPU/MEM/DISK）や PAPER_FILL_MODE/LOG_LEVEL/KABUSYS_ENV の検証とデフォルトを実装。
      - 無効な値は ValueError を送出することで早期検出。

- ポートフォリオ構築（純関数）:
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレーク処理して上位 N 件を選択。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバック、WARNING ログ）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方式に基づき注文株数を計算。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、手数料/スリッページ見積り用の cost_buffer を考慮。
    - aggregate cap によるスケールダウン後、lot 単位で残差を公平に配分するロジックを実装（端数処理の再現性を確保）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター暴露が閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime ('bull'|'neutral'|'bear') に応じた投下資金乗数を提供（未知レジームは 1.0 でフォールバックし WARNING）。

- リサーチ / ファクター計算:
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を DuckDB の prices_daily テーブルから算出。
    - calc_volatility: ATR20・相対 ATR、20日平均出来高、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と当該日の株価を組み合わせて PER/ROE を計算（最新財務レコードを target_date 以前から取得）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括 SQL で計算。horizons の検証（正整数・<=252）。
    - calc_ic: スピアマンランク相関による IC を計算（有効レコード < 3 の場合は None）。
    - rank / factor_summary: 同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージは外部ライブラリに依存せず（duckdb のみ使用）設計。

- AI（LLM）関連:
  - src/kabusys/ai/news_nlp.py
    - raw_news を集約して OpenAI（gpt-4o-mini）に投げ、銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数制限、レスポンス検証、スコアクリップ（±1.0）、部分書き込み（対象コードのみ DELETE→INSERT）により部分失敗耐性を確保。
    - API の 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを実装。その他エラーはフェイルセーフ的にスキップ。
    - 時間ウィンドウ計算（JST ベース）を calc_news_window で提供（testable、datetime.today() を直接参照しない設計）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込みを行う機能を実装。
    - マクロニュース抽出（キーワードベース）と LLM 評価の実装。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - news_nlp のウィンドウ計算を再利用（calc_news_window を import）。
  - OpenAI クライアントは引数の api_key または環境変数 OPENAI_API_KEY を参照する仕様。未設定時は ValueError を送出。

- モニタリング永続化:
  - src/kabusys/monitoring/monitoring_db.py
    - SQLite を用いた監視ログ永続層（init_monitoring_db）を実装。system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを冪等で作成。

- パッケージ API エクスポート:
  - kabusys/portfolio, kabusys/research, kabusys/ai に主要関数を __all__ で公開。

Changed
- 設計上の方針（全体）:
  - ルックアヘッドバイアス防止のため、日付参照や DB クエリで target_date の扱いに注意（datetime.today() / date.today() を直接参照しない）。
  - research モジュールは prices_daily / raw_financials のみ参照し、本番取引 API にアクセスしないことを明示。

Fixed / Notes
- .env パーサの改善:
  - export プレフィックス、シングル/ダブルクォート内部のバックスラッシュエスケープ、インラインコメントの扱い、キー無し行のスキップ等、多くの実戦的な .env ステートメントに耐えるように実装。
  - .env.local を .env の上書きとして読み込む際、OS 環境変数は保護される（protected set）。
- position_sizing:
  - 価格欠損時のスキップと lot 単位丸めにより不正な発注量生成を防止。
  - aggregate cap スケールダウン後の端数配分アルゴリズムで再現性を確保。
- risk_adjustment:
  - "unknown" セクターをセクター上限チェックの対象外とし、セクター未定義銘柄の不当な除外を回避。
- AI モジュール:
  - OpenAI の JSON mode でも余計な前後テキストが混ざる場合に最外の {} を抽出して復元する処理を追加（堅牢化）。
  - API レスポンス検証は厳格に行い、不正応答は該当チャンクだけをスキップしてシステム全体の継続を保証。

Security
- 環境変数からの API キー取得を行うが、DB/ログへのキー保存は行わない設計。OpenAI API キーは引数または環境変数 OPENAI_API_KEY を想定。

Migration notes / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings 上で必須。未設定時は ValueError。
- デフォルトや検証:
  - KABUSYS_ENV は "development"（デフォルト）。有効値: development, paper_trading, live。無効な値は ValueError。
  - LOG_LEVEL は "INFO"（デフォルト）。有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。
  - PAPER_FILL_MODE の有効値: instant, partial, never, reject（無効な指定は ValueError）。
- OpenAI 関連:
  - OPENAI_API_KEY が未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出。
  - LLM 呼び出しは外部 API 依存のため、運用ではレート制限やコストに注意。
- .env 自動読み込み:
  - パッケージ配布後も __file__ を起点にプロジェクトルートを探索するため、CWD に依存しない自動読み込みが行われる。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Known limitations / TODO
- Position sizing の lot_size は現状グローバル固定。将来的には銘柄別 lot_map を受け取る拡張を予定。
- apply_sector_cap の価格欠損時（price == 0.0）ではエクスポージャーが過少見積りされる可能性があるため、将来的には前日終値や取得原価等のフォールバックを検討。
- research の統計・分析は pandas 等に依存しない純 Python 実装のため、大規模データ毎回の処理性能を要検討。

Contact
- バグ報告や問い合わせはリポジトリの Issue にお願いします。