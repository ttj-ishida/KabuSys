# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-19

### Added
- 基本パッケージ構成を追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョンと公開 API を定義。
- 環境変数 / 設定管理機能を追加（src/kabusys/config.py）。
  - .env / .env.local の自動ロード機能をプロジェクトルート（.git または pyproject.toml）から行う。  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env のパースは export 形式・クォート・エスケープ・インラインコメント等を考慮した堅牢な実装。
  - 必須設定を取得する _require()、Settings クラスで設定値（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境種別やログレベル等）を提供。環境値検証（有効な env / log level のチェック）を実装。
- データ取得・保存モジュール（src/kabusys/data/*）を追加:
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制御（固定間隔スロットリング）を実装し、API レート制限（120 req/min）に対応。
    - 再試行（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After を尊重するロジック、401 時のトークン自動リフレッシュ（1 回のみ）を実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装（ON CONFLICT による更新）。
    - 型変換ユーティリティ（_to_float / _to_int）。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集、URL 正規化（トラッキングパラメータ除去、キーソート、フラグメント削除）、記事 ID を SHA-256 ハッシュで生成して冪等性を確保。
    - defusedxml による XML の安全パース、受信サイズ上限（10MB）、SSRF 回避の方針、バルク INSERT チャンク化など堅牢な設計。
- 研究（research）用モジュールを追加（src/kabusys/research/*）:
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1/3/6M、200日移動平均乖離）、ボラティリティ（20日ATR、相対ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）などを DuckDB の prices_daily/raw_financials を参照して計算する関数（calc_momentum, calc_volatility, calc_value）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns, デフォルト horizons=[1,5,21]）、Spearman ランク相関による IC 計算（calc_ic）、基本統計量要約（factor_summary）、ランク付けユーティリティ（rank）。
  - 研究向けユーティリティのエクスポート（src/kabusys/research/__init__.py）。
- 戦略（strategy）モジュールを追加（src/kabusys/strategy/*）:
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した生ファクターをマージ、ユニバースフィルタ（最低株価・最低平均売買代金）、Zスコア正規化（zscore_normalize を利用）、±3 でクリップし features テーブルへ UPSERT（トランザクションを使った日付単位の置換）する build_features を実装。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付け合算で final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換する generate_signals を実装。
    - Bear レジーム判定（AI の regime_score 平均が負の場合に BUY を抑制）や保有ポジションのエグジット（ストップロス・スコア低下）ロジックを実装。
    - 重みの入力バリデーション・正規化、欠損コンポーネントの中立補完（0.5）など堅牢化。
  - strategy パッケージの公開 API を定義（src/kabusys/strategy/__init__.py）。
- その他ユーティリティ・設計上の配慮
  - DuckDB を主要な計算・格納エンジンとして利用する設計。
  - ルックアヘッドバイアス回避のため、すべて target_date 時点のデータのみを参照する方針を各モジュールで明示。
  - ロガー出力による挙動のトレース（各モジュールで logger を利用）。

### Changed
- 初回リリースのための初期実装。設計方針・インターフェースの明示（各関数は DuckDB 接続を受け取り DB のみを参照し、実際の発注 API には依存しない）。

### Fixed
- N/A（初期リリース）。ただし、入力欠損や型変換で無効な行をスキップする等の堅牢性向上を実装（save_* 系・.env パーサなどで警告ログを出力）。

### Security
- ニュース XML のパースに defusedxml を採用して XML Bomb 等の攻撃を緩和。
- ニュース収集で受信バイト数を制限し、メモリ DoS を防止。
- J-Quants クライアントでトークン管理・リフレッシュを実装し、認証処理を安全に扱う設計。

### Removed
- N/A

### Deprecated
- N/A

### Known issues / TODO
- signal_generator のエグジット条件に記載の通り、トレーリングストップ（peak_price を利用）や時間決済（保有 60 営業日超過）は未実装。positions テーブルの拡張（peak_price / entry_date 等）により今後実装予定。
- news_collector の一部処理（RSS のソース拡張や URL の詳細な検証）は今後の改善余地あり。
- execution パッケージは空のまま（発注層はまだ実装されていない）。発注ロジック・kabu ステーション連携は次フェーズの予定。

---

参考:
- パッケージバージョンは src/kabusys/__init__.py の __version__ に従って 0.1.0 を採用しています。