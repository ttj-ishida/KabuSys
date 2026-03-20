# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。以下はコードベースから推測してまとめた主な追加点・設計上の注意点です。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。公開 API を __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を追加。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、CWD に依存しない自動読み込みを実現。
  - .env パーサ実装（コメント/クォート/エスケープ処理対応、export KEY= 形式サポート）。
  - 自動読み込みの無効化環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
  - 必須設定取得関数（_require）と Settings クラスを実装。J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の設定プロパティを提供。
  - env・log_level のバリデーション（許容値チェック）を導入。
- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - レート制限対策（固定間隔スロットリング、120 req/min）を実装。
    - 再試行（指数バックオフ、最大 3 回、408/429/5xx 対象）と 401 時の自動トークンリフレッシュを実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ（_to_float, _to_int）を実装して不正データを安全に扱う。
    - トークンキャッシュをモジュールレベルで保持し、ページネーション間で共有。
    - データ取得時の fetched_at を UTC ISO8601 形式で記録（Look-ahead バイアス対策）。
  - ニュース収集モジュール（news_collector.py）
    - RSS フィード取得・前処理の基礎実装。デフォルトソースに Yahoo Finance のビジネス RSS を登録。
    - URL 正規化（トラッキングパラメータ除去・ソート・小文字化・フラグメント削除）を実装。
    - defusedxml 使用による XML 攻撃対策、HTTP スキーム制限、受信サイズ上限（10MB）などセキュリティ対応。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成する方針（冪等性確保）。
    - DB へのバルク INSERT チャンク化（チャンクサイズ上限）とトランザクション集約を想定した実装設計。
- リサーチ（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - momentum / volatility / value の各ファクター計算を実装。
    - momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を算出。
    - volatility: 20 日 ATR（true range を適切に扱う）、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio を算出。
    - value: raw_financials から最新の財務データを結合して PER・ROE を算出（EPS=0 や欠損は None）。
    - DuckDB のウィンドウ関数を活用し、効率的に集計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）を独自実装、必要最小サンプル数チェック。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）を実装（外部依存なし、標準ライブラリのみ）。
  - research パッケージの公開 API をエクスポート（calc_momentum/calc_volatility/calc_value/zscore_normalize 等）。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の raw factor を取得して統合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 指定カラム群を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - features テーブルへの日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性を確保）を実装。
  - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）のスコアを算出。
  - 各コンポーネント: シグモイド変換・欠損補完（中立 0.5）・重み付き合算で final_score を算出。デフォルト重みを定義（momentum 0.40 など）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負）を導入し、Bear 時は BUY シグナルを抑制。
  - BUY シグナル閾値デフォルト 0.60、STOP-LOSS（-8%）等のエグジット判定を実装。
  - positions / prices_daily を参照した SELL シグナル生成を実装。SELL は BUY に優先し、signals テーブルへ日付単位置換で保存。
  - weights の入力バリデーション（未知キー・非数値・負値の除外）と合計が 1.0 でない場合のリスケール処理を実装。
- 罰則・例外処理・ログ
  - トランザクション失敗時の ROLLBACK 例外処理を適切に実装し、警告ログを出力する設計。
  - 各モジュールで詳細ログ（info/debug/warning）を出力し、運用時のトラブルシューティングを支援。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を利用し XML 攻撃を緩和。
- fetch/save 実装で外部からの不正データ（空値・不正数値）に対する安全な処理（スキップ・None 変換）を行う。

### 既知の制限・未実装（Important notes / TODO）
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要であり未実装。
- news_collector の完全な RSS パース/記事抽出ロジック（記事本文抽出や銘柄紐付け news_symbols の実装）は、このスニペットでは完結していない可能性がある（設計方針は記載あり）。
- 一部のヘルパー（kabusys.data.stats.zscore_normalize 等）は本コード群外に実装済みである想定（research/__init__ で参照）。
- get_id_token は settings.jquants_refresh_token に依存するため、環境変数未設定時は ValueError を送出する。
- .env のパースは多くのケースに対応しているが、特殊なフォーマットの .env 行はスキップされる可能性がある（意図的な設計）。
- 自動 .env ロードはプロジェクトルート検出に失敗した場合スキップされる。CI/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。

### 互換性 (Breaking Changes)
- 初回リリースのため破壊的変更はありません。

---

開発者向けメモ:
- 今後のリリースでは以下が候補:
  - execution 層（kabu ステーション等への実注文エンジン）との統合実装。
  - monitoring / Slack 通知機能の実装（設定項目は存在）。
  - news_collector の記事 → 銘柄紐付けロジック実装と NLP/AI スコアリングの統合。
  - 単体テスト・統合テスト、CI/CD 用のテスト用フック（KABUSYS_DISABLE_AUTO_ENV_LOAD 等の活用）整備。

（以上）