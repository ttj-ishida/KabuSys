# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム KabuSys の基本モジュール群を追加しました。主な追加機能・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン情報と公開モジュール一覧を定義（data, strategy, execution, monitoring をエクスポート）。

- 環境設定/ローディング機能（src/kabusys/config.py）
  - .env/.env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - コメント取り扱い（クォート有無での差異を考慮）。
  - .env の読み込みポリシー:
    - OS 環境変数 ＞ .env.local ＞ .env（.env.local が上書き可能）。
    - OS 環境変数を protected として上書きを防止。
  - Settings クラスでアプリ設定をプロパティ化:
    - 必須変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - パス類（DUCKDB_PATH / SQLITE_PATH）の Path 変換。
    - env（development / paper_trading / live）と log_level のバリデーション。
    - is_live / is_paper / is_dev のユーティリティ。

- データ取得クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装：
    - レート制限制御（_RateLimiter: 120 req/min 固定間隔スロットリング）。
    - 冪等性を考慮した DuckDB への保存（ON CONFLICT による更新）。
    - HTTP リトライ（指数バックオフ、最大 3 回）。再試行対象ステータスと Retry-After の考慮。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の取得関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - 型安全な変換ユーティリティ（_to_float / _to_int）。
    - DuckDB 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）で PK 欠損のスキップとログ出力。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS 取得から raw_news への冪等保存フロー実装方針（記事IDを正規化URLのSHA-256で生成）。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を防止。
    - HTTP/HTTPS スキーム以外の URL 拒否、SSRF に配慮。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - トラッキングパラメータ除去（utm_*, fbclid 等）と URL 正規化処理。
  - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）を導入。

- リサーチ（研究）モジュール（src/kabusys/research/）
  - factor_research.py:
    - モメンタム（1/3/6ヶ月、MA200乖離）、ボラティリティ（20日ATR/atr_pct、出来高比率/平均売買代金）、バリュー（PER、ROE）などのファクター計算。
    - DuckDB のウィンドウ関数を活用した効率的な SQL 実装。
    - データ不足時の None 処理。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns：複数ホライズン対応、範囲バッファによるスキャン最適化）。
    - IC（Spearman の ρ）計算（calc_ic / rank）。
    - ファクター統計サマリー（factor_summary）。
  - research パッケージの __all__ を整備（外部公開 API）。

- 戦略（strategy）モジュール（src/kabusys/strategy/）
  - feature_engineering.py:
    - 研究で算出された生ファクターを正規化（zscore_normalize 参照）して features テーブルへ UPSERT（冪等）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - Z スコアを ±3 でクリップ。
    - 日付単位での置換（トランザクションで削除→挿入）により原子性を確保。
  - signal_generator.py:
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ書き込む（冪等）。
    - コンポーネントスコア計算（momentum, value, volatility, liquidity, news）とシグモイド変換の適用。
    - デフォルト重みとしきい値: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10、BUY 閾値 0.60。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - エグジット条件（stop_loss -8%、final_score が閾値未満）を実装。トレーリングストップ等はいくつか未実装で注記あり。
    - signals テーブルへの日付単位置換（BEGIN/DELETE/INSERT/COMMIT）で原子性を確保。ROLLBACK の失敗はログ出力。

- パッケージ公開 API（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）
  - 主要関数（build_features, generate_signals, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize 等）を __all__ で公開。

### Security / Reliability
- ネットワーク / API:
  - J-Quants クライアントでレートリミット遵守、リトライ、トークン自動更新、ログ出力を実装。
- データ取り扱い:
  - raw データ保存処理は冪等（ON CONFLICT）で整備。
  - .env パーサは引用符やコメント、エスケープを正しく扱うよう実装。
- ニュース収集:
  - defusedxml を用いた XML パースによる安全対策、受信バイト上限などの DoS 防御を実装。

### Notes / Design decisions
- DuckDB を中心に SQL + Python で分析処理を完結する設計（外部依存を極力排除）。
- ルックアヘッドバイアス回避: 各処理は target_date 時点までの情報のみを参照することを明記・徹底。
- 一部仕様はドキュメント参照（StrategyModel.md / DataPlatform.md 等）として実装根拠を示す設計。

### Fixed
- 初回リリースのため該当なし。

### Breaking Changes
- 初回リリースのため該当なし。

---

今後の予定（例）
- execution 層と kabu ステーション API 統合（発注ロジックの実装）。
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済）実装。
- テスト・CI の整備、型注釈強化やドキュメント拡充。