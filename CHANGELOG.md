# Keep a Changelog — CHANGELOG.md

すべての注目すべき変更を追跡します。  
このプロジェクトは [Semantic Versioning](https://semver.org/) に従います。

履歴は主にコードベースから推測して作成しています（実装コメント・設計ノートを参照）。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース（ベース実装）

### 追加 (Added)
- 全体
  - Python パッケージ kabusys の初期実装を追加。
  - パッケージバージョン: 0.1.0。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント扱い等に対応）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / ログレベル / 実行環境（development/paper_trading/live）等の取得・検証を行うプロパティを実装。
  - 必須環境変数未設定時に明確な例外を投げる `_require` を実装。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制御（120 req/min）を実装（_RateLimiter）。
  - HTTP リクエスト周りにリトライ（指数バックオフ、最大3回）、429/408/5xx の再試行、429 の Retry-After 優先処理を実装。
  - 401 Unauthorized を検知した場合、リフレッシュトークンから ID トークンを再取得して 1 回だけリトライするロジックを実装（無限再帰防止）。
  - ページネーション対応の取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への永続化関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による冪等性を確保し、取得時刻（UTC）を fetched_at に記録。
  - 入力データの型安全な変換ユーティリティ `_to_float`, `_to_int` を実装。PK 欠損行はスキップして警告出力。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する基礎実装。
  - URL 正規化（スキーム/ホストの正規化、トラッキングパラメータ削除、フラグメント削除、クエリパラメータソート）を実装し、記事 ID の冪等化（ハッシュ化）に利用。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃対策を考慮。
  - 受信サイズ上限（デフォルト 10 MB）やバルクINSERT用チャンクサイズなどの保護を実装。
  - デフォルト RSS ソース（yahoo_finance）を定義。

- 研究系ユーティリティ / ファクター計算 (src/kabusys/research/*.py)
  - factor_research モジュールを実装:
    - モメンタム（mom_1m, mom_3m, mom_6m）、200日移動平均乖離（ma200_dev）
    - ボラティリティ / 流動性（20日 ATR、atr_pct、avg_turnover、volume_ratio）
    - バリュー（per、roe：raw_financials からの直近財務データを使用）
    - DuckDB に対する SQL ベースの計算（営業日ベースの窓、スキャン範囲バッファ等）
  - feature_exploration モジュールを実装:
    - 将来リターン算出（calc_forward_returns、複数ホライズン対応、データ存在チェック）
    - IC（Information Coefficient）計算（スピアマンのランク相関）および rank ユーティリティ
    - factor_summary：各ファクター列の count/mean/std/min/max/median を算出する統計サマリー
  - research パッケージで主要関数をエクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research で計算した生ファクターを統合して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - 指定カラムを Z スコア正規化して ±3 でクリップ（外れ値抑制）。features テーブルへの日付単位置換（トランザクション＋バルク挿入）により冪等性を確保。
  - DuckDB の prices_daily / raw_financials を参照する設計で発注層には依存しない。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum, value, volatility, liquidity, news を計算（シグモイド変換や PER に基づく変換等）。
  - 重み付けのマージ・検証・再スケール処理を実装（デフォルト重みは StrategyModel.md に従う）。
  - Bear レジーム判定（ai_scores の regime_score の平均が負なら Bear。ただしサンプル閾値を設ける）を実装し、Bear 時は BUY を抑制。
  - SELL 判定としてストップロス（-8%）とスコア低下（threshold 未満）を実装。保有ポジションの価格欠損や features 未登録時の挙動を明示。
  - signals テーブルへの日付単位置換による冪等性を確保。

- パッケージ初期エクスポート
  - kabusys.__all__ に data, strategy, execution, monitoring を定義。
  - strategy パッケージで build_features / generate_signals をエクスポート。

### 変更 (Changed)
- 初回リリースのため該当なし（新規追加が中心）。

### 修正 (Fixed)
- データ保存関数は PK 欠損行をスキップしてログに警告を出力するように実装（不正データの安全な扱い）。
- DB 更新時はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保し、ROLLBACK 失敗時は警告を出す処理を追加。

### セキュリティ (Security)
- news_collector で defusedxml を使用して安全な XML パースを行う設計。
- HTTP レスポンスの最大受信バイト数制限（メモリ DoS 対策）。
- J-Quants クライアントは認証トークンの取り扱いを行い、401 時の安全な再取得ロジックを備える。

### 既知の制限・未実装 (Known issues / Unimplemented)
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）はコメントで未実装として明記されている。positions テーブルに peak_price / entry_date 等の情報が必要。
- news_collector の完全な SSRF/IP 保護・接続制限の実装は検討中（コードには ipaddress/socket のインポート等の痕跡あり）。
- 外部依存（pandas 等）を使わずに標準ライブラリ中心で実装しているため、大規模データ処理でのパフォーマンスチューニング余地あり。
- zscore_normalize は kabusys.data.stats に実装されることを前提とする（本差分では参照あり）。

### 開発ノート / 設計上の決定
- DuckDB を中心とした SQL + Python のハイブリッド実装で、研究（research）コードと実行（execution）/発注層は明確に分離。
- ルックアヘッドバイアス対策として、常に target_date 時点またはそれ以前のデータのみを参照する方針を徹底。
- DB 書き込みは日付単位の「全削除→挿入」パターンをトランザクション内で行い、冪等性と原子性を確保。

---

貢献者: コードベース内の実装コメント・設計ノートに基づき自動生成。実際のコミット履歴がある場合は該当履歴に基づく補記を推奨します。