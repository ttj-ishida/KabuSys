# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [0.1.0] - 2026-04-09

初回リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。
  - 公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - オートロードの探索はパッケージ内のファイル位置を起点に親ディレクトリで `.git` または `pyproject.toml` を探す（カレントワーキングディレクトリに依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local (override) > .env（override=False）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - OS 環境変数は protected として上書きを防止。
  - .env パーサーは `export KEY=val`、クォート、エスケープ、インラインコメントを考慮して堅牢に実装。
  - 設定アクセス用 `Settings` クラスを提供（プロパティベース）。
    - J-Quants / kabuステーション / LINE API / DB パス等の設定プロパティを提供。
    - デフォルト値を多数設定（例: `KABU_API_BASE_URL`, `DUCKDB_PATH`, `SQLITE_PATH`, 各種閾値など）。
    - 環境変数の必須チェックを `_require()` で実施（未設定時は ValueError を送出）。
    - `PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_ENV` (`development`/`paper_trading`/`live`) と `LOG_LEVEL` のバリデーション。
    - ランタイム判定プロパティ: `is_live`, `is_paper`, `is_dev`。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定・重み算出モジュール（portfolio_builder）
    - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分を提供。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
    - すべて純粋関数（DB 参照なし）。
  - リスク調整（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーが閾値（デフォルト 30%）を超える場合、新規候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告ログ）。
    - 純粋関数、DB 参照なし。
  - ポジションサイジング（position_sizing）
    - calc_position_sizes: 以下をサポートする株数算出ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score"。
      - risk_based: リスク許容率（risk_pct）と stop_loss_pct から目標株数を計算。
      - equal/score: 重み w を用いた個別割当（portfolio_value * w * max_utilization）。
      - lot_size（単元）で丸め、単元ごとの端数処理を行う。
      - per-stock 上限（max_position_pct）適用。
      - aggregate cap: 合計投下額が available_cash を超える場合はスケールダウンし、残余キャッシュで端数優先順（fractional remainder）に lot 単位で追加配分する（再現性のため tie-break に code を使用）。
      - cost_buffer により約定コストを保守的に見積もる。
    - 純粋関数、DB 参照なし。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily を用いて計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials と prices_daily を用いて PER / ROE を計算（EPS が 0 または欠損の場合は None）。最新の財務レコードを target_date 以前で取得。
    - いずれも DuckDB 接続を受け取り SQL ベースで高速実行。
  - feature_exploration:
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）先の将来リターンを計算。horizons の検証あり（正の整数かつ <=252）。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。データが 3 件未満や分散ゼロの場合は None。
    - rank: 同順位は平均ランクを与えるランク変換。丸め（round(..., 12)）で ties の誤検出を抑制。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 外部依存（pandas など）を使用せず、標準ライブラリのみで実装。

- AI 機能（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を取得。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄につき最大 10 記事・3000 文字にトリム。
    - OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を使用し、応答の厳密な JSON パースとバリデーションを実施。
    - 429・ネットワーク断・タイムアウト・5xx の場合は指数バックオフでリトライ（最大回数設定）。
    - スコアは ±1.0 にクリップ。バリデーション不能やエラー発生時は該当チャンクをスキップして継続（フェイルセーフ）。
    - ai_scores テーブルへは対象コードのみを絞って DELETE → INSERT（トランザクション）することで部分失敗時の保護を実現。DuckDB executemany の仕様に配慮して空パラメータは送らないガードあり。
    - 時間窓計算（calc_news_window）: target_date を基準に JST の前日 15:00 〜 当日 08:30 を UTC に変換して使用（ルックアヘッドバイアス回避のため日付関数を直接参照しない設計）。
  - レジーム判定（regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースの抽出はキーワードマッチ（複数キーワードを ILIKE 条件で検索）で最大 20 件を使用。
    - LLM 呼び出しは独立実装で JSON Mode を使用。API 失敗時は macro_sentiment=0.0 でフォールバックし処理を継続（フェイルセーフ）。
    - レジームスコアは合成後クリップし閾値でラベル付け。結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策（prices_daily は date < target_date の排他条件など）を厳密に実装。

- 監視データ永続化（kabusys.monitoring.monitoring_db）
  - SQLite を使った監視ログの永続化レイヤを追加。
  - `init_monitoring_db(conn)` により以下を冪等で作成:
    - system_status テーブル（CPU/Memory/Disk/プロセス状態）
    - trade_logs テーブル（ログ・約定情報）
    - positions テーブル（現在ポジション）
    - risk_logs テーブル（スキーマ定義の追加箇所あり：ファイル途中まで実装）
    - 必要なインデックスを含むスクリプトを実行

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 `OPENAI_API_KEY` から解決。未設定時は ValueError を発生させ明示的に対処する設計。
- .env ロード時に OS 環境変数を保護（protected set）して誤った上書きを防止。

### Notes / Implementation details
- 多くの関数は「純粋関数」設計（特にポートフォリオ関連）で副作用を持たずテストしやすい形にしている。
- DuckDB を前提とした SQL ベース実装によりオンメモリでの高速集計を想定。
- 時刻・日付扱いはルックアヘッドバイアス対策を重視しており、内部で日付の「現在時刻」を直接参照しない設計を採用している。
- 一部モジュール（monitoring_db）のファイルは途中までの実装が含まれている（スキーマの続きがファイル末尾付近に続く想定）。

もし詳しい差分（ファイル別の変更理由や設計ドキュメントの参照箇所等）をCHANGELOGに追加したい場合は、どのセクションにどの程度の詳細を載せるか指示してください。