# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
このリポジトリの初回公開リリースを記録しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主要な追加点・設計方針は以下の通りです。

### Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py にてバージョンと公開サブパッケージを定義 (data, strategy, execution, monitoring)。

- 環境設定管理
  - src/kabusys/config.py
    - .env および .env.local（プロジェクトルート探索）からの自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントのパースに対応する細かな .env パーサを実装。
    - 必須キー取得時のエラー処理 (_require) と値検証（KABUSYS_ENV の許容値、LOG_LEVEL の検証）。
    - 設定アクセス用に Settings クラスを提供（J-Quants / kabu API / Slack / DB パス等のプロパティ）。

- Data 層: J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 固定間隔のレートリミッター（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）と 408/429/5xx に対するリトライ制御。
    - 401 発生時の自動トークンリフレッシュ（1 回まで）を実装。モジュールレベルの ID トークンキャッシュを導入。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB へ冪等的に保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE を利用）。
    - 入力パースユーティリティ _to_float / _to_int を実装（安全な数値変換）。

- Data 層: ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集・正規化・保存パイプラインを実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 等に対する防御）。
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去）と記事 ID に SHA-256 ハッシュを利用して冪等性を確保。
    - 受信サイズ上限（10 MB）や非 HTTP(S) スキーム拒否、挿入のチャンク化（_INSERT_CHUNK_SIZE）等の堅牢化措置を実装。
    - INSERT RETURNING を想定したバルク保存戦略（DB 負荷低減・正確な挿入数取得）。

- Research 層: ファクター計算・解析
  - src/kabusys/research/factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA）を計算。データ不足時の扱いを明確化。
    - calc_volatility: 20 日 ATR、atr_pct（ATR/close）、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を厳密に制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードを取得）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターン計算（horizons の検証、1 クエリでの取得）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合、無効値除外、サンプル数閾値）。
    - factor_summary / rank: 基本統計量とランク付けユーティリティ実装。
  - research/__init__.py にて主要関数をエクスポート。

- Strategy 層
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research モジュールで計算した raw factor を結合、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用、指定カラムを Z スコア正規化・±3 でクリップし、features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
    - ルックアヘッドバイアスを防ぐ方針で target_date 時点のデータのみ参照。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重みと閾値（デフォルト threshold=0.60）をサポート。ユーザ指定 weights の検証と再スケール処理を実装。
    - AI レジームスコアの平均から Bear 判定を行い、Bear 時は BUY シグナルを抑制。
    - エグジット判定（ストップロス -8% とスコア低下）に基づく SELL シグナル生成。保有銘柄の価格欠損時の判定スキップやログ出力を実装。
    - signals テーブルへ日付単位置換（冪等）を実装。
  - strategy/__init__.py で build_features / generate_signals を公開。

- その他ユーティリティ
  - 各モジュールで logging を活用し、警告・情報レベルのメッセージを充実。
  - Look-ahead bias 対策、冪等性（ON CONFLICT / 日付単位削除→挿入）、トランザクションによる原子性保証など運用面で重要な設計方針を文書化・実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用し XML 攻撃を緩和。
- URL 正規化でトラッキングパラメータ除去、HTTP/HTTPS スキーム制限により SSRF 等のリスクを低減。
- J-Quants クライアントにおけるトークン自動リフレッシュの際に無限再帰を防ぐ仕組み（allow_refresh フラグ）を導入。

### Notes / Design decisions
- DuckDB をローカル分析ストアとして利用。各種計算は prices_daily / raw_financials / features / ai_scores / positions 等のテーブルを前提としている。
- 外部への注文発行や execution 層への直接依存は strategy 層で持たない設計（signals テーブル経由で分離）。
- 計算・保存処理はできる限り冪等にし、定期バッチや再実行に耐えるように実装。
- エラー時のリトライやバックオフ等は API 呼び出し側に集中させ、上位ロジックは例外を受け取って対処する想定。

---

開発・運用上の詳細や各関数の引数/戻り値、副作用はソース内の docstring を参照してください。質問や追記したい変更があればお知らせください。