# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

フォーマット:
- 変更はバージョンごとに「Added / Changed / Fixed / Security / Deprecated / Removed」等で整理しています。
- 各エントリは可能な限り影響範囲（モジュール名）と挙動を明記しています。

## [Unreleased]

（現時点での開発中変更はここに記載します。）

---

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システムの基礎機能を実装しました。主な追加点と設計上の注意点は以下のとおりです。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys v0.1.0）。
  - モジュール構成: data, research, strategy, execution, monitoring の基本構成を用意。

- 環境設定（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - OSの環境変数は保護（override を制御）される仕組みを導入。
  - 独自の .env パーサ実装（コメント・クォート・export 表記対応）。
  - Settings クラスを提供。J-Quants / kabu ステーション / Slack / DB / ログレベル等の設定プロパティを公開。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を追加。

- データ取得（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx の再試行）。
    - 401 受信時はリフレッシュトークンを使ったトークンの自動再取得と 1 回の再試行を実施。
    - ページネーション対応の fetch_* 関数実装:
      - fetch_daily_quotes（株価日足取得）
      - fetch_financial_statements（財務データ取得）
      - fetch_market_calendar（取引カレンダー取得）
    - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 取得日時（fetched_at）を UTC ISO8601 で記録し、Look‑ahead バイアスのトレースを可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS ベースのニュース収集機能を実装（デフォルトに Yahoo Finance RSS を設定）。
  - 安全対策: defusedxml による XML パース、防御済み受信サイズ制限（MAX_RESPONSE_BYTES）、URL の正規化（追跡パラメータ除去）、HTTP/HTTPS スキームチェック等。
  - 記事ID は正規化後の URL の SHA-256（先頭32文字）を利用して冪等性を担保。
  - バルク INSERT のチャンク化などパフォーマンス配慮。

- リサーチ（kabusys.research）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率
    - calc_value: PER、ROE（raw_financials と prices_daily を結合）
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得
    - calc_ic: スピアマンランク相関（IC）計算
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返すランク付けユーティリティ
  - どの関数も DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計（外部 API へはアクセスしない）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research モジュールの生ファクターを取得し結合、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定列を Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で冪等性を保証）。
    - 欠損や外れ値を扱うための堅牢な実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - シグモイド変換、欠損値は中立（0.5）で補完、重み付け合算による final_score を算出。
    - 重みの入力検証と合計スケーリング（ユーザ指定 weights を許容）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear と判定、サンプル最小数チェックあり）。
    - BUY シグナル（閾値デフォルト 0.60）と SELL（ストップロス -8% / スコア低下）を生成。
    - signals テーブルへ日付単位で置換（冪等）。

### Changed
- （初回リリースのため過去互換差分なし）

### Fixed
- （初回リリースのため過去バグ修正履歴なし）
- 実装中の注意点として、いくつかの判定は価格欠損時に誤動作しないよう警告を出して判定をスキップする扱いを追加（signal_generator / _generate_sell_signals 等）。

### Security
- news_collector: defusedxml を利用して XML の脆弱性（XML Bomb 等）対策を行いました。
- news_collector: 外部 URL の正規化・トラッキングパラメータ除去、受信バイト数制限、HTTP/HTTPS のみ許可する等 SSRF / DoS を意識した実装を導入。
- jquants_client: 認証トークンの自動リフレッシュ実装時に無限再帰を防ぐため allow_refresh フラグを設けています。

### Known limitations / Notes
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装であり、コメントで実装候補を記載しています（positions テーブルに peak_price / entry_date が必要）。
- calc_forward_returns はホライズンに最大 252 を要求するバリデーションがあるため極端な長期ホライズンはエラーになります。
- .env パーサは一般的な形式に対応していますが、極端に複雑なシェル構文（複数行クォートなど）は想定外の挙動になる可能性があります。
- DB スキーマ（features, signals, ai_scores, raw_prices, raw_financials, market_calendar, positions 等）は本パッケージ外で準備する必要があります。初期化スクリプトやマイグレーションの提供は今後の課題です。

### Migration / Setup notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - （不足時は Settings のプロパティアクセスで ValueError を送出）
- 自動.envロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- DuckDB を用いるため features や raw_* テーブル等のスキーマを事前に準備してください（リリースノート内の関数は既定のテーブル名を前提に動作します）。

---

今後の計画（短期）
- positions テーブルのメタ情報（peak_price, entry_date 等）を拡張し、トレーリングストップや保有期間による自動エグジットを実装。
- execution 層（kabu ステーション API 連携）と monitoring / alerting の実装。
- DB スキーマ初期化・マイグレーションツールの提供。
- ユニットテスト／CI の整備とテストカバレッジ向上。

もし特定のモジュールについてより詳細な変更説明や、CHANGELOG の別のバージョン区分（Unreleased での作業内容等）を追加希望であれば教えてください。