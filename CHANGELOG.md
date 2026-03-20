# Changelog

すべての注目すべき変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

最新バージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買プラットフォーム "KabuSys" の基盤機能を実装。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名 kabusys、バージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開 API に data, strategy, execution, monitoring を含めるエクスポート設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定: `.git` または `pyproject.toml` を基準に探索することで、CWD に依存しない自動ロードを実現。
  - .env パーサーを強化:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの扱い、クォートなしのコメント認識のルールを提供。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を実装（テスト用途）。
  - 設定クラス `Settings` を提供（J-Quants, kabuステーション, Slack, DB パス, 環境判定等）。
  - 各種検証: `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェック、必須環境変数未設定時の明示的エラー。

- データ取得 / 保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
  - API レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を導入。
  - リトライロジック（指数バックオフ、最大 3 回）を実装（408/429/5xx を再試行）。429 に対しては `Retry-After` を尊重。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）と ID トークンのモジュールレベルキャッシュを実装。
  - ページネーション対応のデータ取得（株価・財務・カレンダー）。
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE による上書き。
  - データ変換ユーティリティ `_to_float` / `_to_int` を実装し、不正値は安全に None に変換。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を収集して raw_news に保存する処理を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）を実装（メモリ DoS 対策）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
    - SSRF 等を考慮した URL スキームチェックの設計方針（実装コメント）。
  - バルク INSERT のチャンク化による DB オーバーヘッド低減。
  - デフォルト RSS ソースを定義（例: Yahoo Finance）。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算・探索用ユーティリティ群を実装。
  - ファクター探索:
    - 将来リターン計算 `calc_forward_returns`（horizons デフォルト [1,5,21]、営業日ベースのリード/ラグを用いる）。
    - Information Coefficient（Spearman の ρ）計算 `calc_ic`（ランク相関、同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - ランキングユーティリティ `rank`（同順位を平均ランクで処理、丸めで ties 判定を安定化）。
  - ファクター計算 (`kabusys.research.factor_research`):
    - Momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日 MA、データ不足時は None）。
    - Volatility: 20 日 ATR、atr_pct、avg_turnover、volume_ratio（true_range の NULL 伝播を適切に管理）。
    - Value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新レコードを取得）。
  - DuckDB を用いた SQL＋Python の設計（外部 API に依存しない）。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究モジュールで計算した raw factors をマージして特徴量を作成する `build_features` を実装。
  - 処理フロー:
    1. calc_momentum / calc_volatility / calc_value から生ファクター取得
    2. ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）適用
    3. 指定列の Z スコア正規化（zscore_normalize を利用）および ±3 でクリップ
    4. features テーブルへ日付単位の置換（BEGIN / DELETE / INSERT / COMMIT）で冪等性と原子性を保証
  - 欠損値や外れ値に対する対処が組み込まれている。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - features と ai_scores を統合して最終スコア final_score を計算し、BUY/SELL シグナルを生成する `generate_signals` を実装。
  - 実装の主な仕様:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10（合計が 1.0 でない場合はリスケール）。
    - BUY 閾値のデフォルトは 0.60。
    - コンポーネントスコア:
      - momentum: momentum_20/60, ma200_dev をシグモイド平均化
      - value: PER を 20 を基準にした 1/(1+per/20) マッピング（per が不正な場合は None）
      - volatility: atr_pct の Z スコアを反転してシグモイド化
      - liquidity: volume_ratio をシグモイド化
      - news: ai_score をシグモイド化（未登録は中立）
    - None のコンポーネントは中立値 0.5 で補完（欠損銘柄の不当な降格を防ぐ）
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、かつサンプル数が規程以上（デフォルト 3 件）なら Bear と判定し BUY を抑制
    - SELL 条件:
      1. ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      2. スコア低下: final_score が閾値未満
    - 保有ポジションに関する情報は positions テーブルから取得し、SELL 判定は価格欠損時にスキップする安全化ロジックを含む
    - signals テーブルへ日付単位の置換で挿入（冪等）

- データ層共通
  - DuckDB を主要なオンディスクデータベースとして利用する設計（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等を想定）。

### 変更 (Changed)
- 初回リリースのため既存コードとの互換性に関する変更履歴はなし。

### 修正 (Fixed)
- 初回リリースのため修正履歴はなし。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要な以下の機能）:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
- news_collector のネットワーク/SSRF 低レベルチェックの実装は設計方針として記載されているが、実運用での追加検証やホワイトリスト運用を推奨。
- execution パッケージは現状空のプレースホルダ（発注ロジックは別途実装予定）。
- monitoring は __all__ に含まれるが、監視・アラート実装は今後の追加予定。

### セキュリティ
- RSS の XML パースに defusedxml を利用し、XML ベースの攻撃に備える。
- J-Quants クライアントはトークン自動更新とレート制限を実装し、認証失敗時やレート超過時の安全な再試行を行う設計。
- .env 自動ロード処理は OS 環境変数を保護するため上書き保護の仕組みを導入（読み込み時に protected set を使用）。

### 互換性（Breaking Changes）
- 初回リリースのため破壊的変更はなし。

---

今後のリリースでは、execution 層（実際の発注ロジック）、monitoring（メトリクス・アラート）、AI スコア生成パイプライン、及び追加のエグジット戦略/リスク管理機能の実装を予定しています。必要であれば、各モジュールの詳細な変更点（関数レベルの説明）も別途記載します。