# Changelog

すべての注目すべき変更をここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。__all__ に主要サブパッケージを列挙。

- 設定 / 環境変数読み込み (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする機能を実装。
  - export 形式やコメント、クォート・エスケープに対応した .env パーサを実装。
  - 自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）や OS 環境変数保護（.env.local で上書き時の保護）をサポート。
  - settings オブジェクトでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API 設定、Slack、DB パス、環境・ログレベル判定等）。
  - 環境変数の必須チェック（未設定時は ValueError を送出）と入力値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
  - HTTP リクエストに対するリトライ（指数バックオフ、最大 3 回）、429 の Retry-After 対応、401 の自動トークンリフレッシュ（1 回）を実装。
  - ページネーション対応の fetch 関数群を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE / DO NOTHING を利用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ（_to_float / _to_int）を実装し、入力の堅牢性を確保。
  - トークンキャッシュをモジュール単位で保持し、ページネーションや複数呼び出しで再利用。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集モジュールを実装（デフォルトで Yahoo Finance のビジネスカテゴリ RSS を設定）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）や XML パースに defusedxml を利用する等、セキュリティ対策を組み込み。
  - バルク挿入のチャンク処理を実装し DB 操作の効率化を図る。

- リサーチ機能 (kabusys.research)
  - ファクター計算（研究用）モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の算出（ウィンドウ不足時は None）。
    - calc_volatility: 20 日 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
    - calc_value: 最新財務データと株価を組み合わせて PER / ROE を算出。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズン先の将来リターンを一括で取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ。

- 戦略層 (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（最小株価・最小売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ、DuckDB の features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出。
    - デフォルト重み・閾値（weights, threshold）を採用し、ユーザ指定の重みはバリデーション・正規化して反映。
    - Bear レジーム検出により BUY シグナルを抑制するロジックを実装（regime_score の平均が負の場合）。
    - BUY/SELL シグナルの生成。SELL はストップロス（-8%）やスコア低下によるエグジット判定を実装。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
    - 欠損コンポーネントは中立値（0.5）で補完して不当な降格を防止。

### 変更 (Changed)
- 本リリースは新規実装の集合のため、過去バージョンからの変更はありません。

### 修正 (Fixed)
- 本リリースは初版のためバグ修正履歴はありません。

### セキュリティ (Security)
- news_collector:
  - defusedxml を用いた XML パースで XML 関連の攻撃を緩和。
  - レスポンス最大バイト数を制限してメモリ DoS を抑制。
  - URL 正規化によりトラッキングパラメータを除去し、記事 ID の冪等性を確保。
  - （将来的な実装想定）SSR F 防止や IP/ホスト検証のためのユーティリティを用意する構成。

### 設計ノート / 備考
- Look-ahead bias（未来情報の混入）を避ける設計方針を全体で徹底:
  - データ取得時に fetched_at を UTC で記録。
  - 戦略・特徴量計算は target_date 時点のデータのみを参照。
- DuckDB を主要なストレージ（分析用）として利用。INSERT は冪等に設計。
- API クライアントはレート制限・再試行・トークン更新をサポートし、運用耐性を重視。
- トランザクション + バルク挿入により features / signals の日付単位置換を原子操作として実装。

（本 CHANGELOG は、提供されたソースコードからの機能推測に基づいて作成しています。実際のリリースノート作成時はコミット履歴・差分を参照して更新してください。）