# Changelog

すべての変更は Keep a Changelog の慣習に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

特になし。

## [0.1.0] - 2026-03-21

### Added
- 初期リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - パッケージ構成:
    - kabusys (トップパッケージ)
    - サブパッケージ: data, research, strategy, execution, monitoring（execution/monitoring はプレースホルダ）
    - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - 行パーサ: コメント行、export プレフィックス、クォートされた値とバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 上書き制御（override, protected）をサポートし、OS 環境変数の保護を実現。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/システム環境（KABUSYS_ENV）/ログレベルを取得するプロパティ群を提供。環境値検証（有効な env 値・ログレベル）を実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出し共通処理: 固定間隔のレートリミッタ（120 req/min）、指数バックオフによるリトライ（最大3回）、HTTP ステータスに基づく再試行ポリシー、タイムアウト、JSON デコードエラーハンドリング。
  - トークン管理: リフレッシュトークンから ID トークンを取得する get_id_token、401 受信時の自動リフレッシュ処理（1 回のみ再試行）を実装。モジュールレベルのトークンキャッシュを共有。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（取引カレンダー）
  - DuckDB への保存関数（冪等性を確保する INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - ユーティリティ: 安全な変換関数 _to_float / _to_int を実装。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集と前処理（URL 除去・空白正規化）。
  - セキュリティ対策: defusedxml による XML パース（XML Bomb 等の防御）、HTTP(S) スキームの検証、受信サイズ上限（MAX_RESPONSE_BYTES）。
  - URL 正規化: スキーム/ホストの小文字化、tracking パラメータ除去（utm_* 等）、フラグメント削除、クエリソート。
  - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を担保。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で DB オーバーヘッドを抑制。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。

- 研究用モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。過去スキャン範囲を確保し、データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true range の扱いに注意）・atr_pct・avg_turnover・volume_ratio を計算。
    - calc_value: raw_financials から最新財務情報を参照して PER / ROE を算出（EPS が 0 あるいは欠損の場合は PER を None とする）。
    - 設計方針: DuckDB の prices_daily / raw_financials のみ参照、外部ライブラリ依存なし。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位の平均ランクを返すランク変換ユーティリティ（丸めで ties 検出の安定化）。

- ストラテジー関連 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features: research モジュールの生ファクターを統合し、
      - ユニバースフィルタ（最低株価/最低平均売買代金）適用、
      - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、
      - ±3 でクリップ、
      - features テーブルへ日付単位で置換（削除→挿入、トランザクションで原子性保証）を実行。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals:
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news を重み付けして final_score を計算（デフォルトの重みを定義）。
      - weights の検証・補完・正規化ロジック（未知キーや無効値を無視、合計が 1 になるよう再スケール）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制。サンプル不足時は Bear とみなさない）。
      - BUY シグナルは閾値（デフォルト 0.60）超過で生成、SELL は保有ポジションに対してストップロス（-8%）およびスコア低下で判定。
      - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再割当て。
      - signals テーブルへ日付単位で置換（トランザクションで原子性）。
    - スコア変換・補完ユーティリティ（シグモイド変換、平均化、欠損補完など）を実装。
    - 未実装のエグジット条件（将来的に positions に peak_price / entry_date が必要）を関数内で明示（トレーリングストップ、時間決済）。

- public API エクスポート
  - strategy.build_features, strategy.generate_signals, research の主要関数群、data.stats の zscore_normalize などを __all__ 経由で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース XML パースに defusedxml を使用して XML 関連の攻撃を軽減。
- RSS の受信サイズ上限設定と URL 正規化によりメモリ DoS / SSRF リスクを軽減。
- J-Quants クライアントは 401 自動リフレッシュとレート制御を実装し、不正なリトライや過負荷を抑制。

### Notes / Known limitations
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- research モジュールは外部依存（pandas 等）を使わずに実装しているため、非常に大きいデータセットではパフォーマンス上のチューニングが必要になる可能性がある。
- .env パーサや URL 正規化は一般的だが稀なケース（特殊なクォートや極端なクエリ文字列）で想定外の挙動をする場合がありうる。

---

これらはコードベースから推測して作成した CHANGELOG です。必要であれば各項目をより詳細（ファイルごとの変更差分、関数シグネチャの変更点、テストの追加状況等）に展開します。