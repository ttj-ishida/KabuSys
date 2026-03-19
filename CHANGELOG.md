# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

全般方針: 重要なユーザ向け・開発者向けの変更点（追加・修正・注意点）をモジュール単位で記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコアライブラリを追加しました。主な追加項目は以下の通りです。

### Added
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - public API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 / 設定読み込み (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を追加（OS 環境変数を保護して読み込み順: OS > .env.local > .env）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（__file__ ベースのため CWD 非依存）。
  - パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理、トラッキングコメント処理などに対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テストで利用想定）。
  - Settings クラスを提供し、必須環境変数取得時に未設定なら ValueError を送出するプロパティを実装（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）。
  - 環境値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
  - デフォルト DB パス（DUCKDB_PATH / SQLITE_PATH）を Path オブジェクトとして扱うユーティリティ。

- データ取得・永続化（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装（認証、ページネーション、取得関数、保存関数）。
  - レート制限（120 req/min）対応の固定間隔スロットリング _RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429/5xx を対象）を実装。
  - 401 時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライする仕組みを実装（無限再帰防止のフラグ allow_refresh）。
  - fetch_* 系関数:
    - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX カレンダーを取得。
  - save_* 系関数（DuckDB への保存、冪等性を確保）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE で保存。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE で保存。
  - データ変換ユーティリティ:
    - _to_float / _to_int：空値・フォーマット不整合を安全に処理するルールを実装。
  - fetched_at を UTC ISO 形式で記録し、データ取得時刻をトレース可能に（Look-ahead バイアス対策）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS からの記事収集機能を追加（デフォルト RSS ソース: Yahoo Japan business）。
  - 記事前処理: URL 正規化（トラッキングパラメータ削除、フラグメント除去、クエリソート、スキーム/ホスト小文字化）、テキスト正規化。
  - セキュリティ対策:
    - defusedxml を用いて XML Bomb 等の攻撃を防止。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - URL 正規化とトラッキングパラメータ除去ロジックを実装。
    - SSRF を想定した検討（HTTP/HTTPS スキーム以外の拒否等を想定した設計方針）。 
  - DB 保存はバルク挿入とトランザクションで行う（冪等化のため ON CONFLICT DO NOTHING / INSERT RETURNING を想定した実装方針）。

- 研究（research）モジュール
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）を DuckDB の SQL ウィンドウ関数で計算。
    - Volatility（20日 ATR / atr_pct / avg_turnover / volume_ratio）を実装。true_range の NULL 伝播を考慮して正確なカウントを実現。
    - Value（per / roe）を raw_financials と prices_daily を結合して計算。直近報告の財務データを ROW_NUMBER で抽出。
    - 計算範囲バッファ（営業日換算のカレンダー日バッファ）を導入して週末・祝日欠損に対応。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns（指定ホライズンのリターンをまとめて取得）。
    - IC（Information Coefficient）calc_ic（Spearman ランク相関）とランク付けユーティリティ rank。
    - factor_summary：各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージから主要関数をエクスポート（calc_momentum/calc_volatility/calc_value/zscore_normalize 等）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research で計算した生ファクターを正規化・合成して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価: 300 円、20日平均売買代金 >= 5 億円）を適用。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
  - DuckDB トランザクションで日付単位の削除→挿入を行い冪等性を保証（BEGIN/COMMIT/ROLLBACK 処理、ROLLBACK 失敗時の警告ログあり）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア final_score を計算し、signals テーブルへ出力する generate_signals を実装。
  - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算するユーティリティ実装（シグモイド変換、欠損補完は中立 0.5）。
  - 重みの受け渡し:
    - _DEFAULT_WEIGHTS を提供、ユーザ指定 weights は検証（未知キーや負値・非数は無視）、合計が 1.0 でない場合は再スケール。
  - Bear レジーム判定: ai_scores の regime_score の平均が負でサンプル数が閾値以上の場合に BUY シグナルを抑制。
  - エグジット判定（_generate_sell_signals）:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が threshold 未満（score_drop）
    - 価格欠損時は SELL 判定をスキップして誤クローズを防止する挙動を採用。
  - signals テーブルへの書き込みは日付単位の置換（トランザクション＆バルク挿入）で冪等性を確保。ROLLBACK 時のログ出力あり。

### Security
- XML パースに defusedxml を採用（ニュース収集モジュール）。
- ニュース取得での受信サイズ上限と URL 正規化によりメモリ DoS / トラッキングパラメータ / SSRF リスクを低減する設計。
- API クライアントでの認証情報は Settings 経由で必須化しており、トークン自動更新機構を実装。トークンリフレッシュ時の無限ループを防止するフラグを導入。

### Notes / Implementation details / Developer hints
- DuckDB を主要な解析ストアとして利用。多くの計算は SQL ウィンドウ関数で実装されているため、テーブルスキーマ（prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions / market_calendar 等）の整合性に依存します。
- 多くの関数は「target_date 時点の情報のみを使用する」設計（ルックアヘッドバイアス防止）。
- 破壊的な自動挙動（.env 自動ロード）は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- jquants_client の内部レート制御はモジュール単位のシンプルなスロットリングで、並列化が必要な場合は使用方法に注意（モジュール内部の _RateLimiter はプロセス内単一インスタンス）。
- news_collector の設計では記事 ID を URL 正規化のハッシュ等で冪等化する方針（実装コメント有り）。実装の詳細（ハッシュ長など）はコード上の方針に従っている。

---

今後の予定（想定）
- トレーリングストップや時間決済などのエグジット条件の追加（positions テーブルに peak_price / entry_date が必要）。
- ニュースと銘柄の紐付け（news_symbols）や記事の実際の DB 挿入ロジックの拡張。
- 並列/分散取得時のレートリミット調整、より堅牢なバックオフ戦略の導入。

以上。質問や特定モジュールの変更履歴をより詳細に出力したい場合は、そのモジュール名を指定してください。