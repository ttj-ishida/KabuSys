CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
重要な公開バージョンと機能追加・修正をコードベースから推測して日本語で記載しています。

Unreleased
----------
（現時点では未リリースの作業はありません）

[0.1.0] - 2026-04-11
-------------------

Added
- 基本パッケージ初期実装
  - パッケージバージョン: __version__ = "0.1.0"

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - ブローカークライアントを BrokerClientFactory で作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて実行セッションを開始。
    - 起動直後にプロセス優先度を "high" に設定（set_process_priority を利用）。
    - duckdb 接続を使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 や負や非数）はデフォルトにフォールバックし警告ログを出力。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用（monitoring は本番 DB に接続）。

- 設定管理
  - config.Settings を導入（settings = Settings() を提供）。
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探索）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート、エスケープ、行末コメント等に対応。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / PID/KILL フラグ / しきい値 / 環境判定など）。
    - 環境変数値のバリデーション（例: KABUSYS_ENV の有効値、LOG_LEVEL の有効値、PAPER_FILL_MODE の列挙検証 など）。未設定の必須値は ValueError を送出。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装。Windows と POSIX 系（Linux, Darwin, FreeBSD）を吸収して優先度（nice/HIGH_PRIORITY_CLASS）を設定。失敗時は警告を出して継続。
    - set_cpu_affinity(cpu_count) を実装。任意の最初 N コアにプロセスをピン留め可能。権限等で失敗した場合は警告でスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソート。スコア同値は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分。全てのスコアが 0 の場合は等金額にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存保有割合が閾値を超える場合、新規候補を除外（"unknown" セクターはセクター上限適用外）。
    - calc_regime_multiplier: 市場レジーム ('bull','neutral','bear') に対する投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告を出す。

  - portfolio/position_sizing.py
    - calc_position_sizes: 等配分 / スコア配分 / リスクベースの株数算出を実装。
      - 単元株丸め（lot_size、デフォルト 100）や 1 銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer による保守的見積りをサポート。
      - リスクベースでは stop_loss_pct と risk_pct に基づく算出を行う。
      - スケーリング時の端数処理は lot_size 単位で再配分（残余キャッシュと fractional 残差に基づく公平配分）。

  - portfolio/__init__.py で上記関数群を公開。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（MA200）を DuckDB 上の SQL で効率的に計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None を返す設計。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。target_date 以前の最新財務データを取得。
    - DuckDB を用いた一貫した実装で prices_daily / raw_financials を参照。

  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証（1〜252 日）あり。
    - calc_ic: スピアマンのランク相関（IC）を実装。同順位は平均ランクで処理。有効レコードが 3 未満の場合 None を返す。
    - rank: 同順位に平均ランクを与える安定した実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数（None 値除外）。

  - research/__init__.py で主要 API を公開（zscore_normalize を含む）。

- AI（OpenAI）連携機能
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ書き込み。
    - バッチ処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたり最大記事数・最大文字数制限、JSON Mode を利用した厳密なレスポンス期待。
    - リトライ戦略: 429 / ネットワーク / タイムアウト / サーバー 5xx を対象に指数バックオフで最大リトライ（デフォルト _MAX_RETRIES）。
    - レスポンス検証: JSON パース、results 配列の存在、各要素に code と score があること、未知コードの除外、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗に強い設計（対象コードのみ DELETE → INSERT を行い、空の executemany を避けることで DuckDB 互換性を確保）。
    - API キー解決: 引数 api_key または環境変数 OPENAI_API_KEY。未設定時は ValueError。
    - calc_news_window を提供（target_date に対する JST ベースの収集ウィンドウを UTC naive datetime で返す）。

  - ai/regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュース（news_nlp の window 計算を再利用）から market regime（'bull'/'neutral'/'bear'）を判定。
    - MA200 とマクロセンチメントを重み付け（70% / 30%）、組み合わせてスコアを合成し閾値によりカテゴリを決定。API エラー時は macro_sentiment=0.0 でフォールバック。
    - DuckDB 上の prices_daily/raw_news を参照し、冪等的に market_regime テーブルへ書き込み。

Changed
- DB 初期化と接続方針
  - run_execution / run_monitoring は起動時に init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。
  - run_execution は paper_trading 環境時に別 SQLite を使用することでテスト用 DB と本番の完全分離を提供。

Fixed / Robustness
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ対応、export プレフィックス対応、行末コメントの扱いを明確化。
  - OS 環境変数を保護する protected オプションを追加（.env.local は override=True による上書きを可能にしつつ OS 環境を保護）。

- OpenAI 呼び出しの堅牢化
  - JSON mode でも応答に余計なテキストが混ざるケースを想定して最外側の {} を抽出してパースするフォールバックを実装。
  - API 呼び出し関数を分離（_call_openai_api）し、テスト時に差し替え可能に設計。

Notes / 仕様
- デフォルト値と挙動
  - MONITOR_POLL_INTERVAL のデフォルトは 60 秒。不正値はデフォルトにフォールバックして警告を出す。
  - PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。無効値は ValueError。
  - KABUSYS_ENV の有効値は "development" | "paper_trading" | "live"。無効値は ValueError。
  - process_priority の既定動作はプラットフォーム依存。サポート外 OS は警告を出し設定をスキップ。

- フェイルセーフ設計
  - AI API 失敗時は部分的にフェイルセーフ（例: news_nlp は失敗をスキップして継続、regime_detector は macro_sentiment を 0.0 にフォールバック）。
  - DB 書き込みはトランザクションを用い、失敗時はロールバックを試みる。

開発上の備考 / 今後の改善候補（コードから推測）
- price の欠損時のフォールバック（risk_adjustment.apply_sector_cap 内の TODO）。
- 銘柄ごとの lot_size を銘柄マスタから得られるよう拡張（position_sizing の TODO）。
- DuckDB のバージョン差異に起因するバインド制約（executemany の空リスト等）に注意。

ライセンスやセキュリティに関する変更は本差分からは記載されていません。

以上。コードから推測される主要な機能・変更点を Keep a Changelog 準拠で日本語に要約しました。不明点や特定モジュールごとの詳細な履歴化を希望される場合は、そのモジュール単位でさらに分解して作成できます。