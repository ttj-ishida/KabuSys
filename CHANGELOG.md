# Changelog

すべての重要な変更を Keep a Changelog の形式で記録します。  
このファイルはリリースノートを目的としており、ユーザー向けにパッケージの新機能、修正点、既知の制限などをまとめています。

注: 以下の内容は提供されたコードベースから推測して作成したものです。

## [Unreleased]

- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-20

初回リリース

### 追加 (Added)

- パッケージ骨格
  - kabusys パッケージ初期化（src/kabusys/__init__.py）: バージョン情報と主要サブパッケージのエクスポートを定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - .git または pyproject.toml からプロジェクトルートを探索して .env をロード（CWD に依存しない）。
  - .env パーサーの堅牢化:
    - コメント / export プレフィックス対応
    - シングル/ダブルクォート・バックスラッシュエスケープ対応
    - インラインコメント取り扱いの微調整
  - Settings クラスで主要な設定値をプロパティ化:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_*,
      DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
  - Path 型での DB パス処理（~ 展開など）。

- データ取得 / ストレージ (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - 固定間隔スロットルによるレート制限実装（120 req/min の制御）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）実装。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - データ変換ユーティリティ: _to_float / _to_int
    - fetched_at を UTC ISO8601 で記録（ルックアヘッドバイアスのトレースを容易に）
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存

  - ニュース収集モジュール (news_collector.py)
    - RSS フィード取得、記事正規化、raw_news への冪等保存の下地実装。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - defusedxml を使った XML パース（XML Bomb 等への対策）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート。
    - SSRF 対策や受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）などの安全対策。
    - バルク挿入チャンク化のサポート（_INSERT_CHUNK_SIZE）。

- リサーチ関連 (src/kabusys/research/)
  - ファクター計算モジュール (factor_research.py)
    - モメンタム: calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - ボラティリティ/流動性: calc_volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - バリュー: calc_value（per / roe、raw_financials と prices_daily を組合せ）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) をキーとする dict リストを返す設計
  - 特徴量探索ユーティリティ (feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、まとめて1クエリで取得）
    - IC 計算: calc_ic（Spearman のランク相関）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク関数: rank（同順位は平均ランク、丸め処理で ties の検出を安定化）

- 戦略関連 (src/kabusys/strategy/)
  - 特徴量生成 (feature_engineering.py)
    - build_features: research の生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用、Z スコア正規化→±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性確保）
    - ユニバースフィルタの閾値定義（_MIN_PRICE=300 円、_MIN_TURNOVER=5e8 円）
  - シグナル生成 (signal_generator.py)
    - generate_signals:
      - features と ai_scores を統合して momentum/value/volatility/liquidity/news 等のコンポーネントスコアを計算
      - _sigmoid, _avg_scores 等ユーティリティ実装
      - AI レジームスコア集計による Bear 判定（サンプル閾値あり）
      - BUY シグナル（閾値デフォルト 0.60）／SELL シグナル（ストップロス -8% 等）の判定
      - SELL 優先ポリシー（SELL 対象を BUY から除外）、signals テーブルへ日付単位で置換（トランザクション）
      - ユーザ提供 weights を検証・補完・再スケールするロジック

- API エクスポート
  - strategy パッケージで build_features / generate_signals を公開 (src/kabusys/strategy/__init__.py)
  - research パッケージで主要関数を __all__ に含めて公開 (src/kabusys/research/__init__.py)

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- news_collector で defusedxml を使用して XML による攻撃を軽減。
- news_collector で受信サイズ制限（10MB）を導入してメモリ DoS を緩和。
- news_collector の URL 正規化とスキームチェックにより SSRF のリスクを低減。
- jquants_client のリトライ・429 の Retry-After 尊重や 401 自動リフレッシュなど、API 通信の堅牢化。

### 内部 (Internal)

- DuckDB への書き込みは可能な限りトランザクション + バルク挿入で原子性とパフォーマンスを確保。
- ロギング（logger）を各モジュールに導入し、警告・情報を適切に出力。
- 一部の補助関数や定数（_MIN_PRICE 等）をモジュール内で定義して設定を集中管理。

### 既知の制限 / 注意点 (Known issues / Notes)

- execution パッケージの初期化ファイルは存在するが（src/kabusys/execution/__init__.py）、発注 API と結びつく実装は含まれていない。generate_signals / build_features は発注レイヤーへの直接依存を持たない設計。
- シグナルのエグジット判定において、トレーリングストップや時間決済（保有 60 営業日超）などは未実装（コード内コメントとして要件記載）。
- news_collector の記事 → 銘柄紐付け（news_symbols）や一部の細かな前処理の実装詳細は今後の実装対象。
- jquants_client の _to_int は小数を含む文字列（例 "1.9"）を None にする振る舞いがあるため、外部データの形式に依存する部分は注意が必要。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）が前提になっている。スキーマ作成は別途必要。

### 破壊的変更 (Breaking Changes)

- 初回リリースのため該当なし。

---

著者: 自動生成（コードベースから推測）  
注: 実際のリリースノートは実運用での変更履歴・コミットメッセージに基づいて調整してください。必要であれば、各機能ごとにより詳細な説明（例: SQL スキーマ、引数の仕様、例外挙動、ログ出力の種類）も追記します。