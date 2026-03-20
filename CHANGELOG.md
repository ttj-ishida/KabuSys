# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
このプロジェクトのバージョニングは SemVer を採用しています。

## [0.1.0] - 2026-03-20
最初のリリース。日本株自動売買システム KabuSys のコア機能群を実装。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys/__init__.py（バージョン 0.1.0、公開 API の __all__ を定義）
- 設定管理
  - 環境変数ロード/パース機能（kabusys.config）
    - プロジェクトルート（.git / pyproject.toml）を基準に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export KEY=val 形式やシングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応した堅牢な .env パーサ実装。
    - Settings クラスを提供（J-Quants / kabu API / Slack / データベースパス / 環境種別 / ログレベル 等のプロパティを取得）。不正な env 値は明示的にエラーを送出。
- データ収集・保存（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 固定間隔スロットリングによるレート制限 (_RateLimiter)（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ処理。
    - ページネーション対応の fetch_* 関数（daily_quotes / financial_statements / market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar）を実装。PK 欠損行のスキップとログ出力に対応。
    - 型変換ユーティリティ（_to_float / _to_int）で不正値を安全に扱う。
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィード取得、ID 生成（URL 正規化後の SHA-256）、テキスト前処理、raw_news への冪等保存を実装。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）、トラッキングパラメータ除去、URL 正規化、defusedxml による XML 攻撃防御、バルク挿入チャンキングなどを実装。
- 研究用モジュール（kabusys.research）
  - factor_research（calc_momentum / calc_volatility / calc_value）
    - prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー系ファクター計算を実装。
    - 各ファクターは (date, code) キーの dict リストで返却。
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
    - 将来リターンの一括取得（任意ホライズン）、Spearman（ランク相関）による IC 計算、ファクター統計サマリの提供。
  - research パッケージの public export（zscore_normalize を含むユーティリティを再公開）。
- 戦略モジュール（kabusys.strategy）
  - feature_engineering.build_features
    - research モジュールで計算した原始ファクターを統合・ユニバースフィルタ（最低株価・平均売買代金）適用・Z スコア正規化（±3 クリップ）して features テーブルへ日付単位の置換（トランザクション）で保存。
    - DuckDB を用いた原子性（BEGIN/COMMIT/ROLLBACK）でのバルク挿入を実装。
  - signal_generator.generate_signals
    - features と ai_scores を統合し、複数コンポーネント（momentum, value, volatility, liquidity, news）を重み付き合算して final_score を算出。
    - weight のバリデーション・補完・正規化処理を実装。
    - Bear レジーム判定（AI の regime_score 平均が負の場合）による BUY 抑制。
    - BUY シグナルは閾値超過で生成、SELL シグナルはストップロス（終値/avg_price -1 < -8%）およびスコア低下で判定。SELL 優先ポリシー適用後に signals テーブルへ日付単位で置換（トランザクション）で保存。
    - エッジケース（価格欠損、features 未登録銘柄、positions テーブル未整備等）に対するログ出力と安全処理を実装。
- logging / observability
  - 各主要処理に対して INFO/DEBUG/ WARNING ログを追加し、運用時のトラブルシュートを容易に。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサの改善により、エスケープ・クォート・コメントの誤認識を修正（堅牢化）。
- J-Quants データ保存処理で PK 欠損行をスキップして警告ログを出すように改善。
- _to_int/_to_float の挙動を明示化し、不正な文字列や小数部を持つ数値の扱いを安全化。
- DuckDB 書き込み処理にトランザクション（BEGIN/COMMIT/ROLLBACK）を導入し、部分書き込みによる不整合リスクを軽減。

### Security
- news_collector で defusedxml を使用して XML 関係の攻撃（XML bomb 等）を防止。
- ニュースの URL 正規化とトラッキングパラメータ除去を実装し、ID 一意化と過剰な外部トラッキングの混入を防止。
- ニュース取得時の受信バイト上限（MAX_RESPONSE_BYTES）を導入し、メモリ DoS を緩和。
- J-Quants クライアントは認証トークン管理（キャッシュ + 自動リフレッシュ）および再試行ロジックを実装し、認証エラーやネットワーク障害に対して堅牢化。

### Known limitations
- ポジション管理に関する一部のエグジット条件（トレーリングストップや時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要で、現時点では未実装（コード内に TODO コメントあり）。
- news_collector の SSRF や IP 検査等の具体的な実装の残り部分は将来的により厳密にする余地あり（コード内の設計方針は記載済み）。
- 外部依存を抑えるため pandas 等を使わずに実装しているため、大量データ処理時のパフォーマンスチューニングは今後の課題。

---

今後の変更（バグフィックス、機能追加、運用改善）は Unreleased セクションに追記していきます。必要であれば各モジュールごとのリリースノート（より細かな変更履歴）も作成できます。