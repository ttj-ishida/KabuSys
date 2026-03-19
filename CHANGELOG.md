# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このパッケージの初期バージョンは 0.1.0 です。

全般
- バージョン: 0.1.0
- リリース日: 2026-03-19

## [0.1.0] - 2026-03-19

### Added
- パッケージの基本構成を追加。
  - パッケージルート: `kabusys`（src/kabusys）。
  - エクスポート: `data`, `strategy`, `execution`, `monitoring` をパッケージ公開（src/kabusys/__init__.py）。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 設定・環境変数管理（src/kabusys/config.py）を追加。
  - `.env` / `.env.local` を自動的にプロジェクトルート（.git または pyproject.toml を基準）から読み込む自動ロード機能を実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - `.env` パーサーの実装:
    - `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理に対応。
    - コメントや無効行をスキップする堅牢なパース。
  - OS 環境変数を保護するため、既存の環境変数を保護する protected ロジックを実装（`.env.local` は `override=True` だが protected によって OS 環境を上書きしない）。
  - 必須値チェック関数 `_require` と、Settings クラスでアプリケーション設定（J-Quants トークン、kabu API 周り、Slack、DB パス、環境・ログレベル検証など）をプロパティとして提供。
  - `KABUSYS_ENV` および `LOG_LEVEL` の検証（許容値外は ValueError を送出）。

- データ取得・保存ライブラリ（src/kabusys/data/*）を追加。
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx をリトライ対象とする。
    - 401 応答時のリフレッシュトークンによる ID トークン自動更新を 1 回だけ行い再試行する仕組みを実装。
    - ページネーション対応（pagination_key の利用）で fetch 関数を実装:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - レスポンスのパース/型変換ユーティリティ `_to_float`, `_to_int` を提供。
    - モジュールレベルの ID トークンキャッシュを実装し、ページネーション中のトークン共有を行う。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからの記事収集を実装（デフォルトに Yahoo Finance のビジネスカテゴリ）。
    - URL 正規化（トラッキングパラメータ削除、クエリパラメータソート、フラグメント削除、スキーム/ホストの小文字化）。
    - 受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）、XML パースに defusedxml を利用するなど安全性を考慮。
    - 記事 ID を正常化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - DB 挿入はバルク/チャンク化してトランザクションで処理し、ON CONFLICT DO NOTHING（重複排除）を想定。

- 研究（research）モジュール（src/kabusys/research/*）を追加。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - DuckDB の SQL とウィンドウ関数を用いた効率的な実装。
  - 特徴量探索ツール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）による IC 計算。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位を平均ランクとするランク付け関数（丸め処理を導入して ties の扱いを安定化）。

- 戦略（strategy）モジュール（src/kabusys/strategy/*）を追加。
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定日（target_date）分を日付単位で削除してから挿入する冪等処理を実装。
    - 正規化: zscore_normalize を利用し ±3 でクリップ。
    - DuckDB トランザクションによる日付単位の置換（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試みて警告）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - final_score は重み付き合算（デフォルト重みを実装）。weights の検証・正規化（非数や負値は無視、合計を 1 に再スケール）。
    - BUY シグナル閾値（デフォルト 0.60）、Bear レジーム判定（ai_scores の regime_score の平均が負である場合に BUY を抑制）。
    - エグジット（SELL）判定:
      - ストップロス（終値/avg_price - 1 <= -8%）
      - final_score が閾値未満
      - 価格欠損時には SELL 判定をスキップして警告を出力（誤クローズ防止）。
    - signals テーブルへの日付単位の置換（トランザクション）を実装。
    - 最終的な BUY/SELL 件数をログ出力して返却。

- パッケージ公開関数のエクスポート（src/kabusys/strategy/__init__.py、src/kabusys/research/__init__.py）。

### Changed
- （初期リリースに相当のまとめ。設計上の方針を明確化）
  - ルックアヘッドバイアスを防ぐ方針を明示（すべて target_date 時点のデータのみ参照する実装）。
  - 本番発注レイヤ（execution）や外部の発注 API への依存を避け、戦略層はシグナル生成に専念する分離設計。
  - DuckDB の SQL 実行は可能な限り単一クエリでデータを取得するよう最適化（パフォーマンス配慮のコメント追加）。

### Fixed / Robustness improvements
- 環境変数パーサーの堅牢化:
  - クォート内のバックスラッシュエスケープ処理対応（"\'" 等）。
  - クォートなしの値でのインラインコメント扱い（直前がスペース/タブの場合のみコメントとみなす）を明示。
  - 空キーや不正な行をスキップする安全性向上。

- DB 書き込み時の堅牢性:
  - features / signals の日付単位置換をトランザクションで保護し、例外発生時に ROLLBACK を試みて失敗の際は警告を出力する実装。
  - raw_* 保存関数で PK 欠損行はスキップし、スキップ件数を警告ログに出すようにした。

- シグナル生成時の数値エッジケース対応:
  - weight 辞書の妥当性チェック（非数 / NaN / Inf / 負値 / bool を弾く）。
  - コンポーネントスコアが None の場合は中立 0.5 を補完して不当に降格しないように実装。
  - _sigmoid のオーバーフロー（非常に大きい z）を安全に処理。

- データ取得の堅牢化:
  - HTTP エラー時のリトライで 429 の Retry-After ヘッダを優先して待機時間を決定。
  - ネットワークエラー（URLError / OSError）時もリトライするロジックを導入。
  - JSON デコードエラーを明示的に RuntimeError として扱う。

### Security
- ニュース収集で defusedxml を利用し XML-related の攻撃（XML bomb 等）に配慮。
- ニュース URL の正規化でトラッキングパラメータを除去し、ID を正規化して冪等性を保証。
- ニュース取得における受信サイズ制限でメモリ DoS を軽減。
- J-Quants クライアントでは ID トークン・リフレッシュの取り扱いを明確化し、無限再帰を防止（allow_refresh フラグ）。

### Known issues / TODO
- strategy のエグジット条件の一部（トレーリングストップや時間決済）は未実装（コメントで将来的実装案を記載）。
- execution / monitoring パッケージはインターフェース準備のみ（現時点で発注実行層の実装は含まれていません）。
- 一部の関数（特にニュース関連の HTTP フェッチ部分）は外部環境（ネットワーク、RSS フィードの多様性）に依存するため運用時の追加ハードニングが必要。

---

以上が初期リリース（0.1.0）の主な変更点です。必要であれば、各モジュールごとの詳細な変更ログ（関数一覧、引数/返り値の仕様、例外挙動等）を追記します。どのモジュールの詳細を優先して記載しますか？