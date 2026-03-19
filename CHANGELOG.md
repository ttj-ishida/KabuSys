# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
なお、このリポジトリの初回リリースとしてコードベースから推測してまとめています。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-19

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージルートでの __all__ 指定により、data / strategy / execution / monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出（__file__ 基点で探索、CWD 非依存）。
  - .env パーサ実装:
    - export KEY=val 形式対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ対応、インラインコメント処理、クォート無しの # コメント判定の扱い。
  - .env ロード時に OS 環境変数を保護する protected キーセットをサポート（.env.local は override=True）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須チェック（未設定時は ValueError）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
    - データベースパスのデフォルト（duckdb / sqlite）と Path 型変換。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を実装。
    - 冪等なページネーション対応 fetch_* 関数（daily quotes / financial statements / market calendar）。
    - リトライ（指数バックオフ、最大3回）と HTTP ステータスに基づく挙動（408/429/5xx を再試行対象に）。
    - 401 Unauthorized 時は自動でリフレッシュトークンから id_token を取得して 1 回リトライする仕組み。
    - 取得時刻を UTC ISO8601（fetched_at）で保存し、Look-ahead バイアス追跡を可能に。
  - DuckDB 保存関数を提供（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE を用いた重複排除と更新。
    - PK 欠損レコードのスキップと警告ログ。
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換ルール、誤変換防止）。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを実装（デフォルトで Yahoo Finance のカテゴリ RSS をサポート）。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防ぐ。
    - 受信サイズの上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 記事ID は正規化後の URL の SHA-256（先頭32文字）等で生成して冪等性を担保する設計（実装意図を明記）。
    - HTTP/HTTPS 以外のスキーム拒否や SSRF を意識した実装方針。
  - DB 保存はバルク挿入・トランザクションで効率化、INSERT RETURNING を用いて挿入数を正確に取得することを想定。

- リサーチ（ファクター計算・探索） (src/kabusys/research/)
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を DuckDB 上の SQL ウィンドウ関数で実装。
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均）を計算（データ不足時は None）。
    - Volatility: 20 日 ATR（true range の正しい NULL 伝播を考慮）および相対 ATR (atr_pct)、20 日平均売買代金、volume_ratio を計算。
    - Value: raw_financials から target_date 以前の最新財務を取得し PER / ROE を計算（EPS が 0 の場合は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない方針。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを計算（営業日数ベースの LEAD を使用）。
    - calc_ic: Spearman ランク相関（IC）を実装。データ不足（有効サンプル < 3）時は None を返す。
    - rank: 同順位は平均ランクとするランク変換（丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算（None を除外）。
  - research パッケージ __all__ に主要関数を追加して公開。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装:
    - research/factor_research の calc_momentum / calc_volatility / calc_value の出力を統合。
    - ユニバースフィルタを適用（最低株価 >= 300 円, 20 日平均売買代金 >= 5 億円）。
    - 数値ファクターに対する Z スコア正規化（kabusys.data.stats:zscore_normalize を利用）と ±3 でのクリップ。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等性・原子性を保証（トランザクション）。
    - 欠損値や非有限値に対する保護処理。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装:
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
      - momentum: momentum_20 / momentum_60 / ma200_dev の平均（シグモイド変換を挟む）。
      - value: PER を 20 基準で 1/(1 + per/20) に変換（per が不適切なら None）。
      - volatility: atr_pct の Z スコアを反転してシグモイド変換。
      - liquidity: volume_ratio に対するシグモイド。
      - news: ai_score に対してシグモイド（未登録は中立補完）。
    - final_score はデフォルト重み(momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10)の重み付き合算。weights の検証と合計が 1.0 でない場合の再スケールを実装。
    - Bear レジームの判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）で BUY シグナルを抑制。
    - BUY シグナル閾値はデフォルト 0.60。
    - SELL シグナル（エグジット）:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score < threshold
      - positions に関する一部未実装条件（トレーリングストップ / 時間決済）は設計メモとして残す。
    - signals テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等性・原子性を保証。
    - SELL 優先ポリシーにより SELL 対象は BUY から除外し、BUY のランクは再付番。

### 変更 (Changed)
- 新規リリースのため特定の「変更」は無し（初回公開）。ただし設計方針や実装上の注意点をドキュメント文字列やログ出力で明記。

### 修正 (Fixed)
- 該当なし（初回公開）。

### 廃止 (Deprecated)
- 該当なし。

### 削除 (Removed)
- 該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 脆弱性を緩和。
- RSS/URL 処理においてトラッキングパラメータ除去・スキームチェック・受信バイト数制限を実装し、SSRF やメモリ DoS のリスクを低減。
- jquants_client の HTTP エラーハンドリング・トークンリフレッシュ処理により認証エラーや再試行動作を安全に処理。

---

備考:
- 各モジュールには詳細な docstring と設計方針（Look-ahead バイアス防止、冪等性、トランザクションによる原子性、ロギング方針など）が含まれており、実運用での安全性・再現性を重視した設計になっています。
- 一部（news_collector の URL 正規化以降など）はファイルの途中までが提供されていますが、意図・設計は docstring に明記されており、それに沿った実装が行われていることを前提に記載しています。