# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-20

初回リリース。本リリースでは日本株自動売買システム「KabuSys」のコア機能を提供します。主にデータ取得・保存、ファクター計算、特徴量エンジニアリング、シグナル生成、環境設定の読み込み周りが実装されています。

### Added
- パッケージのメタ情報
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開用の __all__ に主要モジュールを追加（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする機能。
  - プロジェクトルートの検出を .git または pyproject.toml を基準に行い、cwd に依存しない探索実装。
  - .env パースの強化（コメント処理、export プレフィックス、シングル/ダブルクォート内のエスケープ対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings オブジェクトを提供し、以下の設定をプロパティ経由で取得：
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL
    - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
    - DUCKDB_PATH、SQLITE_PATH
    - KABUSYS_ENV（development|paper_trading|live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 必須設定未提供時は ValueError を送出する _require 関数。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API のレート制限（120 req/min）を守る固定間隔スロットリング RateLimiter 実装。
  - 再試行ロジック（指数バックオフ、最大3回）。408/429/5xx を対象にリトライを試行。
  - 401 を受信した場合はリフレッシュトークンから自動で id_token を更新して 1 回リトライする仕組み。
  - ページネーション対応の fetch_* 関数：
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB へ冪等的に保存する save_* 関数：
    - save_daily_quotes → raw_prices へ ON CONFLICT DO UPDATE
    - save_financial_statements → raw_financials へ ON CONFLICT DO UPDATE
    - save_market_calendar → market_calendar へ ON CONFLICT DO UPDATE
  - API 通信での JSON デコード失敗やネットワークエラーへの適切なエラーハンドリング。
  - 型変換ユーティリティ _to_float / _to_int の実装（不正値を None に変換）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集・正規化して raw_news に保存する基盤実装。
  - URL 正規化（トラッキングパラメータ削除、スキーム/ホストの小文字化、フラグメント除去、クエリソート）。
  - defusedxml を用いた XML パースで XML Bomb 等に対する防御。
  - HTTP レスポンスの最大受信バイト数制限（10MB）や SSRF 対策を想定した制約。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
  - バルク INSERT のチャンク処理（パラメータ数上限対策）。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を設定。

- 研究・ファクター計算（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）を実装：
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - calc_value（PER、ROE を prices と raw_financials から算出）
    - DuckDB 上の SQL ウィンドウ関数を活用し、営業日不足時の None ハンドリングを実装
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を実装：
    - calc_forward_returns（複数ホライズンに対する将来リターン計算、デフォルト[1,5,21]）
    - calc_ic（Spearman のランク相関による IC 計算、サンプル不足時は None）
    - rank（同順位は平均ランクで処理、丸め処理で ties 対応）
    - factor_summary（count/mean/std/min/max/median の集計）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装：
    - research モジュールから raw ファクターを取得しマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
    - 日付単位で features テーブルに置換（DELETE + BULK INSERT）して冪等性と原子性を確保

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装：
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - スコアをシグモイド変換し、欠損コンポーネントは中立値 0.5 で補完
    - 重み合算による final_score の計算（デフォルト重みを実装）
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数）
      - Bear の場合は BUY シグナルを抑制
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄をランク付けして signals テーブルへ保存
    - 保有ポジションに対する SELL 判定（ストップロス -8%、final_score が閾値未満）
    - SELL 優先ポリシー（SELL 対象は BUY から除外）
    - 日付単位で signals テーブルに置換（DELETE + BULK INSERT）して冪等性・原子性を担保
    - ユーザ指定 weights の検証（未知キー/非数値/負値を無視、合計が 1.0 でなければリスケール）

### Changed
- （初回リリースにつき既存からの変更はなし。設計上の方針や注意点を明記）
  - DB 保存は可能な限り冪等化（ON CONFLICT）およびトランザクションを用いて原子性を確保。
  - ルックアヘッドバイアス対策として、各処理は target_date 時点のデータのみを使用する設計。

### Fixed
- N/A（初回リリース）

### Security
- news_collector で defusedxml を使用し XML 攻撃を軽減。
- news_collector による受信サイズ制限、URL 正規化・スキーム検査等で SSRF / DoS リスクの低減を考慮。
- jquants_client でトークン自動リフレッシュ時の無限再帰を回避するフラグ（allow_refresh）を導入。

## 今後の予定（未実装 / TODO）
- execution 層（kabu ステーション連携）と monitoring の具体実装。
- signal_generator の追加的エグジット条件（トレイリングストップ、時間決済）は positions テーブルに peak_price / entry_date 情報を含めた上で実装予定。
- news_collector の記事→銘柄マッチング（news_symbols との紐付け）ロジックの強化。
- テストカバレッジの拡充と CI パイプラインの整備。
- パフォーマンス最適化（大量データ処理時のバルク挿入調整、DuckDB クエリの改善等）。

---

（注）この CHANGELOG は現在のコードベースから推測して作成しています。実際のリリースノート作成時はユーザー向けの変更点・既知の制限事項・互換性情報等を必要に応じて追加してください。