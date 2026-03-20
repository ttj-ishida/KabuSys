# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

なお以下は提供されたコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを実装。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索するため、CWD に依存しない自動ロードを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応。
  - _load_env_file にて既存 OS 環境変数を保護する protected オプションを実装。
  - Settings クラスを提供し、必要な環境変数取得メソッドを公開（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）を実装。
  - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）設定を提供。

- データ取得・永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行（指数バックオフ、最大3回）を実装。408/429/5xx を再試行対象とする。
    - 401 が返った場合はリフレッシュトークンで自動的に ID トークンを更新して一度だけ再試行。
    - ページネーション対応で全ページを取得。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスの追跡を支援。
  - fetch_* 系関数を実装: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への保存関数を実装（冪等性を重視、ON CONFLICT による upsert）:
    - save_daily_quotes -> raw_prices テーブル
    - save_financial_statements -> raw_financials テーブル
    - save_market_calendar -> market_calendar テーブル
  - 型安全な数値変換ユーティリティ (_to_float / _to_int) を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集して raw_news と関連テーブルへ保存するための実装。
  - セキュリティ考慮:
    - defusedxml を用いた XML パース（XML Bomb などへの対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - URL 正規化・トラッキングパラメータ除去（utm_* 等）。
    - HTTPS/HTTP スキームの許可と SSRF リスクに配慮した実装方針（注: 実際のネットワーク検査は実装箇所に依存）。
  - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）などで冪等性を担保。
  - バルク INSERT のチャンク処理を実装。

- 研究用ファクター計算 (kabusys.research)
  - ファクター計算モジュール（factor_research）を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA による乖離）を計算。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: per / roe を raw_financials と prices_daily を使って計算。
    - 実装は DuckDB 上の SQL ウィンドウ関数を活用し、営業日欠損やウィンドウ不足時の None 処理を行う。
  - 特徴量探索モジュール（feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（<3 サンプル）時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を提供。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
  - zscore_normalize は外部のデータモジュール経由で利用可能にしている（kabusys.data.stats からインポート）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装。
    - research モジュールの calc_* から生ファクターを取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + bulk insert）して冪等性を保証。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold, weights) を実装。
    - features と ai_scores を統合して各銘柄の final_score を算出（コンポーネント: momentum/value/volatility/liquidity/news）。
    - デフォルト重みを実装（momentum 0.40 等）、ユーザー重みを受け入れて合計が 1.0 になるようスケーリング。無効値はフィルタ。
    - sigmoidal 変換・欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負で十分なサンプル数がある場合 BUY を抑制）。
    - BUY シグナル閾値デフォルト _DEFAULT_THRESHOLD = 0.60。
    - SELL（エグジット）判定を実装（ストップロス -8%、スコア低下）。positions・prices を参照して判定。
    - signals テーブルへ日付単位で置換して保存（トランザクションで原子性確保）。
    - 売り優先ポリシー: SELL と判定された銘柄は BUY 候補から除外。

- パッケージエクスポート
  - strategy モジュールから build_features / generate_signals を公開（kabusys.strategy.__init__）。
  - research パッケージから主要関数を __all__ で公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector における XML パースで defusedxml を使用、受信サイズ上限を設定するなどの安全策を追加。
- J-Quants クライアントは 401 リフレッシュの扱い・再試行戦略・レート制御を実装し、誤ったリクエスト増加やトークン漏洩リスクの低減に配慮。

### Notes / Known limitations
- execution パッケージは空の __init__ のみで、実際の注文送信ロジック（kabu API 呼び出し等）は未実装または別途実装を想定。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済など）は positions テーブルに peak_price / entry_date 等の追加情報が必要で未実装。
- news_collector の実際のネットワーク・URL 検査や SSRF 対策の詳細は実行環境に依存するため、運用時に追加の制約（接続先ホワイトリスト等）を推奨。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news など）は想定されているが、マイグレーション/スキーマ定義は別途管理が必要。

---

今後のリリースでは以下を想定:
- execution 層の実装（kabu API との通信、注文管理のトランザクション化）
- 追加エグジットルール（トレーリングストップ、時間決済）
- 単体テスト・統合テスト及び CI 設定の整備
- ドキュメントの拡充（StrategyModel.md / DataPlatform.md 等の参照実装）