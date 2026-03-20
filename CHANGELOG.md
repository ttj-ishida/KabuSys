# Changelog

すべての重要な変更をこのファイルに記録します。  
この変更履歴は Keep a Changelog のフォーマットに準拠しています。

注: 以下は与えられたコードベースの内容から推測して作成したリリースノートです。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース: kabusys — 日本株自動売買システムの基礎モジュール群を追加。
  - src/kabusys/__init__.py
    - パッケージバージョンを "0.1.0" として公開。パブリック API (`__all__`) に data, strategy, execution, monitoring を含める。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env のパースロジックを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い等に対応）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを追加し、J-Quants / kabu / Slack / DB パス等の設定をプロパティ経由で取得。値検証（例: KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
    - 必須環境変数未設定時は ValueError を発生させ、開発者に明示的なエラーを返す。

- データ取得・保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。日次株価・財務データ・マーケットカレンダーの取得関数を提供（ページネーション対応）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）を実装。429 の場合は Retry-After を尊重。
    - 401 Unauthorized 受信時のトークン自動リフレッシュ処理（1 回のみ）を実装。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスのトレースを可能に。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保。
    - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、入力データの堅牢なパースを実現。

- ニュース収集
  - src/kabusys/data/news_collector.py（途中実装）
    - RSS フィードからニュースを収集して raw_news に保存する設計を実装（記事IDは正規化 URL の SHA-256 ハッシュなどで冪等性を担保）。
    - defusedxml を用いた XML パースでセキュリティを強化（XML Bomb 等への対策）。
    - 受信バイト数の上限設定（MAX_RESPONSE_BYTES）やトラッキングパラメータ除去、URL 正規化ロジックを実装。
    - HTTP(S) スキームの検証や SSRF 対策、バルク挿入のチャンク化等の設計方針を明示。
    - デフォルトの RSS ソースに Yahoo ファイナンスのビジネスカテゴリを設定。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日移動平均乖離等）、ボラティリティ（20 日 ATR、相対 ATR、出来高関連）、バリュー（PER、ROE）等のファクター計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials テーブルのみ参照し、外部 API に依存しない設計。
    - 業務上の欠損・データ不足に対する扱い（十分なデータがない場合は None を返す）を明確化。

  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns）を追加。複数ホライズン（デフォルト [1,5,21]）対応。ホライズン検証と範囲限定でパフォーマンスを配慮。
    - IC（Information Coefficient）計算（calc_ic）およびランク変換ユーティリティ（rank）を実装（スピアマン ρ）。
    - ファクターの統計サマリーを算出する factor_summary を実装（count, mean, std, min, max, median）。
    - すべて標準ライブラリのみで実装し、pandas 等には依存しないことを明記。

  - src/kabusys/research/__init__.py
    - 主要関数をパッケージレベルで公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- ストラテジー（特徴量生成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した生ファクターを正規化・合成して features テーブルへ保存する処理（build_features）を実装。
    - ユニバースフィルタ（最低株価・20 日平均売買代金）や Z スコア正規化、±3 でのクリップ、日付単位での置換（トランザクション）などを行い、冪等性とルックアヘッド防止を考慮。
    - 正規化処理に kabusys.data.stats.zscore_normalize を利用。

  - src/kabusys/strategy/signal_generator.py
    - 正規化済み feature と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
    - デフォルト重み・閾値（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60）を提供。ユーザー指定の重みは検証・正規化して使用。
    - Sigmoid や平均化によるコンポーネントスコア計算、AI スコアの補完（未登録は中立 0.5）、Bear レジーム検知（レジームスコア平均が負の場合）による BUY 抑制を実装。
    - 保有ポジションのエグジット判定（ストップロス -8% / スコア低下）を実装。SELL 優先ポリシーにより BUY から除外。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を担保。
    - 一部トレーリングストップ等は未実装だが設計にコメントを追加。

  - src/kabusys/strategy/__init__.py
    - strategy API（build_features, generate_signals）を公開。

- データ統計ユーティリティ（参照）
  - kabusys.data.stats（コード参照中に利用されるユーティリティ）を参照して使用する設計。Z スコア正規化等の中心的ユーティリティを利用。

### Changed
- 初回リリースのため該当なし（ベース実装の追加が中心）。

### Fixed
- 初回リリースのため該当なし。

### Security
- news_collector で defusedxml を使用（XML 関連の脆弱性対策）。
- J-Quants クライアントで認証トークンの扱いと自動リフレッシュを実装。HTTP レスポンスサイズやネットワーク例外に対する耐性を提供。

### Notes
- 多くの DB 操作は DuckDB を前提に設計されており、transactions（BEGIN/COMMIT/ROLLBACK）と ON CONFLICT を組み合わせて冪等性と原子性を確保している。
- ルックアヘッドバイアス防止の考慮（取得時刻記録、target_date 時点のデータのみ参照など）が各所で設計に反映されている。
- 一部モジュール（news_collector）はファイル内で途中実装の箇所があるため、実装完了や安定化に伴うマイナー/パッチリリースが想定される。

---

今後のリリース案（例）
- Unreleased: news_collector の完全実装、execution 層（発注 API との接続）、monitoring 周りの実装、単体テスト・統合テストの追加、ドキュメント補完。