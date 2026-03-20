# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは主にコードベースから推測して生成された初期リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムの基盤機能を実装。

### Added
- パッケージ基盤
  - パッケージ初期化およびバージョン管理（kabusys __version__ = 0.1.0）。
  - サブモジュール公開インターフェース: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env / 環境変数の自動読み込み機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD非依存）。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - コメント行 / export 形式対応、シングル／ダブルクォートのエスケープ処理、インラインコメント処理（条件付き）。
  - _load_env_file による保護キー（protected）・override オプション。
  - Settings クラスで必須環境変数取得（_require）と検証:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の検証。
    - パス設定（DUCKDB_PATH / SQLITE_PATH）の Path 変換ユーティリティ。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出しラッパ: ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - レート制限制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
    - リトライロジック: 指数バックオフ、最大リトライ回数、HTTP 408/429/5xx 再試行、429 の Retry-After 優先処理。
    - 401 Unauthorized を検知した場合の ID トークン自動リフレッシュ（1回のみ再試行）およびトークンキャッシュの実装。
    - JSON デコード例外処理、ネットワークエラー処理を実装。
    - DuckDB への保存ユーティリティ:
      - save_daily_quotes: raw_prices テーブルへの冪等保存（ON CONFLICT DO UPDATE）。PK 欠損行はスキップして警告。
      - save_financial_statements: raw_financials テーブルへの冪等保存（ON CONFLICT DO UPDATE）。PK 欠損行はスキップ。
      - save_market_calendar: market_calendar への保存（ON CONFLICT DO UPDATE）。HolidayDivision の解釈を実装。
    - データ整形ユーティリティ: _to_float / _to_int（変換ルールと欠損扱いの明確化）。
    - 取得時に fetched_at を UTC ISO 形式で付与（Look-ahead バイアス可追跡性向上）。
  - ニュース収集 (news_collector.py)
    - RSS フィード取得・解析フレームワークの下地実装。
    - 記事ID 生成設計: URL 正規化 → SHA-256 ハッシュ（先頭部分を採用）による冪等性確保（トラッキングパラメータ除去）。
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策。
    - URL 正規化処理 (クエリのトラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、パラメータソート) を実装。
    - raw_news / news_symbols などへの保存を想定したバルク挿入のチャンク分割設計（_INSERT_CHUNK_SIZE）。
    - HTTP スキーム/ホスト/SSRF に関する設計指針（実装に必要なユーティリティを準備）。

- リサーチ機能 (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算を実装（DuckDB SQL ベース）。
    - Volatility: 20日 ATR（atr_20）／相対 ATR（atr_pct）／avg_turnover／volume_ratio 計算を実装。true_range の NULL 伝播を厳密に扱う実装。
    - Value: prices_daily と raw_financials を組み合わせた PER / ROE の取得。
    - 計算に用いるウィンドウ／スキャン範囲やデータ不足時の None 扱い等の設計方針を実装。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算(calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）に対応し、LEAD を用いた一括取得。
    - IC（Information Coefficient）計算(calc_ic): スピアマンのランク相関（ties は平均ランク）を実装。サンプル不足時は None。
    - 統計サマリー(factor_summary): count/mean/std/min/max/median を計算するユーティリティ。
    - ランク変換ユーティリティ(rank): 同順位を平均ランクにする実装（丸め処理で ties 検出漏れを低減）。

- 戦略層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research モジュールの生ファクターを統合して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5億円 の閾値を適用。
    - 正規化: 指定列を Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - データベース操作は日付単位で削除→挿入のトランザクション置換（原子性確保）。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合して final_score を計算する generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティを実装。
      - シグモイド変換、欠損値は中立 0.5 で補完。
      - value スコアは PER に基づく逆数的な設計（PER=20→0.5）。
    - 重み付け: デフォルト重みを提供し、ユーザ渡しの weights は検証・正規化して合計1.0へスケーリング。
    - BUY シグナル閾値デフォルト 0.60。Bear レジーム判定時は BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス: 損益率 <= -8% で即売却。
      - スコア低下: final_score が閾値を下回る場合に売却。
      - 保有銘柄に対して価格欠損時は SELL 判定をスキップ（誤クローズ防止）。features に存在しない保有銘柄は score=0 と見なして SELL 対象に。
    - SELL 優先ポリシー: SELL 対象は BUY リストから除外、ランクは再計算。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性確保）。

- 共通設計上の注意点・安全性
  - Look-ahead bias 回避設計（target_date 時点までのデータのみ使用、fetched_at の記録等）。
  - DuckDB を想定した SQL ベースの高速集計実装。
  - 冪等性とトランザクション処理を重視した DB 書き込み。
  - ロギングと失敗時のロールバック／警告出力を実装。

### Changed
- 初期リリースにつき過去リリースからの変更はありません。

### Fixed
- 初期リリースにつき既知のバグ修正記録はありません。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Security
- news_collector で defusedxml を使用し、XML 脆弱性（XML Bomb 等）に対策。
- J-Quants クライアントでトークン管理（自動リフレッシュ）・レート制御・安全なリトライ実装。
- RSS / URL 正規化・トラッキングパラメータ除去・受信サイズ制限等による入力検証および DoS/SSRF 対策の設計を反映。

### Breaking Changes
- 初版のため互換性破壊はありません。

---

注:
- 上記はソースコード（docstring・実装内容）から推測して作成した CHANGELOG です。実際のリリースノートには、テスト結果・マイグレーション手順・既知の問題点などを追記することを推奨します。