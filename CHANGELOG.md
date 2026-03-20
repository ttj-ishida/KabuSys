# Changelog

すべての注目すべき変更点はこのファイルで管理します。  
フォーマットは「Keep a Changelog」仕様に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装しました。主要な機能、設計方針、注意点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - pakage メタデータと公開モジュール定義を追加（kabusys.__init__、バージョン "0.1.0"）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env パースロジックの実装（コメント / export 形式 / クォート・エスケープ対応）。
  - OS 環境変数保護（protected set）および上書き制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack、DB パス、環境判定・ログレベル検証など）。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限制御（固定間隔スロットリング、120 req/min）。
  - リトライ機構（指数バックオフ、最大3回、408/429/5xx 対応）。
  - 401 に対する自動トークンリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ。
  - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存。
  - 入力パースユーティリティ（_to_float / _to_int）を実装し不正値を安全に扱う。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集フロー実装（デフォルトソース: Yahoo Finance）。
  - 記事ID を正規化 URL の SHA-256 ハッシュで生成し冪等性を保証。
  - URL 正規化（トラッキングパラメータ除去、キーソート、小文字化、フラグメント除去）。
  - XML パースに defusedxml を利用し XML 攻撃を軽減。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF/非 http(s) スキーム防御を考慮。
  - DB へのバルク挿入をトランザクションでまとめ、チャンク化により SQL 長制限に対応。
- 研究用ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を組合せ
  - 特徴量探索モジュール（feature_exploration）:
    - 将来リターン計算（calc_forward_returns）
    - IC（Information Coefficient）計算（Spearman ρ）および rank ユーティリティ
    - factor_summary（count/mean/std/min/max/median）
  - 研究用 API をまとめてエクスポート（kabusys.research.__init__）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research の生ファクターを取得しマージ
    - ユニバースフィルタ（最低株価、20日平均売買代金閾値）適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）
    - Z スコアを ±3 でクリップし features テーブルへ日付単位で置換（トランザクションで原子性保持）
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算
    - momentum/value/volatility/liquidity/news の重み付き合算で final_score を算出（デフォルト重みを実装）
    - 重みの入力検証と再スケーリング機能
    - Bear レジーム検知（ai_scores の regime_score 平均で判定）に基づく BUY 抑制
    - BUY（threshold 0.60 デフォルト）・SELL（ストップロス / スコア低下）シグナルの生成
    - positions / prices_daily を参照したエグジット判定
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）
- パッケージ API エクスポート
  - strategy パッケージで build_features / generate_signals を公開。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を利用、最大受信バイト数制限、HTTP(S) スキーム検査などにより外部入力処理の安全性を考慮。
- jquants_client のネットワーク呼び出しにタイムアウト（urllib の timeout）を設定し無限待ちを防止。

### 設計上の注意点 / 未実装事項 (Known issues / Notes)
- signal_generator のトレーリングストップおよび時間決済（保有 60 営業日超過）は未実装（positions テーブルに peak_price / entry_date が必要）。
- feature_engineering / strategy は発注（execution）層に依存しない設計。実際の注文実行は execution 層の実装が別途必要。
- 一部の設計判断（Z スコア ±3 クリップ、重みデフォルト値、ユニバース閾値など）は StrategyModel.md 等の仕様を前提としています。パラメータチューニングは今後の改版で提供予定。
- DB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, raw_news, features, ai_scores, positions, signals など）は選定済みだが、マイグレーション / スキーマ定義ファイルは本リリースに含まれていません。導入時は対応するスキーマを用意してください。

### マイグレーション / アップグレード手順
- 既存環境からのアップグレードは特になし（初回リリース）。
- .env 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants リフレッシュトークンは環境変数 JQUANTS_REFRESH_TOKEN に設定してください。

---

作成日: 2026-03-20

（要望があれば、以降のリリース向けにカテゴリ分けやより細かな変更履歴・移行ガイドの追記を行います。）