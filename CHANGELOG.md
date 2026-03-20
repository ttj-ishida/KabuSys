CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

バージョニングは https://semver.org/ に従います。

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システムのコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: kabusys v0.1.0 を導入。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定をロードする自動読み込み機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して行う（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env の行解析は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなど複数ケースに対応。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack 設定、DB パス、環境 (development/paper_trading/live) やログレベルのバリデーション等をプロパティ経由で取得可能。

- データ取得 / 永続化 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - 日足 / 財務データ / 取引カレンダー取得 API を実装（ページネーション対応）。
    - レート制限（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx をリトライ対象に。
    - 401 を受けた場合はリフレッシュトークンで id_token を自動更新して一度だけリトライ。
    - データ取得時の fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT による冪等保存を行う。
    - 型変換ユーティリティ _to_float / _to_int を提供。変換に失敗したレコードは None にし、PK 欠損行をスキップして警告を出力。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィードからのニュース取得と raw_news テーブルへの冪等保存（ON CONFLICT DO NOTHING）を実装するための基盤。
    - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
    - defusedxml を利用して XML 関連の脆弱性を軽減。
    - 外部 URL の正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去、クエリソート）を実装。
    - レスポンスの最大受信バイト数（10MB）制限、チャンク化によるバルク INSERT の最適化など DoS 対策を実施。
    - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を登録。

- リサーチ用モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）の計算を実装。必要な履歴範囲のスキャン最適化済み。
    - volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio を計算。true_range の NULL 伝播制御あり。
    - value: latest 財務データを prices_daily と組み合わせて PER / ROE を算出（EPS が 0 / 欠損の場合は None）。
    - いずれも DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API には依存しない設計。
  - 特徴量探索・統計 (feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日がデフォルト、ホライズンは最大252日以内制約）。
    - Spearman ランク相関による IC 計算 calc_ic（欠損除外、サンプル数が 3 未満は None を返す）。
    - rank ユーティリティ（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールが計算した生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）を行い ±3 でクリップして外れ値影響を抑制。
  - features テーブルへ日付単位で置換（削除→挿入）することで冪等性と原子性（トランザクション）を保証。
  - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - コンポーネントはシグモイド等で 0〜1 に変換、欠損コンポーネントは中立値 0.5 で補完。
  - final_score は重み付き和で算出（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定 weights は検証・補正して合計を 1.0 に再スケール。
  - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数 >= 3）：Bear の場合は BUY シグナルを抑制。
  - BUY シグナル閾値デフォルト 0.60。
  - SELL（エグジット）条件:
    - ストップロス: 終値/avg_price - 1 < -8%（優先判定）
    - final_score が threshold 未満
    - positions テーブルの価格欠損や features 未登録の保有銘柄に対する挙動（警告／score=0 として SELL）を考慮。
  - signals テーブルへ日付単位の置換で冪等保存。SELL は BUY から除外して優先的に扱う。

### 変更 (Changed)
- （初版のため変更履歴なし）

### 修正 (Fixed)
- （初版のため修正履歴なし）

### 注意点 / 既知の制限 (Known Issues / Notes)
- positions テーブルに peak_price / entry_date 等の追加がないため、トレーリングストップや時間決済（保有60営業日超）等はいまの実装では未対応。関連の TODO コメントあり。
- calc_forward_returns のホライズンは営業日ベース（連続レコード数）で扱う設計。カレンダー日での不足を吸収するためにスキャン範囲にバッファを確保しているが、完全一貫性については利用者側で確認が必要。
- news_collector は RSS パースや URL 正規化を備えているが、実際のドメインホワイトリスト／SSRF 統制は利用環境に応じて追加を推奨。
- J-Quants API クライアントは最大リトライ回数を設けており、429 の場合は Retry-After 優先等の処理を行うが、極端なレート超過状況では呼び出し側での追加レート制御が望ましい。
- .env パーサは多くのケースに対応するが、極端に特殊な .env 構文（複雑な複数行クォート等）は未サポート。

### セキュリティ (Security)
- news_collector は defusedxml を使用して XML ベースの攻撃を軽減。
- J-Quants クライアントは ID トークンのキャッシュと自動リフレッシュを実装（401 の自動処理）、ただしトークン管理は安全な環境で行うこと。
- .env 自動ロードはテスト等で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 互換性 / マイグレーション (Migration notes)
- 初版のため互換性の破壊は無し。将来バージョンで positions テーブルのスキーマ拡張（peak_price 等）を行う可能性があるため、戦略層の永続テーブルスキーマの変更に注意。

---

今後の予定（非包括的）
- trailing stop / 時間決済などエグジット条件の追加実装。
- ai_scores の生成パイプライン（NLP/ニュース分析）や Slack 通知等の monitoring / execution 層との統合強化。
- performance 最適化とテストカバレッジの拡充。