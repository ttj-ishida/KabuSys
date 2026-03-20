# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測される主要な追加・設計方針・品質改善の概要です。

### Added
- パッケージ基盤
  - パッケージメタ情報の追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - strategy, execution, data, monitoring を公開モジュールとしてエクスポート。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env の自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト用）。
  - .env パーサー実装（コメント・export 形式・クォート・エスケープ対応）。
  - OS 環境変数を保護する protected オプション、.env.local による上書きサポート。
  - Settings クラスで主要設定をプロパティとして公開：
    - J-Quants / kabu API / Slack トークン・チャンネル、データベースパス（DuckDB / SQLite）、環境（development/paper_trading/live）、ログレベル等。
  - 設定バリデーション（env 値・LOG_LEVEL の許容値チェック）および is_live/is_paper/is_dev 補助プロパティ。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装：
    - 固定間隔の RateLimiter（120 req/min）によるスロットリング。
    - HTTP リトライ（指数バックオフ、最大 3 回、408/429/5xx に対応）。
    - 401 時の自動トークンリフレッシュ（1 回のみリトライ）とモジュール内トークンキャッシュ。
    - ページネーション対応のフェッチ関数（株価日足、財務データ、マーケットカレンダー）。
    - DuckDB への保存関数（raw_prices/raw_financials/market_calendar）における冪等性の実装（ON CONFLICT .. DO UPDATE）。
    - fetch/save 関数は取得件数ログを出力し、PK 欠損行はスキップして警告を出す。
    - saved_at/fetched_at は UTC で記録して Look-ahead バイアスのトレーサビリティを確保。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集・正規化して raw_news テーブルへ冪等保存するロジック。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
  - セキュリティ対策：defusedxml による XML パース、防御的な最大受信サイズ（MAX_RESPONSE_BYTES）、HTTP スキームの検証、IP/SSRF に配慮した処理（実装方針記載）。
  - 挿入はチャンク化（_INSERT_CHUNK_SIZE）してバルク INSERT を実行、INSERT RETURNING を用いる設計（説明に準備）。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - Momentum/Volatility/Value の各ファクター計算を実装：
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、volume_ratio。
    - calc_value: per（株価/EPS）、roe（最新財務データの取得と結合）。
  - DuckDB を用いた効率的な SQL ウィンドウ集計で営業日欠損（祝日等）を考慮したスキャン範囲を確保。
  - 計算不能な場合は None を返すなど欠損処理を明示。

- 研究支援ユーティリティ（src/kabusys/research/feature_exploration.py）
  - 将来リターン計算（calc_forward_returns）: 複数ホライズンをサポートし 1 クエリで取得。
  - スピアマン IC 計算（calc_ic）、ランキングユーティリティ（rank）、ファクター統計要約（factor_summary）を追加。
  - 外部依存を避け、標準ライブラリ + DuckDB で完結する設計。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールの生ファクターを統合・正規化し features テーブルへ UPSERT（日付単位の置換）する build_features を実装。
  - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリップ。
  - トランザクション + バルク挿入による日付単位の原子更新（冪等性）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し各銘柄の final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込む generate_signals を実装。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付け合算（デフォルト重みを実装）。
  - ユーザ渡しの weights の検証・フォールバック・再スケール処理を実装（未知キー・非数値・負値は無視）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負で、サンプル数閾値を満たす場合）により BUY を抑制。
  - SELL 条件の実装（ストップロス -8% を優先、スコア低下によるエグジット）。保有銘柄の価格欠損時は判定をスキップして警告。
  - 日付単位の原子更新（DELETE + INSERT をトランザクションで実行）。

- 公開 API の整理（src/kabusys/research/__init__.py, src/kabusys/strategy/__init__.py）
  - 研究/戦略関連の主要関数を __all__ でエクスポート。

### Changed
- 設計上の安全性・品質指針をコード内ドキュメントに反映：
  - Look-ahead バイアス回避の方針（fetched_at の記録や target_date 時点のみ参照）。
  - 冪等性、トランザクション利用、ログ出力方針を各モジュールで明示。
  - 外部依存（pandas 等）を避け、標準ライブラリ + DuckDB で完結するポリシー。

### Fixed
- 入出力/パースの堅牢化（推定）
  - .env 読み込みでファイルオープン失敗時の警告（warnings.warn）を追加しクラッシュを回避。
  - J-Quants クライアントの HTTP エラー／ネットワークエラーでのリトライとログを実装し一時障害耐性を向上。
  - データ保存時に PK 欠損レコードをスキップしてログ出力（不正データによる例外回避）。

### Security
- ニュース収集における XML パースの安全化（defusedxml の採用）。
- RSS/URL 正規化・トラッキングパラメータ除去・受信サイズ制限などメモリ DoS / トラッキング漏洩への対策方針を明示。
- J-Quants クライアントにおける認証トークンの取り扱い（自動リフレッシュとキャッシュ）を実装、無限再帰防止ロジックを導入。

### Known limitations / TODO（ソースから推測）
- strategy の一部エグジット条件（トレーリングストップ、時間決済など）は positions テーブルに peak_price / entry_date 等の追加情報が必要で未実装。
- news_collector の詳細な RSS パース・ホワイトリスト検証や実際の SSRF 防止処理（IP 範囲チェック等）は方針レベルで記載されているが、実装の範囲は要確認。
- execution パッケージは初期状態では空（発注層の実装は今後の追加予定）。

---

このリリースノートはソースコード内容からの推測に基づき作成しています。実際の変更履歴やリリースノートに反映する際は、コミット履歴やリリース担当者の検証を行ってください。