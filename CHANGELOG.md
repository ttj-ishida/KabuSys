# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-03-21

初回リリース。パッケージ名: kabusys (日本株自動売買システム)。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- 基本パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを "0.1.0" に設定。パッケージ公開用のエクスポート: data, strategy, execution, monitoring。

- 環境設定・自動.env ロード (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可能）。
  - .env 行パーサー実装:
    - コメント行・空行無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしの行でのインラインコメント判定（直前が空白／タブの場合に # をコメント扱い）。
  - .env 読み込みの保護機能:
    - OS 環境変数（既存 os.environ のキー）を protected として .env の上書きを制御。
    - .env.local は既存環境を上書き（override=True）するが、protected キーは上書きしない。
  - Settings クラス実装（settings インスタンスを提供）:
    - J-Quants / kabu API / Slack / DB パス等のプロジェクト設定取得プロパティ。
    - 必須キー未設定時は明示的な ValueError を送出。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL 値検証（不正値は ValueError）。
    - duckdb/sqlite のパスを Path として返すユーティリティ。

- データ取得・永続化（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装（認証・ページネーション・再試行・レート制御をサポート）。
  - 固定間隔スロットリング RateLimiter 実装（120 req/min の遵守）。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時にリフレッシュトークンから id_token を取得して 1 回リトライ。
  - fetch_* 関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いて重複を処理
    - fetched_at を UTC ISO8601 で記録
  - 型変換ユーティリティ (_to_float / _to_int) を実装して不正入力を安全に処理。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し raw_news に保存する仕組みを追加。
  - URL 正規化機能実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリパラメータをキーでソート）。
  - defusedxml を使った XML パース（安全対策）、受信サイズ上限（MAX_RESPONSE_BYTES）などドキュメントに基づく設計を導入。
  - 記事IDは正規化 URL の SHA-256 を用いた冪等な生成を想定。
  - バルク INSERT のチャンク処理、ON CONFLICT DO NOTHING による重複排除を想定した設計。

- リサーチ / ファクター計算 (src/kabusys/research/*.py)
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率(ma200_dev) の計算。
    - calc_volatility: 20 日 ATR（atr_20）, 相対 ATR（atr_pct）, 20 日平均売買代金(avg_turnover), volume_ratio の計算。
    - calc_value: 最新の財務データ（raw_financials）を利用した per / roe の計算（price と組み合わせ）。
    - DuckDB の SQL を利用し、営業日欠損やデータ不足に対して None を返す設計。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）での将来リターン計算（LEAD を利用）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（Information Coefficient）計算。
    - factor_summary: カラム毎の count/mean/std/min/max/median を計算。
    - rank: 平均ランク方式による同順位処理（丸めで ties 検出安定化）。
  - research パッケージの __all__ を整備しユーティリティを公開。

- 戦略ロジック (src/kabusys/strategy/*.py)
  - feature_engineering.py:
    - research 側の生ファクターを結合・正規化し features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価 / 20 日平均売買代金）を適用。
    - zscore_normalize を使った Z スコア正規化と ±3 クリップを適用（外れ値対策）。
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性を担保。
  - signal_generator.py:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースをコンポーネントスコアに変換。
    - シグモイド関数で Z スコアを [0,1] に変換、欠損コンポーネントは中立 0.5 で補完。
    - 重み (デフォルト: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10) のバリデーション・再スケール機能を提供。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY を抑制。
    - BUY は閾値（デフォルト 0.60）超の銘柄に対して付与、SELL はストップロス（-8%）およびスコア低下で判定。
    - positions / prices_daily / ai_scores / features を参照して日付単位の置換で signals テーブルへ保存（冪等）。

### 変更 (Changed)
- なし（初回リリースのため既存からの変更点はありません）。

### 修正 (Fixed)
- 環境変数パーサーの堅牢化:
  - export プレフィックス対応、クォート内エスケープ処理、インラインコメント判定など現実的な .env ケースを考慮して実装。
- DuckDB への保存処理で PK 欠損行をスキップし、スキップ件数をログ出力するように実装（データ品質問題を可視化）。

### セキュリティ (Security)
- news_collector で defusedxml を利用した安全な XML パースを採用（XML Bomb 等の防止）。
- news_collector の URL 正規化・トラッキングパラメータ除去・スキーム制限等により SSRF・トラッキングリスクを軽減する設計方針を導入。
- J-Quants クライアントでのタイムアウト・再試行・トークンリフレッシュにより不正な状態からの自動回復を考慮。

### ドキュメント (Documentation)
- 各モジュールに豊富な docstring を追加し、設計意図や処理フロー（ルックアヘッドバイアス回避、冪等性、トランザクション制御等）を明示。

### 既知の制限 / 今後の実装予定 (Known issues / Roadmap)
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 情報が必要であり未実装。
- news_collector の一部実装（ネットワークリクエスト、IP/ホワイトリスト検証、記事パース→DB 保存の完全な実装）は docstring に設計方針が記載されているが、現時点のコードスニペットは一部未完（normalize 関数の続き等）。
- execution / monitoring サブパッケージはパッケージエクスポートに含まれているが（__all__）、公開 API の実体は今後充実予定。

---

作業や追加の差分があれば、この CHANGELOG を更新してください。