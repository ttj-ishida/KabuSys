# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

現在のバージョンは 0.1.0（初回リリース）です。

## [0.1.0] - 2026-04-09

### 追加 (Added)
- 基本パッケージ初期実装を追加。以下の主要コンポーネントを含む:
  - kabusys.config
    - .env ファイルまたは環境変数からの設定読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。プロジェクトルートが見つからない場合は自動ロードをスキップ。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`.env.local` は `.env` を上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
    - `.env` のパースは `export KEY=val`、クォート/エスケープ、行末コメント処理等に対応。
    - 環境変数保護機能: OS 側で既に設定されているキーは上書きしない（protected set）。
    - Settings クラスを提供。主要なプロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - LINE_*（LINE Messaging API 用、デフォルト空）
      - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等、デフォルト値あり）
      - Paper trading 関連（PAPER_FILL_MODE のバリデーション）
      - 監視関連ファイルパス（PID / KILL FLAG）およびリソース閾値（CPU/MEM/DISK）
      - 環境モード（KABUSYS_ENV）および LOG_LEVEL のバリデーション、is_live/is_paper/is_dev 補助属性
  - kabusys.portfolio
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順・同点時タイブレークで選択。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
    - risk_adjustment:
      - apply_sector_cap: 既存ポジションのセクター比率が閾値を超える場合に同セクターの新規候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 でフォールバック（WARNING ログ）。
    - position_sizing:
      - calc_position_sizes: 発注株数決定ロジックを実装。
        - allocation_method: "risk_based" / "equal" / "score" に対応。
        - 単元株（lot_size）丸め処理、単銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン処理を実装。
        - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積りと、スケールダウン時の端数（fractional）を lot 単位で再配分するアルゴリズムを実装。
  - kabusys.research
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の prices_daily から計算。データ不足時は None を返す設計。
      - calc_volatility: 20日 ATR（avg true range）、相対 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）を計算。TRUE_RANGE の NULL 伝搬を制御。
      - calc_value: raw_financials と prices_daily を用いて PER / ROE を計算（最新報告日以前の最新財務レコードを銘柄ごとに取得）。
    - feature_exploration:
      - calc_forward_returns: 指定 horizon（営業日ベース）に対する将来リターンを一括で取得。horizons のバリデーションあり。
      - calc_ic: Spearman ランク相関（IC）を実装。レコード不足/定数分散時は None を返す。
      - rank: 同順位は平均ランクで処理。丸め誤差を防ぐため round(..., 12) を用いた比較。
      - factor_summary: count/mean/std/min/max/median の統計サマリーを標準ライブラリのみで計算。
    - 設計方針として DuckDB のみ参照、外部 API / 実際の発注系にはアクセスしないことを明確化。
  - kabusys.ai
    - news_nlp:
      - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
      - ニュース時間ウィンドウ（JST 基準）を calc_news_window で算出（UTC naive datetime を返す）。
      - チャンク処理（_BATCH_SIZE = 20）、記事数/文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、JSON Mode を利用した厳密なレスポンス期待。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ。レスポンスバリデーション、安全なスコアクリップ（±1.0）。
      - DuckDB への書き込みは部分更新（対象コードのみ DELETE → INSERT）で、部分失敗時に既存スコアを消去しない工夫あり。executemany の空リスト制約（DuckDB 0.10）に対処。
      - テスト用に _call_openai_api をモック可能（unittest.mock.patch を想定）。
    - regime_detector:
      - ETF 1321（日経連動ETF）200日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成し、市場レジームを 'bull'/'neutral'/'bear' で判定。
      - 重み付け: MA(70%) / macro sentiment(30%)、スケール係数・閾値定義あり。API 失敗時は macro_sentiment=0.0 を採用して継続（フェイルセーフ）。
      - マクロニュース抽出はキーワードベースでタイトルを検索（_MACRO_KEYWORDS）。LLM 呼び出しは別実装で news_nlp と結合しない設計。
      - market_regime テーブルへの冪等書き込みを実装（BEGIN / DELETE / INSERT / COMMIT）。
    - 共通:
      - OpenAI API キー未設定時は ValueError を投げる明示的チェック（api_key 引数または OPENAI_API_KEY 環境変数）。
  - kabusys.monitoring
    - monitoring_db:
      - init_monitoring_db を実装。SQLite を用い、監視用のテーブル群（system_status, trade_logs, positions, risk_logs 等）とインデックスを冪等に作成するスクリプトを提供。
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - パッケージ公開用 __all__ に主要モジュール群を設定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 既知の制限 (Notes / Known limitations)
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後や CWD が異なる状況で期待どおり動作しないことがある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に環境変数をセットしてください。
- calc_momentum / calc_volatility 等は営業日ベース（連続レコード数）で計算するため、カレンダー日での扱いと差が出る可能性があります。
- apply_sector_cap は price_map に 0.0 の価格が含まれる場合、エクスポージャーを過少見積もる可能性がある（TODO コメントあり）。フォールバック価格戦略は今後の拡張対象。
- news_nlp / regime_detector は OpenAI に依存するため、API 仕様変更や料金、利用制限に注意が必要。テスト時には API 呼び出し部をモックすることを推奨します。
- DuckDB の executemany に関する互換性対応を行っている（空リスト不可）ため、古い/将来の DuckDB バージョンでの動作差異に注意。

### 開発者向けメモ
- 多くの外部通信部分（OpenAI 呼び出し）は内部関数として分離されており、ユニットテストで差し替え可能（patch を想定）。
- 研究・特徴量計算モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装しているため、環境構築が容易。
- settings の各プロパティは未設定時に ValueError を投げるもの（必須）とデフォルトを返すものが混在するため、運用前に必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OpenAI API key）がセットされていることを確認してください。

--- 

その他のリリースやバグフィックスは次回以降のバージョンで記載します。