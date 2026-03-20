# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に従っています。  

※ 本 CHANGELOG はリポジトリ内のソースコードから推測して作成した初版リリースノートです。

## [0.1.0] - 2026-03-20

初回リリース。日本株の自動売買システム「KabuSys」の基本コンポーネントを実装しました。主にデータ取得・保存、ファクター計算、特徴量作成、シグナル生成、設定管理に関するモジュールを含みます。

### Added
- パッケージ基礎
  - src/kabusys/__init__.py にパッケージ情報（バージョン 0.1.0、公開 API）を追加。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込み順序: OS 環境 > .env.local > .env
    - プロジェクトルート検出は .git または pyproject.toml を探索して行う（CWD 非依存）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパースロジックを拡張:
    - コメント行・export プレフィックスに対応、シングル/ダブルクォートとエスケープ処理を考慮。
    - インラインコメント処理（クォートなしの場合は直前が空白/タブの '#' をコメントとみなす）。
  - Settings クラスを提供し、必須環境変数をチェック・取得するプロパティを実装。
    - 必須例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値や検証付きのプロパティあり（KABUSYS_ENV / LOG_LEVEL / DB パス等）。
    - 有効な環境モード: development / paper_trading / live
    - 有効なログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

- データ取得クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（価格・財務・市場カレンダー取得）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を RateLimiter で実装。
  - 再試行ロジック: 指数バックオフ（最大3回）、408/429/5xx を対象。
  - 401 応答時にはトークン自動リフレッシュを1回行い再試行する仕組みを実装。
  - ページネーション対応（pagination_key を使った繰り返し取得）。
  - データ保存関数（DuckDB 向け）を実装・冪等化（ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices テーブル
    - save_financial_statements -> raw_financials テーブル
    - save_market_calendar -> market_calendar テーブル
  - 取得時刻（fetched_at）は UTC ISO8601 で保存し、Look-ahead バイアスのトレースを可能に。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存する実装。
  - セキュリティ・堅牢化:
    - defusedxml を利用して XML 攻撃（XML Bomb 等）を防止。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES: 10MB）でメモリ DoS を緩和。
    - HTTP/HTTPS 以外のスキームを拒否するなど SSRF 対策を検討（実装方針あり）。
  - 挿入はバルクかつトランザクションで行い、ON CONFLICT / INSERT RETURNING で冪等性・挿入数の正確化を意識。
  - デフォルト RSS ソースのサンプル（yahoo_finance）を用意。

- 研究用モジュール（src/kabusys/research/）
  - factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算を実装。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: 最新の財務データ（eps/roe）と株価から PER / ROE を算出。
    - 各関数は prices_daily / raw_financials のみ参照。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算。
    - factor_summary / rank: 基本統計量とランク関数を実装。
  - research パッケージの __all__ を整備。

- 戦略モジュール（src/kabusys/strategy/）
  - feature_engineering.py:
    - research で計算した raw ファクターを統合し features テーブルへ保存する処理を実装。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - Z スコア正規化（外部 zscore_normalize を使用）と ±3 のクリップを実施。
    - 日付単位で置換（DELETE + bulk INSERT をトランザクションで実行）し冪等性を確保。
  - signal_generator.py:
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存。
    - 重み付き合算（デフォルト重みを実装）・閾値（デフォルト 0.60）をサポート。
    - AI の regime_score を集計して Bear レジーム（市場平均が負）を検出し、Bear 時は BUY を抑制。
    - SELL 判定（ストップロス -8%、score 未満）を実装。保有中の価格欠損処理や features 欠損時の扱いも記載。
    - 重みの検証・正規化（不正値スキップ、合計が 1 でない場合のリスケール）を実装。
    - 日付単位置換（DELETE + INSERT）で冪等性を確保。

- 共通ユーティリティ
  - data.stats.zscore_normalize（参照のみ: import と使用箇所あり）
  - 型チェック・欠損値処理を一貫して実施する実装方針。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を採用、受信サイズ制限や URL 正規化などを導入。
- J-Quants クライアントでトークンリフレッシュ時の無限再帰を防ぐ設計（allow_refresh フラグ）。

### Known issues / Limitations
- signal_generator のエグジット条件でコメントにあるトレーリングストップ（peak_price に基づく）や保持期間による時間決済は未実装。positions テーブルに peak_price / entry_date 等の追加情報が必要。
- news_collector の一部セキュリティ対策は設計方針に記載されているが、実運用における追加検証（DNS/IP フィルタやプロキシ経由の取得など）が必要な場合あり。
- research/feature_exploration は外部ライブラリ（pandas 等）に依存しない実装だが、大規模データや高度な分析では性能や利便性の観点で追加実装が考慮される。
- 設定値（環境変数）の必須チェックは厳格に行われるため、本番導入前に .env を準備する必要あり。例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD。

### Migration / Upgrade notes
- 初回リリースのため既存ユーザー向けのマイグレーション手順は不要です。導入時は以下を確認してください:
  - .env（または環境変数）に必須キーを設定すること。
  - DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals など）を事前に準備すること（DDL は別途提供される想定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使えば自動 .env ロードを抑止可能。テスト環境等で利用してください。

---

（今後のリリースでは Unreleased セクションを用いて次バージョンの変更点を記録してください。）