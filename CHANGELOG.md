# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはコードベース（初期実装）から推測して作成した変更履歴です。

なお、バージョンはパッケージの src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

## [Unreleased]


## [0.1.0] - 2026-03-20
初回リリース — 基本的なデータ取得・保存、研究用ファクター計算、特徴量生成、シグナル生成のコア機能を実装。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。公開 API: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読込する機能を実装。
  - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント等に対応）。
  - 自動ロードの抑止用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別・ログレベル検証等）。
  - デフォルトの DB パス（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）を用意。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の Retry-After を尊重。
  - 401 受信時はリフレッシュトークンを用いた自動 id_token リフレッシュを 1 回行う仕組み。
  - ページネーション対応のデータ取得（株価日足、財務データ、マーケットカレンダー）。
  - DuckDB への冪等保存関数を実装（raw_prices / raw_financials / market_calendar）。ON CONFLICT DO UPDATE を使用。
  - 取得時刻 (fetched_at) を UTC ISO8601 で記録し、Look-ahead バイアス対策を考慮。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集モジュールを実装（デフォルトソースに Yahoo Finance を含む）。
  - defusedxml を使った安全な XML パース（XML Bomb 等への対策）。
  - 受信サイズ上限（10 MB）や SSRF・非 HTTP(S) スキームの検討、安全な URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を保証。
  - DB へのバルク挿入をチャンク化して実行（INSERT RETURNING を前提にした設計）。
  - テキスト前処理（URL 除去、空白正規化）等を含む記事整形ロジック。

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials から計算。
    - 営業日ベースの窓・集計、データ不足時の None ハンドリング、スキャン日数バッファを考慮した実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを同時に取得、入力検証（horizons の範囲制限）。
    - IC 計算（calc_ic）: Spearman（ランク相関）計算の実装、最小サンプル数チェック。
    - factor_summary / rank 等の統計ユーティリティ（同順位は平均ランク、丸めによる ties 対策）。
  - research/__init__.py で主要関数をエクスポート。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research 側で計算した生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 指定カラムを Z スコアで正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - features テーブルへ日付単位の置換（DELETE + bulk INSERT）でトランザクショナルかつ冪等に保存。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して最終スコア（final_score）を算出。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）を計算。シグモイド変換等を使用。
  - 重み付けのサポート（デフォルト重みを持ち、ユーザー指定でフォールバック・正規化）。
  - Bear レジーム判定（ai_scores の regime_score の平均が負でかつサンプル数閾値以上で検出）により BUY を抑制。
  - BUY シグナル閾値（デフォルト 0.60）を超える銘柄に BUY を生成、SELL は保有ポジションに対してストップロス（-8%）およびスコア低下で判定。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を確保。
  - エッジケース（価格欠損・features 未登録の保有銘柄）に対するロギングと安全対策を実装。

- strategy/__init__.py で build_features / generate_signals を公開。

### Security
- ニュース処理に defusedxml を利用して XML による攻撃を軽減。
- ニュース URL 正規化とトラッキング除去、HTTP(S) 制限、受信サイズ上限を設けて SSRF やメモリ DoS を低減。
- J-Quants クライアントはトークン管理とリトライロジックを備え、認証失敗時の挙動を制御。

### Notes / Limitations
- positions テーブルに peak_price / entry_date 等の追加フィールドがないため、トレーリングストップや保有日数ベースの時間決済は未実装（signal_generator 内で注記あり）。
- research/strategy モジュールは DuckDB のテーブル（prices_daily / raw_financials / features / ai_scores / positions 等）を前提とする。外部 API への依存は最小化しており、ルックアヘッドバイアス防止の設計がなされている。
- execution および monitoring パッケージは名前空間として存在するが、実装は今回のコードベースでは最小または未実装（将来の拡張を想定）。
- zscore_normalize は kabusys.data.stats から提供される前提。外部ライブラリ（pandas 等）に依存しない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

----

今後のリリースで想定される追加点（例）
- execution 層の実装（発注処理・kabu API 統合）
- モニタリング用 DB / UI の拡張
- テストカバレッジ・CI の追加
- トレーリングストップや保有日数ベースのエグジット条件の実装
- パフォーマンス改善（大規模データでの DuckDB クエリ最適化、並列取得）

※ この CHANGELOG はコードの内容から推測して作成したドキュメントです。実際のリリースノートとして利用する際は、実装差分やコミット履歴を基に適宜調整してください。