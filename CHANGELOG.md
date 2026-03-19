# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の様式に準拠しています。  

フォーマット: [バージョン] - YYYY-MM-DD  
カテゴリ: Added / Changed / Fixed / Deprecated / Removed / Security

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株の自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測される主要な追加・設計方針・既知の制約点です。

### Added
- パッケージ基盤
  - パッケージメタ情報を公開（kabusys.__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理（kabusys.config）
  - .env ファイル自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env / .env.local 読み込みの優先順位制御（OS 環境変数を保護）。
  - .env 行パーサ実装（コメント・export プレフィックス・クォート／エスケープ対応、インラインコメント処理）。
  - 環境変数の必須チェック機能（_require）と Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack 設定、DB パス等）。
  - 設定値バリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - API レート制御（固定間隔スロットリングで 120 req/min を遵守する RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応（pagination_key によるループ）。
  - DuckDB への保存ユーティリティ（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT を使った冪等保存。
  - 数値変換ユーティリティ（_to_float/_to_int）を用意し、異常値や不適切なフォーマットに安全に対処。
  - レスポンス JSON のデコードエラーや HTTP エラーのハンドリングとログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの収集・前処理と raw_news テーブルへの冪等保存。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリのソート）。
  - セキュリティ対策: defusedxml を使用して XML 攻撃を緩和、受信サイズ上限（MAX_RESPONSE_BYTES）を設定、HTTP/HTTPS 以外のスキーム拒否等が想定される設計。
  - 記事ID を URL 正規化後の SHA-256 ハッシュで生成して冪等性を担保。
  - バルク INSERT チャンク化（_INSERT_CHUNK_SIZE）により SQL 長やパラメータ数上限へ配慮。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）:
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily を結合
    - DuckDB を用いた SQL ベース実装（外部依存最小化）
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns（複数ホライズン対応、営業日扱いの LEAD による実装）
    - calc_ic（スピアマンのランク相関（IC）を実装。サンプル不足時は None を返却）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランク処理、浮動小数点の丸め対策あり）
  - research パッケージから主要関数をエクスポート。

- 戦略（kabusys.strategy）
  - 特徴量生成（feature_engineering.build_features）:
    - research の生ファクターを取得し統合、ユニバースフィルタ（株価>=300円、20日平均売買代金>=5億円）適用。
    - Zスコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で冪等）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - スコア変換にシグモイド関数を使用、欠損コンポーネントは中立値 0.5 で補完。
    - 重みの合成（デフォルト重みあり）。ユーザー入力 weights は検証・正規化して合計が 1.0 になるようスケーリング。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら BUY を抑制。サンプル数閾値あり）。
    - BUY は閾値（デフォルト 0.60）超で生成、SELL はストップロス（-8%）およびスコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位で置換。
    - トランザクションとエラーハンドリング（ROLLBACK ログ）を実装。

### Changed
- （初版のため過去からの変更なし）

### Fixed
- （初版のため過去の不具合修正履歴なし）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- ニュースパーサに defusedxml を採用して XML ベースの脆弱性に配慮。
- news_collector で受信バイト数上限を設定してメモリ DoS を軽減。
- jquants_client でトークン管理・再試行の制御により認証エラーやレート制限への堅牢性を向上。

### Known limitations / Notes（既知の制約・今後の要検討点）
- execution 層は空のパッケージ（src/kabusys/execution/__init__.py が存在）であり、実際の注文送信・ブローカー連携は未実装。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- AI（news）スコアの扱いは中立値補完やシグモイド変換など簡易実装。AI モデル連携時のスコア正規化戦略は要検討。
- calc_forward_returns は営業日ベースのホライズンを想定しているが、実運用では市場カレンダー（祝日・半日）との整合性確認が必要。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布・インストール環境では KABUSYS_DISABLE_AUTO_ENV_LOAD による制御が必要な場合がある。
- news_collector の詳細な SSRF/ネットワーク検査（例: 外部ホストへの接続先 IP 制御）は設計方針に含まれるが、実装の呼び出し側で追加の保護が必要な場合がある。

### Migration / Upgrade notes
- 既存環境から導入する際は .env.example を参考に必須環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を設定してください。
- DuckDB/SQLite の初期スキーマ（tables: raw_prices, raw_financials, market_calendar, features, ai_scores, signals, positions, prices_daily 等）が前提となります。初期スキーマは別途用意する必要があります。

---

貢献・バグ報告・改善提案はリポジトリの Issue を通してお願いします。