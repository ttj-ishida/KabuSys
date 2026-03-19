# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
公開済みバージョンのみを記載しています。

※この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。バージョンは `0.1.0`。
  - public API を簡潔にエクスポート: data, strategy, execution, monitoring（__all__）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を探索して決定。
  - .env パーサーの実装（コメント、export プレフィックス、クォート内のエスケープ処理等に対応）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）と検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - パス設定（DUCKDB_PATH, SQLITE_PATH）は Path 型で返す。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。日足・財務・マーケットカレンダーの取得関数を提供（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - 固定間隔のレートリミッタ実装（120 req/min を守る _RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大試行回数、HTTP 408/429/5xx のリトライ）を実装。
  - 401 応答時にリフレッシュトークンで自動的に id_token を再取得して再試行する仕組み（1 回のみ）。
  - ページネーション対応（pagination_key の利用）。
  - DuckDB への冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT で更新することでアップサートを実現。
  - レスポンス変換ユーティリティ（_to_float, _to_int）を実装し、データ妥当性を担保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集するモジュールを実装（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、パラメータソート）。
  - セキュリティ対策: defusedxml による XML の安全パース、受信サイズ制限（最大 10MB）、HTTP スキームチェック、SSRF 緩和を意識した実装方針。
  - バルク挿入のチャンク化や、記事ID を正規化 URL の SHA-256 ハッシュで生成する設計を採用（冪等性確保）。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: 約1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。
    - Volatility: 20 日 ATR、相対ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio)。
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）。
  - データスキャン範囲や窓長（MA200/ATR/VOLUME 等）を定義し、休場日等を考慮したクエリ設計。
  - 研究用ユーティリティ: zscore_normalize を外部（kabusys.data.stats）から利用。

- 研究支援（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト 1,5,21 営業日）での将来リターンをまとめて取得。
  - IC 計算（calc_ic）：ファクターと将来リターンのスピアマン順位相関（Information Coefficient）を実装。サンプル不足時は None を返す。
  - ランク変換ユーティリティ（rank）と、ファクター統計要約（factor_summary）を実装。
  - pandas 等の外部依存を避け、標準ライブラリ + DuckDB の SQL で実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。research の calc_* 結果をマージし、ユニバースフィルタ（最低株価300円、20日平均売買代金 5 億円）を適用、指定列を Z スコア正規化、±3 でクリップして features テーブルへ日付単位で置換（冪等）するワークフロー。
  - トランザクション + バルク挿入で原子性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装。
  - 正規化済 features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出（デフォルト重みは StrategyModel.md の値に準拠）。
  - 重みの入力検証と再スケーリング、未知キーや無効値のスキップ処理を実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）により BUY シグナルを抑制。
  - SELL（エグジット）条件を実装（ストップロス -8% / スコア低下）。SELL の優先ポリシーを適用して BUY から除外、signals テーブルへ日付単位で置換。
  - 欠損値補完ポリシー: コンポーネント None は中立 0.5 で補完（欠損銘柄の不当な降格を防止）。
  - ログ出力およびトランザクション + バルク挿入で原子性を保証。

### Changed
- （初版のため履歴なし）

### Fixed
- （初版のため履歴なし）

### Security
- ニュースパーサーで defusedxml を使用し XML 関連の攻撃（XML Bomb 等）に対処。
- ニュース収集で受信バイト上限を設定してメモリ DoS を軽減。
- J-Quants クライアントで HTTP エラー時のリトライ制御を実装し、429 の Retry-After を尊重する等の耐障害性を向上。

### Notes / Known limitations
- signal_generator のトレーリングストップや時間決済（保有 60 営業日超）は未実装（positions テーブルに peak_price / entry_date 等のカラムが必要）。
- AI（news）スコアが欠損している場合は中立 0.5 を採用するため、AI 未導入時も動作するが最終スコア設計に注意が必要。
- .env パーサーは多くのケースに対応するが、非常に特殊な .env の記法がある場合は事前に確認が必要。
- DuckDB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）はリポジトリの別箇所または運用ドキュメントに従って事前準備が必要。
- news_collector の記事 ID は URL 正規化とハッシュに依存するため、外部ソース側で大幅な URL 構造変更があると重複判定に影響する可能性あり。

---

（補足）リリース以降の変更やバグ修正は本ファイルの Unreleased セクションに追記し、バージョンアップごとに履歴を移動してください。