# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
- （無し）

## [0.1.0] - 2026-03-20
初回リリース（推定）。以下の主要機能・モジュールを追加。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン 0.1.0 を設定し、公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数読み込み／管理モジュール（src/kabusys/config.py）を追加。
    - プロジェクトルート探索（.git または pyproject.toml を起点）により CWD に依存しない .env 自動読み込みを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env 行パーサ（エクスポート形式、シングル/ダブルクォート、インラインコメント、エスケープ処理対応）。
    - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定プロパティと検証（KABUSYS_ENV / LOG_LEVEL の検証）を実装。
- データ取得・永続化（J-Quants クライアント）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加。
    - 固定間隔レートリミッタ（120 req/min）実装。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx 対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回）とトークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。主キー欠損行スキップ、ON CONFLICT による更新、fetched_at の記録。
    - 型変換ユーティリティ（_to_float / _to_int）。
- ニュース収集
  - RSS ベースのニュース収集モジュール（src/kabusys/data/news_collector.py）を追加。
    - RSS 取得、記事正規化、URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除）、SHA-256 ベースの記事 ID 生成による冪等性。
    - defusedxml を使用した安全な XML パース、受信サイズ制限（MAX_RESPONSE_BYTES）、バルク INSERT のチャンク処理、挿入件数報告。
- 研究用ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum / calc_volatility / calc_value を実装。DuckDB の SQL ウィンドウ関数を用いた高性能な集約（MA200、ATR、リターン等）。
    - 各ファクターは (date, code) ベースの dict リストとして返却。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位平均ランク処理）を実装。
    - pandas 等に依存しない純標準ライブラリ実装。
- 戦略実装（研究→運用ブリッジ）
  - feature_engineering（src/kabusys/strategy/feature_engineering.py）
    - research モジュールの生ファクターを結合、ユニバースフィルタ（最低株価・20日平均売買代金）、Z スコア正規化（zscore_normalize を利用）、±3 クリップ、features テーブルへの日付単位の置換（トランザクションによる原子性）を実装。
  - signal_generator（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算する一連のロジックを実装。
    - コンポーネントスコア（momentum / value / volatility / liquidity / news）算出、重み付け（デフォルト値を定義）、weights のバリデーションと再スケーリング。
    - Bear レジーム検知による BUY 抑制、BUY/SELL シグナル生成、保有ポジションのエグジット判定（ストップロス・スコア低下）、signals テーブルへの日付単位置換を実装。
- 研究パッケージ集約
  - src/kabusys/research/__init__.py で主要関数をエクスポート（calc_momentum 等）。

### Changed
- 設計/実装上の方針や注意点をコード内に明記（Look-ahead bias 回避、API 呼び出しの副作用回避、DuckDB のみ参照、外部発注 API 依存排除など）。
- DuckDB への書き込みは可能な限りトランザクション＋バルク挿入／ON CONFLICT により冪等性と原子性を確保。

### Fixed / Robustness
- .env 読み込みにおける以下の堅牢性向上:
  - export プレフィックス対応、引用符内エスケープ処理、インラインコメントの扱い。
  - プロジェクトルート探索によりパッケージ配布後も自動読み込みが CWD に依存しないように修正。
  - .env.local を .env の上書きとして扱う際、OS 側環境変数（プロセス環境）キーを保護。
- J-Quants クライアント:
  - HTTP 429 の場合は Retry-After ヘッダを優先して待機。その他再試行は指数バックオフ戦略により実施。
  - JSON デコード失敗時に詳細メッセージを含めてエラーを投げる。
  - ID トークン取得時の再帰（無限リフレッシュ）を防ぐため allow_refresh フラグを導入。
- news_collector:
  - defusedxml を採用して XML による外部攻撃（XML bomb 等）への耐性を確保。
  - レスポンス最大バイト数制限等によりメモリ DoS のリスクを低減。

### Security
- RSS パーシングで defusedxml を使用し、危険な XML 構造による攻撃を防止。
- ニュース URL 正規化によりトラッキングパラメータを除去し、ID を安定化（冪等性向上）。
- J-Quants への認証処理はトークンキャッシュ／自動リフレッシュロジックを用いて安全に管理。

### Deprecated
- なし

### Removed
- なし

### Breaking Changes
- なし（初回リリースのため該当なし）

---

注意:
- CHANGELOG はソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。