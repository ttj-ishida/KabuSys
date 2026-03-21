# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に従います。  

## [Unreleased]

なし

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主な追加点・設計方針・既知の制約です。

### 追加 (Added)
- パッケージ基盤
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を追加。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env の行パーサーを実装。コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
  - OS 環境変数を保護する protected 機能（.env.local の上書き制御）。
  - 必須設定取得の _require() と Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン、DB パスなど）。
  - KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。
- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限制御（固定間隔スロットリング、120 req/min を想定）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を考慮。
  - 401 受信時の自動トークンリフレッシュを実装（1 回のみ再試行）。
  - ページネーション間で使う ID トークンをモジュールキャッシュで共有。
  - fetch_* 系（株価 / 財務 / カレンダー）と、それらを DuckDB に保存する save_* 系関数を実装。保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実行。
  - データ取得時に fetched_at を UTC ISO8601 で記録し、look-ahead bias を追跡可能にする設計。
  - 型変換ユーティリティ (_to_float / _to_int) を実装。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得・正規化し raw_news に保存する機能を実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保。
  - defusedxml を用いた XML パース（XML Bomb 等への対策）、受信サイズ上限（10MB）、HTTP スキーム検証などを実装して各種攻撃を軽減。
  - DB バルク挿入をチャンク化してパフォーマンスと SQL 長制限に配慮。INSERT RETURNING により挿入数を把握。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネス RSS）。
- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離の算出（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: target_date 以前の最新財務データに基づく PER / ROE 計算。
  - feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）。
    - calc_ic（Spearman のランク相関による IC 計算）、rank ユーティリティ。
    - factor_summary（count/mean/std/min/max/median）を実装。
  - research/__init__.py で主要関数をエクスポート。
- 戦略（Strategy）モジュール (src/kabusys/strategy/)
  - feature_engineering.build_features:
    - research の生ファクターを取得し、ユニバースフィルタ（最低株価 / 最低平均売買代金）を適用。
    - 数値ファクターを Z スコア正規化（zscore_normalize に依存）し ±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE → INSERT のトランザクション）を行い冪等性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）などの扱いを実装。
    - 重みの受け取りと検証、合計が 1.0 でなければ再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負）に基づく BUY 抑制。
    - BUY（閾値デフォルト 0.60 以上）および SELL（ストップロス -8% / スコア低下）を生成。
    - positions / prices_daily を参照してエグジット判定を行い、signals テーブルへ日付単位の置換で書き込む。
  - strategy/__init__.py で build_features, generate_signals をエクスポート。
- DuckDB とトランザクション設計
  - 複数箇所で BEGIN/COMMIT/ROLLBACK による原子性保証を実装（features / signals など）。
  - SQL はパフォーマンスを意識したウィンドウ関数・集約を活用。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制約・未実装 (Known issues / TODO)
- execution 層はまだ未実装（src/kabusys/execution/__init__.py は空）。実際の注文送信ロジックは含まれていない。
- signal_generator に記載の「未実装のエグジット条件」：
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- feature_engineering では features に avg_turnover を保存していない（フィルタ用に参照するが features テーブルには含めない）。
- news_collector の RSS ソースはデフォルトが少数で、拡張や失敗耐性の更なる強化が可能。
- rate limiting は固定間隔スロットリング（単純）で、バーストや複雑なトークンバケットには未対応。
- 一部関数は外部ライブラリ（pandas 等）を使わず標準ライブラリで実装しているため、巨大データに対するメモリ/速度の最適化余地がある。
- .env パーサーは多くのケースを考慮しているが、特殊な .env 書式の全網羅は保証しない。

### セキュリティ関連 (Security)
- news_collector で defusedxml を使用し XML 攻撃を抑制。
- ニュース取得で受信サイズ上限を設定（メモリ DoS 対策）。
- URL 正規化とスキーム検証を行い、SSRF のリスク低減を図る。
- config の .env 読み込みでは OS 環境変数を protected として上書き防止する挙動を採用。

### 互換性 (Breaking Changes)
- なし（初回リリース）

---

もし CHANGELOG の内容に補足してほしい点（例: 日付の変更、より細かなモジュール別の差分記述、将来予定のマイルストーン等）があればお知らせください。コードの注釈や TODO コメントに基づき更に細分化して追記できます。