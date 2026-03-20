CHANGELOG
=========

すべての変更は「Keep a Changelog」の形式に準拠して記載しています。  
各リリースは安定性・再現性・セキュリティを重視した設計方針に基づいて実装されています。

Unreleased
----------

- （現時点の開発中変更はここに記載してください）

0.1.0 - 2026-03-20
-----------------

初期リリース — KabuSys の基本コンポーネントを実装しました。主な追加点は以下の通りです。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開 API: data, strategy, execution, monitoring を __all__ でエクスポート（execution はプレースホルダ）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env 行パーサ: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
  - protected keys を考慮した上書き制御（OS 環境変数を保護）。
  - Settings クラス: J-Quants / kabu API / Slack / データベースパス（duckdb/sqlite） / 環境種別・ログレベル検証（許容値チェック）等のプロパティを提供。
  - is_live / is_paper / is_dev のユーティリティプロパティを追加。
- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（ベース URL, レート制限, ページネーション対応）。
  - 固定間隔レートリミッタ（120 req/min）と共有トークンキャッシュ実装。
  - 再試行（指数バックオフ、最大 3 回）を実装。408/429/5xx をリトライ対象とし、429 の Retry-After を尊重。
  - 401 受信時はリフレッシュトークンで自動的にトークンを更新して 1 回リトライ。
  - fetch_* 系: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
  - save_* 系: raw_prices / raw_financials / market_calendar への保存関数を実装（DuckDB への冪等保存、ON CONFLICT DO UPDATE）。
  - データ型変換ユーティリティ（_to_float / _to_int）と PK 欠損行スキップでの警告ログ。
  - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスの可視化をサポート。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集実装（デフォルトソース: Yahoo Finance）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、小文字化、フラグメント除去）。
  - 記事 ID は正規化 URL の SHA-256 を用いたハッシュ（先頭 32 文字）で生成し冪等性を保証。
  - defusedxml による XML パースで安全性向上（XML Bomb 等への対策）。
  - SSRF 対策や受信サイズ上限（MAX_RESPONSE_BYTES=10MB）などの防御策を導入。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）とトランザクションでの効率的挿入、INSERT RETURNING 相当の挿入件数取得方針。
- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均の乖離）を算出。必要行数不足時は None。
    - Volatility: ATR（20日平均 true range）/ atr_pct、avg_turnover、volume_ratio を算出。必要行数不足時は None。
    - Value: 最新財務情報（raw_financials）と prices_daily を組み合わせて PER / ROE を算出。
    - SQL とウィンドウ関数を活用し、DuckDB のみを参照（外部依存なし）。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装。
    - calc_forward_returns は複数ホライズン（デフォルト [1,5,21]）に対応し、ホライズン検証（1〜252 営業日）を実施。
    - calc_ic は Spearman の ρ（ランク相関）を計算し、サンプル不足時は None を返す。
    - rank は同順位の平均ランクを採用（丸めによる ties 対応あり）。
    - factor_summary は count/mean/std/min/max/median を算出。
  - すべて標準ライブラリと DuckDB のみを使用（pandas 等に依存しない設計）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。
    - research モジュールの生ファクターを取得（calc_momentum / calc_volatility / calc_value）。
    - ユニバースフィルタ（最小株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化: zscore_normalize を使用して指定列を Z スコア化し ±3 でクリップ。
    - features テーブルへ日付単位の置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性を保証。
    - 価格取得は target_date 以前の最新価格を参照し、休場日や当日の欠損に対応。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features と ai_scores（および positions / prices_daily）を参照して最終スコア final_score を計算。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news を個別に計算（シグモイド変換等）。
    - 欠損コンポーネントは中立値 0.5 で補完し、不当な降格を防止。
    - 重みのマージ / 検証 / 正規化処理を実装（未知キーや無効値は無視、合計が 1 でない場合は再スケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル閾値あり）。
    - BUY 条件: final_score >= threshold（Bear 時は抑制）。SELL 条件: ストップロス（-8%）またはスコア低下。
    - SELL 対象は BUY から除外（SELL 優先ポリシー）。signals テーブルへ日付単位の置換で書き込み（トランザクション）。
    - ロギングと欠損データに対する安全ガード（価格欠損時の SELL 判定スキップ等）。
- 設計上の注力点
  - ルックアヘッドバイアス防止: target_date 時点の知識のみを利用する実装方針を明確化。
  - 冪等性・原子性: DB 書き込みは日付単位の置換を基本とし、トランザクションとバルク挿入で実現。
  - フェイルセーフ: 入力値検証（horizons, env 値等）、欠損データの扱い（None / ログ出力）を丁寧に実装。
  - セキュリティ対策: defusedxml、SSRF を想定した URL チェック、受信サイズ制限、環境変数上書き保護など。

Notes / 未実装・将来実装予定
- signal_generator の trailing stop（トレーリングストップ）と time-based exit（保有 60 営業日超過）は positions テーブルに peak_price / entry_date 等の情報が必要なため、将来的に実装予定（コード内にコメント記載）。
- research / strategy によるさらなるチューニング、ユニットテストの充実、モニタリング機能の追加を予定。

Fixed
- なし（初期リリース）

Changed
- なし（初期リリース）

Removed
- なし（初期リリース）

Security
- ニュースパーサで defusedxml を使用し XML ベース攻撃を軽減。
- RSS URL の正規化・検証、受信サイズ上限により SSRF / メモリ DoS のリスクを低減。
- .env 読み込みはプロジェクトルート検出に基づき、OS 環境変数を保護する設計。

Authors
- 開発チーム（コードベースの実装に基づき自動生成した変更記録）

ライセンスやバージョニング方針に関する情報は、プロジェクトの README / pyproject.toml を参照してください。