# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従い記載しています。  
このプロジェクトはセマンティックバージョニングに従います。 (参照: src/kabusys/__init__.py の __version__ = "0.1.0")

## [Unreleased]

### 追加
- （開発中の予定や未リリースの変更があればここに記載します）

---

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py）。
  - 公開 API のエクスポート設定（data, strategy, execution, monitoring を想定）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は .git または pyproject.toml を探索し決定（CWD非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ等に対応）。
  - Settings クラスを提供し、必要な設定値（J-Quants・kabu API・Slack・DB パス・環境名・ログレベル等）をプロパティ経由で取得。必須項目未設定時は ValueError を発生。
  - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値はソース内定義）。

- データ取得（J-Quants）クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - API レート制限（120 req/min）に合わせた固定間隔スロットリング RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大試行回数、特定ステータスでのリトライ）を実装。
    - 401 Unauthorized 受信時にリフレッシュトークンから id_token を自動更新して一度だけ再試行する処理を実装。
    - ページネーション対応（pagination_key を利用）によるデータ取得。
    - データの保存ユーティリティ（DuckDB へ冪等保存）:
      - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE を使用して保存。
      - save_financial_statements: raw_financials へ冪等保存。
      - save_market_calendar: market_calendar へ冪等保存。
    - JSON デコードエラーやネットワークエラーの扱い、ロギング強化。
    - 型変換ヘルパー _to_float / _to_int を追加。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news 等へ保存する基盤を実装。
    - デフォルト RSS ソース（Yahoo Finance のカテゴリRSS）を定義。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を抑制。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）を実装。
    - defusedxml を利用して XML 攻撃（XML bomb 等）を軽減。
    - 挿入時はバルク INSERT をチャンク化してパフォーマンスと SQL 長制限に配慮。
    - 記事IDは URL 正規化後のハッシュを一意キーとして使用する設計（冪等性確保の想定）。
    - HTTP/HTTPS 以外のスキームや不正なホストへのアクセスを制限するための検証を行う設計（SSRF 対策の方針記載）。

- リサーチ（ファクター計算）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR・相対ATR・平均売買代金・出来高比率）、Value（PER・ROE）などを DuckDB 上の prices_daily / raw_financials を参照して計算。
    - 欠損・データ不足時の扱い（条件不足なら None を返す）を設計。
    - 期間を営業日ベースで扱うことを明記し、検索範囲には余裕（カレンダー日バッファ）を設ける。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（指定ホライズンのリターンを一括で取得）。
    - IC（Information Coefficient）計算（ランク相関（Spearman））calc_ic。
    - ランク変換ユーティリティ rank（同順位は平均ランク）と factor_summary（基本統計量の集計）。
    - pandas 等外部依存を避け、標準ライブラリのみで実装する方針。

  - research パッケージの __init__ で主要関数を再公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで計算した raw ファクターを取り込み、ユニバースフィルタ（最小株価・平均売買代金）を適用後、指定カラムを Z スコア正規化（外れ値は ±3 でクリップ）して features テーブルへ日付単位の置換（削除→挿入）で保存する処理を実装。
  - 正規化ユーティリティ zscore_normalize を kabusys.data.stats から利用する想定（外部モジュールとの接続点）。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いて原子性を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - シグモイド変換・欠損補完（None を中立値 0.5）・重み付け合算による final_score 計算を実装。
  - デフォルト重みと閾値を定義（デフォルト閾値 0.60）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負で一定サンプル数以上の場合に BUY 抑制）。
  - BUY シグナル生成（threshold 超）および保有ポジションに対する SELL（ストップロス、スコア低下）判定を実装。
  - positions テーブルや prices_daily を参照して、現在ポジションのエグジット判定を行うロジックを実装。
  - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で保存。
  - 未実装機能（将来的な TODO）としてトレーリングストップや時間決済に関する注記を含む（positions テーブルの追加情報が必要）。

- strategy パッケージの __init__ で主要 API を再公開（build_features, generate_signals）。

### ドキュメント（ソース内コメント・設計メモ）
- 各モジュールに詳細な docstring と設計方針・処理フローを追記。これにより実装意図、ルックアヘッドバイアス対策、冪等性 / 原子性の設計が明確化されました。

### 互換性・依存関係
- Python 3.10+ の構文（PEP 604 の型記法 a | b を使用）を想定。
- DuckDB をデータストアとして利用する前提（DuckDBPyConnection 型での I/O）。
- defusedxml（XML の安全パーサ）をニュース収集で使用する想定。
- 外部 API は J-Quants（認証トークン管理を含む）および将来的に kabuステーション API を想定（設定項目を提供）。

### 既知の制限・今後の TODO
- positions テーブルに peak_price / entry_date 等の情報がないため、トレーリングストップや時間決済は未実装（コメントで明示）。
- news_collector の詳細なストア/紐付け処理（news_symbols 等）や外部フィード追加は今後拡張予定。
- データ保存先テーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）のスキーマは別途用意する必要あり（本リリースではスキーマ定義は含まず、処理側で想定しているテーブル名やカラムをコメントで明示）。
- zscore_normalize は kabusys.data.stats に依存しており、その実装が必要。

### セキュリティ
- 外部データの取り扱いに際して以下を考慮:
  - RSS/ XML のパースに defusedxml を使用（XML爆弾対策）。
  - ニュース収集時の受信バイト上限を設定。
  - J-Quants クライアントでのトークン管理は安全にリフレッシュする設計（無限ループ回避のため allow_refresh フラグ）。
  - NewsCollector では URL 正規化・トラッキング除去・スキーム確認など SSRF/追跡対策を実装方針として明示。

---

注記:
- 初期リリースのため多くのモジュールは「データベースの想定スキーマ」に依存します。運用前に必要な DuckDB テーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）のスキーマを準備してください。
- 実行環境の設定（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）を .env に準備するか、OS 環境変数として設定してください。設定が不足すると Settings プロパティは ValueError を投げます。