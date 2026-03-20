# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

※ この CHANGELOG は与えられたコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装。

### 追加 (Added)
- パッケージ骨組みを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パースの堅牢化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のエスケープ処理をサポート
    - インラインコメントの扱いを改善（クォート有無での取り扱い差分を考慮）
  - 設定アクセス用の Settings クラスを提供（プロパティ経由）:
    - J-Quants / kabu API / Slack トークン等の必須設定取得（未設定時に ValueError を送出）
    - DB パス（duckdb / sqlite）のデフォルトと Path 変換
    - 環境種別（KABUSYS_ENV）の検証（development/paper_trading/live）
    - ログレベル（LOG_LEVEL）の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データ収集・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装（認証、ページネーション、保存ロジック）。
  - レート制限対応:
    - 固定間隔スロットリング (_RateLimiter) を用いて 120 req/min を順守。
  - 再試行ロジック:
    - 指数バックオフによるリトライ（最大 3 回）、408/429/5xx を対象。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への整合的な保存関数を実装（冪等／ON CONFLICT DO UPDATE）:
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - データ変換ユーティリティ `_to_float`, `_to_int` 実装（安全な型変換）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS から記事収集・前処理・DB保存の基盤を実装。
  - セキュリティと堅牢性に関する考慮:
    - defusedxml を利用して XML 攻撃を防止
    - 受信サイズ上限（10 MB）を設定してメモリDoSを抑止
    - URL 正規化とトラッキングパラメータ除去（utm_ 等）
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を確保
    - HTTP/HTTPS スキーム検証や SSRF 回避の実装方針（コードに安全チェックあり）
  - 大量挿入を考慮したチャンク単位のバルク INSERT 実装

- リサーチ機能 (`kabusys.research`)
  - ファクター計算・探索・評価用のユーティリティ群を実装
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離(ma200_dev)等を計算
    - calc_volatility: 20日 ATR、相対 ATR(atr_pct)、20日平均売買代金、出来高比率 等を計算
    - calc_value: PER／ROE を計算（target_date 以前の最新財務データを使用）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンランク相関（IC）を計算（ties の平均ランク対応）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算
    - rank: 同順位は平均ランクとするランク付け実装（丸めで ties 検出の安定化）

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - build_features 実装:
    - research モジュールの生ファクターを取得（momentum/volatility/value）
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）適用
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ
    - DuckDB の features テーブルへ日付単位で置換（トランザクションで原子性を保証）
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - generate_signals 実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントはシグモイド変換や逆転処理を適用（例: volatility は反転）
    - デフォルトの重み (momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10) を採用。重みは引数で上書き可能。合計が 1.0 になるよう再スケール。
    - デフォルト BUY 閾値: 0.60（threshold）
    - Bear レジーム判定:
      - ai_scores の regime_score 平均が負で且つサンプル >= 3 の場合、Bear と判定して BUY を抑制
    - SELL（エグジット）判定:
      - ストップロス: PnL <= -8%（優先）
      - スコア低下: final_score < threshold
      - 未実装だが設計に記載された条件（トレーリングストップ、時間決済）は将来対応予定
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）
    - 保有ポジションの価格欠損時は SELL 判定スキップ、features に存在しない保有銘柄は score=0.0 扱いで SELL 対象にする挙動

- 公開 API の整理
  - strategy パッケージで build_features / generate_signals を __all__ として公開
  - research パッケージで主要ユーティリティ群を __all__ として公開

- ロギング
  - 各モジュールに logging を組み込み、重要な操作（取得レコード数、WARN/ERROR 条件、ROLLBACK 失敗等）で出力

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector: defusedxml の採用、受信バイト数制限、URL 正規化などにより外部入力の攻撃面を低減。
- jquants_client: トークン管理・自動リフレッシュにより認証失敗からの無限ループを回避する実装（allow_refresh フラグ等）。

### 注意事項 (Notes)
- DuckDB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals 等）はコードの期待に合わせて事前に作成する必要があります（スキーマ定義はこの変更履歴に含まれていません）。
- 一部の機能（例: positions テーブルに peak_price / entry_date を持たせたトレーリングストップ、時間決済）は設計に記載されているが未実装のため、将来のリリースで追加予定です。
- settings の必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を未設定だと起動時に ValueError が発生します。`.env.example` を参考に設定してください。
- research モジュールは外部依存（pandas 等）に依存しない実装方針です。大量データでの性能は DuckDB のクエリ最適化に依存します。

---

今後のリリースでは以下を計画しています（非確定）:
- positions 側情報を充実させたトレーリングストップ / 時間決済の実装
- ニュース -> 銘柄マッピング（news_symbols）や NLP ベースの news スコアリング統合
- テストカバレッジ追加、CI/CD ワークフロー整備

--- 

（作成者注: 上記 CHANGELOG は提供されたコード内容から仕様・設計意図を推測して作成した初期リリースの記述です。実際のリリースノートに合わせて日付や項目を調整してください。）