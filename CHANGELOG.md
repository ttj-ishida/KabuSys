# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ドキュメントは Keep a Changelog の形式に準拠します。  
この CHANGELOG は提供されたコードベースの内容から推測して作成しています（実装・設計方針の要約を含む）。

## [Unreleased]
- なし（初回リリース: 0.1.0 を参照）

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要機能・設計上の考慮点を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開 API の __all__ 設定）。
- 設定管理
  - 環境変数 / .env ロード機能（kabusys.config）
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）に基づく .env 自動ロード。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - .env 行パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
    - Settings クラスで主要設定値をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境・ログレベル判定など）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。
- データ収集・保存（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - レートリミッタ (_RateLimiter) による固定間隔スロットリング（デフォルト 120 req/min）。
    - 再試行（指数バックオフ、最大試行回数、特定ステータスコードでのリトライ）、429 の Retry-After 優先処理。
    - 401 受信時のトークン自動リフレッシュ（1回のみ）とモジュールレベルの ID トークンキャッシュ共有。
    - ページネーション対応の fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への永続化関数 (save_daily_quotes, save_financial_statements, save_market_calendar) は冪等性を確保（ON CONFLICT DO UPDATE、PK 欠損行のスキップ・ログ出力）。
    - レスポンスパース時の型安全ユーティリティ (_to_float, _to_int)。
  - ニュース収集モジュール（data/news_collector.py）
    - RSS フィード取得、URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）、記事IDを正規化 URL の SHA-256 の先頭で生成し冪等性を保証。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策等の安全考慮。
    - raw_news へのバルク保存のためのチャンク処理とトランザクション最適化。
- 研究（research）モジュール
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算関数を提供
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日不足時は None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（窓不足時は None）。
    - calc_value: per / roe（raw_financials から target_date 以前の最新財務を参照）。
    - SQL を活用した DuckDB 内計算（prices_daily / raw_financials を参照）。
  - feature_exploration.py: 研究用途向けの補助関数
    - calc_forward_returns: 任意ホライズンの将来リターン計算（horizons の妥当性チェック）。
    - calc_ic: スピアマンランク相関（IC）計算（結合/欠損値除外、サンプル数閾値）。
    - rank / factor_summary: ランク化（同順位は平均ランク）、基本統計量集計（count/mean/std/min/max/median）。
  - research パッケージの __init__ で主要関数を公開。
- 戦略（strategy）モジュール
  - feature_engineering.py
    - 研究で計算された raw ファクターを統合し features テーブルへ保存（Z スコア正規化、±3 でクリップ、ユニバースフィルタ: 価格 >= 300 円、20 日平均売買代金 >= 5 億円）。
    - DuckDB トランザクションを用いた日付単位の置換（冪等）。
    - ルックアヘッドバイアス回避の設計（target_date 時点のデータのみ使用）。
  - signal_generator.py
    - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ保存（冪等）。
    - デフォルトの重み設定、ユーザー指定 weights の検証・正規化（合計が 1 に調整）。
    - 各コンポーネントスコア計算（momentum, value, volatility, liquidity, news）、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）。
    - SELL 条件: ストップロス（-8%）、score の閾値未満によるエグジット（未実装のTrailing/Time-based 条件は注記）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。
    - DuckDB トランザクションによる日付単位の置換（冪等）。
- パッケージエクスポート
  - strategy パッケージ __init__ で build_features / generate_signals を公開。

### 改良 (Changed)
- なし（初回実装のため該当なし）

### 修正 (Fixed)
- なし（初回実装のため該当なし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- RSS パースに defusedxml を採用し XML 攻撃を防止。
- ニュース収集での URL 正規化とスキームチェックにより SSRF リスクを低減。
- J-Quants クライアントにおけるトークン自動リフレッシュは無限再帰を起こさないよう設計（allow_refresh フラグ、1 回のみリフレッシュ）。

### 注意事項 / 実装上の設計メモ
- 多くの処理は Look-ahead バイアスを避ける設計（target_date 時点のデータのみ使用）を優先。
- データ永続化は DuckDB を想定し、SQL 内で集計・ウィンドウ関数を多用。
- 冪等性を重視（ON CONFLICT、日付単位の DELETE→INSERT トランザクションパターン）。
- 一部機能（例: positions テーブルに依存するトレーリングストップや時間決済）は設計に記載があるが未実装の箇所がある（将来追加予定）。
- settings による環境値チェックが厳格なため、運用時は .env.example を参照して必須環境変数を正しく設定してください。

---

本 CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリース履歴・日付・マイグレーション手順はリポジトリのリリースノートやタグを参照してください。