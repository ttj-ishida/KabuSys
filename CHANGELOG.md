# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容（ソース内の実装・コメント）から推測して作成した変更履歴です。

## [Unreleased]

### Added
- 今後実装予定の改善点・未実装の仕様メモを追加
  - factor_research のエグジット条件に示されたトレーリングストップや時間決済（positions に peak_price / entry_date が必要）は未実装。将来的に追加予定。
  - ニュース収集の URL 検証や記事テキスト前処理の追加強化、RSS ソースの拡充計画。

### Changed
- （なし）

### Fixed
- （なし）

---

## [0.1.0] - 2026-03-20

初回リリース（ベースライン実装）。主な追加内容と設計方針を列挙します。

### Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - パッケージエクスポート __all__ を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと OS 環境変数の統合読み込みを実装（自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を手がかりに探索）。
  - .env パーサ実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ処理に対応）。
  - 上書き制御（.env, .env.local の読み込み順、OS 環境変数保護）。
  - Settings クラスを提供し、必須環境変数取得（_require）、各種プロパティ（J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境モード・ログレベルの検証等）を定義。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限制御（固定間隔スロットリングで 120 req/min を順守する RateLimiter）。
  - リトライ／指数バックオフ（408/429/5xx へのリトライ、最大試行回数の指定）。
  - 401 発生時のトークン自動リフレッシュ（1 回だけリトライ）とモジュールレベルのトークンキャッシュ。
  - 各種フェッチ関数を実装：fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
  - DuckDB への冪等保存関数を実装：save_daily_quotes、save_financial_statements、save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - 入力データの型変換ユーティリティ（_to_float / _to_int）を実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存する処理（記事IDは正規化 URL の SHA-256 ハッシュを使用）。
  - セキュリティ対策：defusedxml を XML パーサに使用、受信サイズ上限（MAX_RESPONSE_BYTES）、SSRF 対策（非 http/https 拒否 等）の設計が記載。
  - URL 正規化ロジック（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。

- リサーチモジュール（kabusys.research）
  - factor_research を実装：
    - モメンタム（1/3/6 ヶ月リターン、200 日移動平均乖離）
    - ボラティリティ（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - バリュー（PER、ROE：raw_financials と prices_daily を結合）
    - 各関数は DuckDB 接続を受け取り SQL＋Python で実行
  - feature_exploration を実装：
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、引数検証）
    - IC（Information Coefficient）計算（スピアマンのランク相関 calc_ic）
    - ファクター統計要約（factor_summary）、ランク計算ユーティリティ（rank）
  - 研究用途のユーティリティ（zscore_normalize は data.stats に委譲）を公開。

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research 側で算出した生ファクターをマージ、ユニバースフィルタ（最低株価・流動性）適用、Z スコア正規化、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性保持）。
    - ルックアヘッドバイアス回避方針（target_date 時点のデータのみ使用）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を作成。
    - デフォルト重みのフォールバック・正規化、ユーザ指定 weights の検証（未知キー・非数値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら BUY を抑制）および SELL（エグジット）判定ロジック（ストップロス、スコア低下）。
    - BUY/SELL シグナルを signals テーブルへ日付単位で置換（トランザクションで原子性保持）。
    - 欠損データに対する中立補完（None のコンポーネントは 0.5 で補完）等のロバスト性。

- 共通設計・実装上の注意点（ドキュメント化）
  - ルックアヘッドバイアス回避、発注層への依存排除（strategy 層は execution 層に直接依存しない）、DuckDB をデータストアとする方針がコードコメントや実装で示されている。

### Fixed
- （初期リリースのため特段の bugfix はなし）

### Security
- ニュース収集で defusedxml を使用し XML の安全なパースを意識。
- RSS の受信サイズ制限、トラッキングパラメータ除去、URL 正規化等で悪意ある入力に対する防御を設計。
- J-Quants クライアントでタイムアウト・再試行・トークンリフレッシュを実装し、認証エラー・過負荷への耐性を高める。

### Notes / Known limitations
- 一部機能（factor_research のトレーリングストップや時間決済など）はコメントとして未実装のまま記載されている。
- zscore_normalize 実装は data.stats モジュールで提供される前提（今回のスナップショットでは参照のみ）。
- NewsCollector の完全な URL/SRR 防御（IP 解決後のホワイトリストなど）は設計に触れられているが、実運用上の追加検証が推奨される。

---

過去のバージョン履歴やリリースノートへのリンクは現時点では存在しません。必要であれば、各モジュールの更なる変更点（例: パラメータ追加、アルゴリズム調整、パフォーマンス改善等）を反映した更新版 CHANGELOG を作成します。