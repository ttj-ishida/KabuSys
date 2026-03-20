# CHANGELOG

すべての注目すべき変更点を時系列で記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

### Added
- （今後の開発用の未リリース変更をここに記載します）

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加。

### Added
- 基本パッケージ構成
  - パッケージエントリポイント src/kabusys/__init__.py を追加。バージョンは 0.1.0。
  - サブパッケージ公開 API: data, strategy, execution, monitoring（execution の実装は空のイニシャライザのみ）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式やクォート内のバックスラッシュエスケープ、インラインコメントに対する堅牢な .env パースロジックを実装。
  - 環境変数の必須チェック用 _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許可値セットでバリデーション）。
- Data 層（src/kabusys/data）
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - J-Quants API から日足・財務・カレンダーを取得するクライアントを実装。
    - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - 408/429/5xx 等に対する指数バックオフ付きリトライ（最大 3 回）を実装。429 の場合は Retry-After ヘッダを考慮。
    - 401 受信時にはリフレッシュトークンで自動的に ID トークンを更新して 1 回だけリトライする安全策を実装。
    - ページネーション対応（pagination_key の取り扱い）とモジュールレベルの ID トークンキャッシュを実装。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT による冪等保存を行う。
    - データ変換ユーティリティ (_to_float / _to_int) を実装して堅牢にパース。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィードから記事を収集し raw_news に保存するロジックの下地を実装。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除、小文字化）を実装。
    - セキュリティ対策として defusedxml を用いた XML パース（XML Bomb 防止）、受信サイズ上限（10MB）設定、HTTP/HTTPS スキーム検証（SSRF 緩和）を採用。
    - 記事 ID に URL 正規化後の SHA-256 を利用して冪等性を確保する方針を採用。
- Research 層（src/kabusys/research）
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum / Volatility / Value の定量ファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR / 相対 ATR (atr_pct) / 20日平均売買代金 / 出来高比率を計算。true_range の NULL 伝播を制御して正しいカウントを行う。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0 の場合は PER を None）。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）での将来リターンを一括取得する SQL 実装を提供。
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関を実装（同順位は平均ランクで処理）。有効サンプルが 3 未満の場合は None を返す。
    - factor_summary / rank：ファクターの基本統計量とランク計算ユーティリティを提供。
  - research パッケージ __all__ を整備して主要ユーティリティを公開。
- Strategy 層（src/kabusys/strategy）
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research 側で計算した生ファクターを集約・ユニバースフィルタ（最低株価・最低売買代金）適用・Z スコア正規化（指定カラム）・±3 クリップして features テーブルへ日付単位で UPSERT（冪等）する build_features を実装。
    - ユニバースフィルタ条件（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - トランザクション（BEGIN/COMMIT/ROLLBACK）で日付単位の原子操作を保証。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換する generate_signals を実装。
    - momentum/value/volatility/liquidity/news の重み付け合算式を実装。カスタム weights を受け付け、検証・正規化（合計 1 に再スケール）を行う。
    - スコア変換ヘルパ（シグモイド、平均化）やコンポーネントスコア計算を実装（モメンタムは複数要素の平均、バリューは PER に基づく逆数モデル、ボラティリティは -Z をシグモイド化 等）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制する機能を実装。
    - エグジット（SELL）判定実装（ストップロス -8%／スコア低下）。保有ポジションの価格欠損時は判定をスキップしログ出力。
    - SELL 優先ポリシー：SELL 対象を BUY から除外し、BUY のランクを再付与。
  - strategy パッケージ __all__ を整備して build_features / generate_signals を公開。

### Changed
- 設計方針の明確化（モジュールドキュメンテーション）
  - 各モジュールに Look-ahead bias 回避、発注層への非依存、DuckDB のみ参照する旨のコメントを追加。研究用と本番用の責務分離を明確化。
  - DuckDB SQL を中心に実装し、外部ライブラリ（pandas 等）に依存しない方針を明記。

### Fixed
- N/A（初期リリースのため既知のバグ修正はなし）

### Security
- news_collector に defusedxml を使用して XML 攻撃を緩和。
- RSS 受信サイズ上限・URL スキーム検証・トラッキングパラメータ除去等により、SSRF やメモリ DoS を軽減する設計を採用。
- J-Quants クライアントは認証トークンの自動リフレッシュ処理を導入し、認証失敗時の再帰を防止するため allow_refresh フラグ等で無限再試行を回避。

### Notes / Known limitations
- execution パッケージは初期状態で実装されていません（発注ロジックは含まれていない）。
- 一部戦術（例: トレーリングストップ、時間決済）は戦略モジュール内で未実装としてコメントで明示されています（positions テーブルに peak_price / entry_date が必要）。
- ニュース記事の保存・銘柄紐付けロジック（news_symbols 等）は収集モジュールでの方針は定義済みだが、完全な ETL ワークフローやマッピングロジックは追加実装が必要。
- DuckDB スキーマ（tables）やマイグレーションは本リリースに含まれていないため、利用前に適切なスキーマ作成が必要。

---

保持方針:
- メジャー/マイナー/パッチポリシーに従い、今後の変更はセマンティックバージョニングに基づき記載します。