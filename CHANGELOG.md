Keep a Changelog準拠の CHANGELOG.md（日本語）を作成しました。プロジェクトの現状（初期リリース v0.1.0）をコードから推測してまとめています。必要なら日付や貢献者情報の追記・修正を行います。

---
# CHANGELOG

すべての重要な変更はこのファイルに記録します。本プロジェクトはセマンティックバージョニングに従います。

フォーマットは Keep a Changelog に準拠します。  
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-21
初回リリース。以下の主要機能および実装が含まれます。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - モジュールエクスポート: data, strategy, execution, monitoring を公開。

- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - .env ファイルの堅牢なパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数を保護する protected キーセットによる上書き制御。
  - Settings クラスを提供し、環境変数からアプリ設定を安全に取得（必須値チェック、型変換、検証）。
  - サポートされる環境: development, paper_trading, live。ログレベル検証も実装。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限管理（120 req/min、固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
  - ページネーション対応の fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）：
    - ON CONFLICT（重複更新）でのアップサート。
    - fetched_at の UTC 記録、PK 欠損行のスキップ警告。
  - 型変換ユーティリティ _to_float / _to_int を実装（堅牢なパースと不正値除外）。

- ニュース収集（kabusys.data.news_collector）
  - RSS 収集モジュールを追加（デフォルトで Yahoo Finance の RSS を含む）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの正規化、クエリソート、フラグメント除去）。
  - defusedxml による XML パースでセキュアに処理（XML Bomb 対策）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）や SSRF・IP 検査といった安全対策を考慮した設計。
  - 挿入はバルク・チャンク化してパフォーマンス配慮。記事ID に SHA-256 を用いる冪等設計（設計方針に記載）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュールを実装:
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200 日移動平均乖離）。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio。
    - バリュー: per, roe（raw_financials からの最新財務データ参照）。
    - DuckDB 上の SQL を用いた効率的な計算（窓関数使用）。データ不足時の None 処理。
  - feature_exploration モジュールを実装:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、営業日ベースの取扱い）。
    - IC（Information Coefficient）計算（スピアマンの ρ、rank/同順位平均ランク対応）。
    - factor_summary（count/mean/std/min/max/median の統計サマリ）。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties を安定化）。
  - research パッケージのエクスポート整理（calc_momentum, calc_volatility, calc_value, zscore_normalize 等を公開）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で算出した raw factor をマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
  - Zスコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップ。
  - features テーブルへの日付単位の置換（DELETE + INSERT のトランザクションで日付単位の冪等性）。
  - 価格欠損や数値非有限の取り扱いに注意した実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア final_score を計算。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出するユーティリティを実装（シグモイド変換、欠損補完：中立 0.5）。
  - デフォルト重みとしきい値（デフォルト weights、threshold=0.60）を実装。ユーザ指定の重みは検証・正規化。
  - Bear レジーム判定（AI の regime_score 平均が負 → BUY を抑制、サンプル数閾値あり）。
  - SELL シグナル（エグジット）判定:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - スコア低下（final_score < threshold）
    - 価格欠損時は SELL 判定をスキップして誤クローズ防止。
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）。
  - ログ出力と警告により不整合や欠損を可視化。

### 変更
- （初回リリースのため過去変更はなし）

### 修正（バグフィックス）
- （初回リリースのため過去修正はなし）

### 既知の制限 / 未実装の機能
- signal_generator 内の未実装エグジット条件（コメントに明示）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）など
- feature_engineering は per（逆数変換等）は一部の列で特別扱い。将来的な拡張の余地あり。
- news_collector の記事→銘柄紐付け（news_symbols）周りは設計方針に触れているが、詳細実装の確認が必要。
- 外部依存を最小化する設計だが、defusedxml は依存あり（安全上の理由）。その他は標準ライブラリと duckdb を想定。

### セキュリティ
- defusedxml の利用による XML パースの安全化。
- news_collector での受信サイズ上限や URL 正規化 / トラッキング除去、HTTP スキームチェック等による安全対策。
- .env 読み込みで OS 環境変数の保護（protected set）を採用。

---

必要であれば以下を追記できます:
- 実際のリリース日（現在は 2026-03-21 を仮置き）。
- 変更履歴を Unreleased に残す運用ルール。
- 貢献者・クレジット表記。