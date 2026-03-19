 KEEP A CHANGELOG 準拠 — CHANGELOG.md

全体方針
- このプロジェクトは日本株自動売買システム "KabuSys" の初期リリース（v0.1.0）を想定しています。
- 各項目はソースコードから推測して記載しています（実装済み機能、設計方針、既知の制限など）。

[0.1.0] - 2026-03-19
Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン 0.1.0 を定義し、公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサを実装（export KEY=val 形式のサポート、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - 環境設定クラス Settings を提供：
    - 必須項目取得時に未設定なら例外を投げる _require。
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを用意（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG, INFO, ...）の値検証。
    - duckdb / sqlite のデフォルトパス指定機能。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - レート制限制御（_RateLimiter, デフォルト 120 req/min 固定スロットリング）。
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の再試行、429 の Retry-After 対応）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有。
    - ページネーション対応のフェッチ関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等性を保障する ON CONFLICT による upsert 実装）:
      - save_daily_quotes → raw_prices テーブル
      - save_financial_statements → raw_financials テーブル
      - save_market_calendar → market_calendar テーブル
    - データ変換ユーティリティ _to_float / _to_int（堅牢な変換と不正値の無視）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news へ保存するロジックを実装（仕様ベース実装）。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - 記事IDを URL 正規化後の SHA-256 ハッシュ先頭 32 文字で生成して冪等性確保。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリパラメータソート。
    - defusedxml を利用して XML 攻撃（XML Bomb 等）を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES＝10MB）など DoS 対策。
    - SSRF・不正スキーム対策のため URL 検証（実装のための準備：ipaddress, socket の利用あり）。
    - DB 保存はトランザクションとバルク挿入（チャンク化）で効率化。INSERT 時の実際に挿入された数を返すことを想定。

- 研究用モジュール（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算（DuckDB SQL ウィンドウ関数利用）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: 直近の raw_financials を用いた PER/ROE 計算（価格と結合）。
    - 実装は prices_daily / raw_financials のみ参照（外部依存なし）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的クエリ。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の count／mean／std／min／max／median を算出。
    - rank: 同順位は平均ランクとなるランク化処理（丸めによる tie 対応を実施）。
  - research パッケージの __all__ に主要関数を公開。

- 戦略モジュール（src/kabusys/strategy/）
  - feature_engineering.py:
    - build_features(conn, target_date): research のファクター計算関数（calc_momentum, calc_volatility, calc_value）を呼び出して生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを Z スコア正規化して ±3 でクリップし、features テーブルへ日付単位で置換（DELETE → INSERT のトランザクションによる原子性）。
    - 正規化対象カラムとクリップ閾値を定数化。
  - signal_generator.py:
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合し最終スコア（final_score）を計算して BUY/SELL シグナルを生成、signals テーブルへ日付単位で置換。
    - コンポーネントスコア:
      - momentum（momentum_20, momentum_60, ma200_dev のシグモイド平均）
      - value（PER に基づく逆比例式）
      - volatility（atr_pct の Z スコアの反転にシグモイド）
      - liquidity（volume_ratio のシグモイド）
      - news（AI スコアをシグモイドで変換、未登録は中立）
    - 重みはデフォルト値を提供し、ユーザ指定は検証・補完・再スケールされる（不正値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3）により BUY を抑制。
    - SELL 条件（実装済み）:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - 未実装（注記あり）: トレーリングストップ、時間決済（要 positions テーブルの追加情報）。
    - SELL を優先し、BUY のランキングを再付与するポリシー。
    - トランザクション + バルク挿入で signals テーブルを更新（冪等）。

Changed
- なし（初回リリース相当）。

Fixed
- なし（初回リリース相当）。

Security
- RSS パースで defusedxml を利用し XML インジェクション対策を実施。
- .env の自動読み込み時、既存 OS 環境変数は保護（protected set）され上書きされない挙動を導入。
- J-Quants クライアントで 401 時のトークン自動リフレッシュを実装し、無限再帰を回避するため allow_refresh フラグを導入。

Documentation
- 各モジュールに docstring と処理フロー／設計方針の注記あり（コード内に実装）。

Known limitations / Notes
- positions テーブルに peak_price / entry_date 等のカラムがないため、トレーリングストップや時間決済の条件は未実装（signal_generator に注記あり）。
- news_collector の実装は堅牢化のための多くの対策を備えているが、外部ネットワーク／DNS や HTTP レスポンスの実装詳細は運用環境に依存するため追加の検証が必要。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, raw_financials, features, ai_scores, positions, signals 等）は本 CHANGELOG に含めていない。実行前に適切なスキーマを用意する必要がある。
- ログ出力や例外ハンドリングは基本的に実装されているが、運用時のログレベル設定や監視（monitoring モジュール）は別途整備が必要。
- 外部ライブラリ依存を極力避ける設計（research では pandas 等を使用しない）だが、大規模データや高度な分析ではパフォーマンス／利便性の面で追加ライブラリ導入を検討する余地がある。

開発者向け補足
- パッケージエントリポイントの version は src/kabusys/__init__.py の __version__ を更新してください。
- テストや CI で .env 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントのレートリミット・リトライ設定は定数で制御可能（_RATE_LIMIT_PER_MIN, _MAX_RETRIES 等）。

今後の改善案（提案）
- signals / positions テーブル設計の拡充（peak_price, entry_date 等）とそれに基づくトレーリングストップ実装。
- news_collector の URL 検証・ホワイトリスト/ブラックリストの強化と非同期フェッチ対応。
- monitoring モジュールの実装（Slack 通知、ヘルスチェック、アラートルールの追加）。
- 単体テスト・統合テストの追加（DuckDB を使ったテストフィクスチャの整備）。

--- End of CHANGELOG ---