# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
重大なバージョン番号は semver に準拠しています。

## [Unreleased]

### Added
- 企画中 / 今後実装予定の機能を明記：
  - ポジション管理の強化（positions テーブルに peak_price / entry_date を持たせ、トレーリングストップや時間決済のエグジット条件を実装予定）。
  - execution 層と実際の発注連携（現在は signals テーブルまでの生成に限定）。
  - News -> 銘柄紐付け処理の高度化（NER/正規化の精度向上）。

### Changed
- 設定ロードの自動化動作に関する拡張案（環境変数の保護ポリシーやロード順の見直し検討）。

### Fixed
- （今後のリリースで対応予定の不具合修正項目を記載）

---

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システム "KabuSys" の基本モジュールを実装。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期バージョンを定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントを考慮した .env パーサを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、各種必須設定をプロパティ経由で取得（J-Quants / kabuステーション / Slack / DB パス / 環境判定 / ログレベル検証）。
  - 環境変数の検証（KABUSYS_ENV, LOG_LEVEL）の厳密チェックとエラーメッセージ。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装：
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
    - 401 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組み。
    - ページネーション対応（pagination_key の追跡）。
    - データ整形ユーティリティ（_to_float, _to_int）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices/raw_financials/market_calendar）を実装。ON CONFLICT の扱いにより重複更新を防止。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集の基本機能を実装（デフォルトソースに Yahoo Finance のビジネスカテゴリを設定）。
  - セキュリティ対策：defusedxml による XML パース、安全な最大受信バイト数制限（10MB）、HTTP/HTTPS スキーム制限、IP/SSRF 対策の考慮（実装方針）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホストの小文字化）。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成する方針（冪等性確保）。
  - バルク INSERT チャンク処理とトランザクションでの一括保存方針。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - Momentum / Volatility / Value の各ファクターを DuckDB の prices_daily/raw_financials を参照して計算する関数を実装：
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）。必要行数が不足する場合は None を返す挙動。
    - calc_volatility: 20日 ATR（atr_20, atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio)。NULL 伝播の制御に注意。
    - calc_value: 最新の財務（eps, roe）を target_date 以前の最新値から取得し PER/ROE を計算。
  - 実運用を想定したスキャン範囲（カレンダー日バッファ）やデータ不足時の扱いを明確化。

- 研究支援ユーティリティ（src/kabusys/research/feature_exploration.py）
  - 将来リターン計算 calc_forward_returns（複数ホライズンに対応、入力検証）。
  - IC（Spearman の ρ）計算 calc_ic（結合・欠損除外・最小サンプルチェック）。
  - ランク計算ユーティリティ rank（同順位は平均ランク）
  - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算。

- データ統計ユーティリティ
  - zscore_normalize の公開（src/kabusys/research/__init__.py を通じて re-export。実体は kabusys.data.stats に存在する想定）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールの生ファクターを統合・正規化して features テーブルに UPSERT する build_features を実装：
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化対象カラムを Z スコアで正規化し ±3 でクリップ。
    - target_date 単位での削除→挿入の原子操作（トランザクション）により冪等性を保証。
    - 価格不足（休場日等）に対応するため target_date 以前の最新価格を参照。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して最終スコア final_score を算出し signals テーブルに保存する generate_signals を実装：
    - momentum/value/volatility/liquidity/news の重み付け合算（デフォルト重みを実装）。
    - 重みはユーザ指定で上書き可能だがバリデーション（非数値・負値などを無視）と合計 1.0 への再スケーリングを行う。
    - Sigmoid を用いたスコア変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY シグナルは閾値（デフォルト 0.60）以上の銘柄に対して生成。SELL シグナルはエグジット条件（ストップロス -8% / スコア低下）で生成。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）とランク再付与。
    - signals テーブルへの日付単位の置換で冪等性を保証（トランザクション + バルク挿入）。
    - 一部未実装のエグジット（トレーリングストップ、時間決済）はコード中に TODO として明示。

- パッケージのエクスポート（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）
  - 主要関数（build_features / generate_signals / calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize）をパッケージレベルで公開。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- news_collector で defusedxml を使用し、RSS/XML パースにおける XML Bomb 等の攻撃を軽減する設計を採用。
- J-Quants クライアントでトークン管理・リフレッシュを実装し、認証エラー時の安全な再試行を確保。
- .env の読み込みではファイル権限/予期せぬIOエラー時に警告を発する実装。

### Notes / Limitations
- execution パッケージは present だが、実際の発注ロジック（kabuステーション接続・注文送信）はこのリリースでは含まれていない（分離された責務）。
- 一部エグジット条件（トレーリングストップ、時間決済）は実装済みロジックには含まれておらず、positions に追加情報（peak_price / entry_date）が必要。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar 等）は本 CHANGELOG に対応するコードの前提であり、スキーマ定義は別途管理すること。
- 外部依存を抑えるため、研究モジュールは pandas 等に依存せず標準ライブラリ + duckdb で実装されている。

---

作成日: 2026-03-20

（注）この CHANGELOG は提示されたソースコードから機能・設計方針を推測して作成しています。実際のリリースノートやプロダクション向けドキュメント作成時はコミット履歴や実際のスキーマ／運用仕様を参照して調整してください。