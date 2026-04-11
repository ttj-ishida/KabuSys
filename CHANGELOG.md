# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  

- リリースポリシー: 重大変更は Breaking Changes、互換的な機能追加は Added、バグ修正は Fixed、非推奨は Deprecated に分類します。

[0.1.0] - 2026-04-11
--------------------

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
  - 公開 API として portfolio / research / ai 等の主要機能をエクスポート（src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py）。

- 実行スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用する実装。
    - 起動時にプロセス優先度を "high" に設定しようとする（set_process_priority を呼び出し）。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine、OrderManager、RiskManager、Reconciler 等の組み立てとセッション実行。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読込。OS 環境変数を保護（上書きしない）し、`.env.local` は上書き許可。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサーは export 文、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - 多数のプロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視・閾値設定 / 環境判定 等）。
    - 入力検証: `KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等の値チェックを実装し、不正値はエラーで通知。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分へフォールバック（警告ログ）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを算出し、1 セクターの上限を超える場合は当該セクターの新規候補を除外（"unknown" セクターは制限適用外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 を返す。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: `allocation_method`（"risk_based" / "equal" / "score"）に基づき発注株数を算出。lot_size（単元）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer を用いた保守的見積り、端数処理（remainders による再配分）を実装。
    - リスクベース方式では stop_loss_pct と risk_pct に基づいて株数を算出。

- リサーチ（DuckDB ベース）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR/close（相対 ATR）、20 日平均売買代金、出来高比率を算出。NULL の取り扱いに注意した実装。
    - calc_value: raw_financials と組み合わせて PER / ROE を算出（最新レポートを銘柄ごとに選択）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: target_date 基準の将来リターン（複数ホライズン）を一括取得。horizons のバリデーションを実施。
    - calc_ic / rank / factor_summary: スピアマン（ランク相関）での IC 計算、同順位の平均順位付け、基本統計量集計を標準ライブラリのみで実装。
  - DuckDB 接続を受け取り、prices_daily / raw_financials などのテーブルのみ参照する設計（外部 API にアクセスしない）。

- AI（OpenAI）連携
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の Chat Completions（JSON mode）で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄）、記事数・文字数のトリム（最大記事数/文字数制限）を実装。
    - レート制限（429）・接続断・タイムアウト・5xx に対して指数バックオフ（最大リトライ）を実装。その他のエラーはフェイルセーフでスキップ。
    - API レスポンスの堅牢なバリデーション（JSON 抽出、構造検証、未知コード無視、数値チェック）とスコアの ±1.0 クリップ。
    - 書き込みは冪等性を考慮し、対象コードのみ DELETE → INSERT（トランザクション）を実施。DuckDB の executemany の注意点（空リスト不可）を考慮した実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - 時刻処理はルックアヘッドバイアス回避のため date.today() / datetime.today() を参照しない設計。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経連動） の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - ma200_ratio の算出は target_date 未満のデータのみ使用（ルックアヘッド回避）。データ不足時は中立（1.0）扱い。
    - マクロキーワードによる raw_news 抽出、OpenAI 呼び出し（gpt-4o-mini）、合成スコアのクリップを実施。API 失敗時は macro_sentiment=0.0（中立）で継続。
    - market_regime テーブルへ冪等書き込み。

- DB / 分析基盤
  - DuckDB を分析用 DB（duckdb.connect を利用）として多くのリサーチ / AI モジュールで採用。
  - SQLite はモニタリング / 実行関連の状態保存に使用。paper_trading 環境では専用 SQLite を使用して本番と分離。

- ユーティリティ
  - process_priority: psutil を利用してプラットフォームに依存しないプロセス優先度設定および CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, macOS, FreeBSD）をサポート。サポート外 OS ではスキップして警告。
    - 権限不足や未実装 API に対しては警告ログを出して安全にスキップ。
    - set_cpu_affinity は cpu_count 引数で最初の N コアに固定する（引数チェックあり）。
  - utils パッケージの雛形。

Security
- OpenAI API キーなどの機微情報は環境変数で管理する設計。`.env` 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

Compatibility / Notes
- DuckDB 0.10 系の挙動（executemany に空リスト不可など）を考慮した実装上の注意がある。
- 多くの処理で「ルックアヘッドバイアス防止」の設計原則を採用（datetime.today() 等を直接参照しない）。
- 一部の処理（例: price が欠損のときのエクスポージャー算出や前日終値フォールバック）に将来的な拡張の TODO コメントあり。

Deprecated
- なし（初期リリースのため該当なし）。

Fixed
- なし（初期リリースのため該当なし）。

Breaking Changes
- なし（初期リリースのため該当なし）。

---- 

注: 上記は提供されたコードベースから推測してまとめた CHANGELOG です。実際のリリースノート作成時はコミット履歴やリリース方針に基づき適宜調整してください。