CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトのバージョニングは SemVer に従います。

[Unreleased]
-------------

（現在なし）

[0.1.0] - 2026-03-21
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」の基盤となる主要モジュールを実装しました。主な追加・設計上のポイントは以下の通りです。

Added
- パッケージ基礎
  - パッケージ初期化 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - パブリック API として data, strategy, execution, monitoring を公開。
  - strategy パッケージの公開関数 build_features / generate_signals をエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env ファイルのパースロジックを詳細に実装（export プレフィックス、クォート、インラインコメント処理、保護された OS 環境変数等）。
  - Settings クラスを導入し、J-Quants トークンや Kabu ステーション設定、Slack、DB パス、環境（development/paper_trading/live）やログレベルの検証を提供。
  - デフォルト値（KABUSYS_ENV=development、LOG_LEVEL=INFO、DUCKDB_PATH / SQLITE_PATH のデフォルトパス等）を設定。

- データ取得・保存（J-Quants API クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API 呼び出し用の HTTP ラッパーを実装（ページネーション対応）。
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 時は Retry-After を尊重。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。トークン取得関数 get_id_token を用意。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：ページネーション対応のデータ取得関数を追加。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複を排除。
    - fetched_at を UTC ISO8601 で記録。
    - 入力の基本的な型変換ユーティリティ _to_float / _to_int を実装。
    - PK 欠損行をスキップし、その件数をログで警告。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する基盤を実装。
  - セキュリティ対策を考慮：
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - HTTP/HTTPS スキームのみ許可等の SSRF 対策、受信サイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS 対策。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）やテキスト正規化処理を実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ先頭で生成する方針（冪等性確保）。
  - 大量挿入に対応するチャンク化を導入。

- 研究（research）モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR 等）を計算。
    - ビジネスルール（MA200 必要行数チェック、ATR の true_range 計算ルール、窓サイズとスキャン範囲のバッファ等）を明確化。
  - feature_exploration.py:
    - calc_forward_returns：ターゲット日から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic：Spearman ランク相関（IC）を計算。サンプル不足時の None 処理。
    - factor_summary / rank：ファクター統計量・ランク付けユーティリティを実装（同順位は平均ランク、浮動小数点丸め対応）。
  - research パッケージの __all__ を設定して主要関数を公開。

- 戦略（strategy）モジュール (src/kabusys/strategy/)
  - feature_engineering.py:
    - 研究側の生ファクターを結合、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリップを実行。
    - DuckDB の features テーブルへの日付単位 UPSERT（トランザクション + バルク挿入で原子性確保）。
    - ルックアヘッドバイアス回避の設計（target_date 時点のデータのみ使用）。
  - signal_generator.py:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や逆転処理（例: PER）で正規化。
    - デフォルト重みと閾値を持ち、ユーザ渡し weights の検証・補完・リスケーリングを実装。
    - Bear レジーム（ai_scores の regime_score 平均 < 0）検出で BUY を抑制するロジック。
    - BUY シグナルは閾値超過で生成。SELL シグナルはストップロス（終値/avg_price -1 < -8%）およびスコア低下で判定。SELL 優先ポリシーを適用して signals テーブルに日付単位で書き込み（トランザクションで原子性確保）。
    - 欠損コンポーネントは中立値 0.5 で補完する方針。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- ニュース収集で defusedxml を使用して XML 関連攻撃を軽減。
- ニュース収集で受信サイズ制限・URL 正規化・スキーム検査などを導入して SSRF / DoS 等のリスク低減を図る。
- J-Quants クライアントは 401 時にトークン自動リフレッシュを行うが、無限再帰を避けるため allow_refresh フラグで制御。

Notes / Design decisions
- Look-ahead bias を避ける設計が随所に反映されています（取得時刻の記録、target_date 以前の最新値のみ参照、研究コードと実行層の分離など）。
- DuckDB を中心に SQL ウェイトで集計処理を行い、パフォーマンスを考慮した窓幅・スキャン範囲のバッファを採用。
- 保存処理は基本的に冪等化（ON CONFLICT）しており、再実行可能な設計です。
- execution パッケージは存在するが現時点でファイルは空（発注層の実装は今後の予定）。

既知の制限・未実装事項
- 一部戦略ロジック（例: トレーリングストップ、時間決済）については positions テーブルに追加情報（peak_price / entry_date 等）が必要であり、未実装である旨がコメントに記載されています。
- data.stats.zscore_normalize 実装は別モジュールに依存している（本リリースでは参照している形）。
- monitoring 周りの実装はまだ整備中の可能性があります（__all__ に monitoring を公開しているが実装状況に依存）。

将来のリリースでの予定（例）
- execution 層の実装（kabuステーション API との連携、注文管理）
- より詳細なテスト・例外処理の強化、メトリクス／監視機能の追加
- モデル重み・閾値の A/B テスト／自動最適化基盤の追加

署名
- KabuSys 開発チーム