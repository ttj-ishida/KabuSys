Changelog
=========

すべての注目すべき変更履歴をここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマットの説明・慣例:
- セクションは Unreleased / リリースバージョン（[x.y.z] - YYYY-MM-DD）で分けます
- 各リリース内は Added / Changed / Fixed / Security / Deprecated / Removed / Notes 等で整理します

Unreleased
----------
（なし）

[0.1.0] - 2026-03-20
-------------------
Added
- 初期リリース: KabuSys 日本株自動売買システムのベース機能を実装。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、環境変数から設定値を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABUSYS_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、データベースパス（DUCKDB_PATH, SQLITE_PATH）等の既定値。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL（DEBUG/INFO/...）の検証ロジック。
- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - 固定間隔レートリミッタ（120 req/min）を実装（内部クラス _RateLimiter）。
    - リトライ（指数バックオフ）を実装（最大 3 回、408/429/5xx を再試行対象）。429 に対して Retry-After を優先。
    - 401 受信時の自動トークンリフレッシュ（1 回だけ）とキャッシュ化された ID トークンの共有。
    - ページネーション対応の fetch_* API（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数群（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE を用いた upsert。
    - 型安全な変換ユーティリティ _to_float / _to_int を実装（不正値は None）。
  - ログ出力（info/warning/debug）で操作をトレース。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集用モジュールを実装（設計に基づいた実装を含む）。
  - URL 正規化ロジックを実装:
    - トラッキングパラメータ（utm_* 等）の削除、スキーム/ホストの小文字化、フラグメント削除、クエリパラメータのソート。
  - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、XML パースに defusedxml を使用して安全性を向上。
  - 記事 ID を正規化 URL の SHA-256 ハッシュで生成する設計（冪等性を確保）。
  - バルク INSERT をチャンク化してパフォーマンス・SQL 長制限を配慮。
- リサーチ（kabusys.research）
  - ファクタ計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算（窓関数利用）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播を考慮）。
    - calc_value: raw_financials の最新報告を用いて PER / ROE を計算。
    - 計算は target_date 時点のデータのみを使用（ルックアヘッドバイアス対策）。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を実装（有効サンプル数が少ない場合は None を返す）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク計算を実装（丸めによる tie 検出安定化）。
  - zscore_normalize を外部に公開（kabusys.data.stats 経由で利用）。
- 戦略層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
    - research モジュールから取得した生ファクターを結合し、ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化し ±3 でクリップ。features テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を保証。
  - シグナル生成（kabusys.strategy.signal_generator）:
    - features と ai_scores を組み合わせ、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントはシグモイド変換／補完（欠損は中立 0.5）を適用。
    - 最終スコア final_score を重み付け合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。外部から weights を与え可能で、入力検証/再スケールを行う。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプルがある場合）により BUY シグナルを抑制。
    - BUY シグナル閾値のデフォルトは 0.60。SELL シグナル（エグジット）はストップロス（-8%）とスコア低下で判定。SELL は BUY より優先して排除。
    - signals テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を保証。
- トランザクション・障害耐性
  - features / signals など DB 書き込みは BEGIN/COMMIT/ROLLBACK を使用。ROLLBACK 失敗時は警告ログを出力して例外を再送出。
- 設計方針
  - ルックアヘッドバイアスを防ぐために計算は target_date の時点で利用可能なデータのみを使用。
  - DuckDB を主要な分析用 DB として採用。外部依存（pandas 等）を避け標準ライブラリ + duckdb で実装する方針。

Security
- ニュース XML パースに defusedxml を使用し、XML 攻撃（Billion laughs 等）対策を講じている。
- news_collector は受信サイズ制限や URL 正規化（トラッキング除去）など、情報収集時の安全設計を導入。

Notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックされます。未設定の場合は起動時に ValueError を発生します。
  - .env.example を参照して .env を作成してください。
- 自動 .env 読み込み:
  - プロジェクトルートの特定に失敗した場合（.git/pyproject.toml が見つからない）や KABUSYS_DISABLE_AUTO_ENV_LOAD を設定した場合は自動読み込みをスキップします。ユニットテストなどで無効化可能です。
- DB デフォルトパス:
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
- ログレベルと実行環境:
  - KABUSYS_ENV は development / paper_trading / live のいずれか。is_live/is_paper/is_dev で判定可能。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかで検証されます。
- 外部 API の注意:
  - J-Quants API のレート制限（120 req/min）に合わせた実装です。運用時は API 利用ルールに従ってください。

Deprecated
- なし

Removed
- なし

Breaking Changes
- 初期リリースのため該当なし

今後の予定（短期）
- news_collector のさらなる堅牢化（SSRF/ホスト検証等の追加）
- positions テーブルの拡張（peak_price / entry_date 等）を追加してトレーリングストップや時間決済の実装
- テストカバレッジと CI の強化

問い合わせ・貢献
- 不具合報告や改善提案は Issue を立ててください。README / ドキュメントに沿った PR を歓迎します。

以上。