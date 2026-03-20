# Changelog

すべての注目すべき変更をここに記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-20

### 追加
- パッケージ初期リリース: kabusys 0.1.0
- 基本パッケージ構成
  - モジュール群: data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env パーサ実装
    - export KEY=val 形式に対応、クォート文字列やエスケープ処理、インラインコメントの扱いなどを考慮。
    - 上書き制御（override）および protected（OS 環境変数保護）機構をサポート。
  - Settings クラス
    - 必須設定取得時の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値（KABUSYS_ENV=development, LOG_LEVEL=INFO 等）とバリデーション（env/log_level の許容値チェック）。
    - パス設定（duckdb/sqlite）の Path 変換。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - レート制限 (_RateLimiter): 120 req/min 固定スロットリングを実装。
    - 汎用 HTTP リクエストラッパー (_request): ページネーション対応、JSON パース、リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先、408/429/5xx の再試行対象化。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰を防止）。
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB 保存ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar — ON CONFLICT（冪等）で更新を行う。
    - 型変換ユーティリティ: _to_float / _to_int（文字列や小数表現の扱いに細かなポリシーを実装）。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス対策とトレーサビリティを確保。
    - モジュールレベルで ID トークンをキャッシュし、ページング間で共有。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得・パース（デフォルトソースに Yahoo Finance を含む）。
    - defusedxml を使用して XML 攻撃を防止。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）など DoS 緩和策。
    - URL 正規化: トラッキングパラメータ除去（utm_, fbclid 等）、スキーム/ホストの小文字化、フラグメント除去、クエリソート。
    - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保。
    - DB へのバルク保存はチャンク化と単一トランザクションにより効率化・原子性を保証。

- リサーチ（研究）関連 (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum: mom_1m/mom_3m/mom_6m、200 日移動平均乖離率（ma200_dev）を計算。
    - Volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - Value: PER（price / EPS）、ROE を raw_financials と prices_daily から算出。最新の報告書を銘柄ごとに取得。
    - 各計算は DuckDB のウィンドウ関数を活用して実行（営業日欠損への耐性を考慮）。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - IC 計算 (calc_ic): ファクターと将来リターンの Spearman（順位）相関を計算、サンプル不足時に None を返す。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を返す。
    - rank ヘルパー: 同順位は平均ランクを割り当てる実装（浮動小数丸めで ties の検出を安定化）。
  - research パッケージの __all__ エクスポートを整備。

- 戦略関連 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.py)
    - 研究環境で計算した raw factors を結合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化: 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（DELETE -> INSERT をトランザクションで実行し冪等性を担保）。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - final_score を重み付き和で算出（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - シグナル閾値のデフォルトは 0.60（BUY 判定）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数が閾値未満なら Bear とみなさない）。
    - SELL（エグジット）ロジック: ストップロス（-8%）優先、final_score の閾値未満でエグジットなど。SELL は BUY より優先して排除。
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）。
    - 欠損コンポーネントは中立値 0.5 で補完する方針を採用し、欠測銘柄が過度に不利にならないよう設計。
  - strategy パッケージのエクスポート（build_features, generate_signals）。

- logging / 設計注記
  - 各主要処理は詳細なログ出力を行う（info/warning/debug を適切に使用）。
  - 設計方針として「ルックアヘッドバイアスの防止」「本番発注 API への依存排除」「冪等性の確保」「外部ライブラリ依存の最小化（研究側で pandas などに依存しない）」を明記。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- defusedxml を使用した RSS パースにより XML 関連の脆弱性（XML Bomb 等）に対処。

注: 上記はソースコードの実装内容に基づいて推測した、本リリースで導入された主要な機能・設計上の決定の要約です。実際のリリースノートには利用方法や既知の制限、マイグレーション手順（DB スキーマ等）が別途必要になる場合があります。