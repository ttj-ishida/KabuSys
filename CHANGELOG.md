# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

なお、この CHANGELOG はリポジトリ内のコードから実装内容を推測して作成した初版の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。システム全体の基盤機能（データ取得・保存、ファクター計算、特徴量生成、シグナル生成、環境設定、ニュース収集、Research用ユーティリティ）を実装しました。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン情報（0.1.0）と公開モジュール一覧を定義。

- 環境設定
  - robust な .env / 環境変数読み込み機能（src/kabusys/config.py）。
    - プロジェクトルートを .git / pyproject.toml から探索して自動で .env, .env.local を読み込む。
    - .env ファイルのパースロジックを独自実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - OS 環境変数の保護（protected keys）や override 挙動をサポート。
    - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - Settings クラスによる型付き・検証付き設定アクセサ（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル 等）。

- データ取得・保存（J-Quants）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリング（120 req/min）によるレート制御。
    - リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先利用、408/429/5xx をリトライ対象に設定。
    - 401 を検知した場合の自動トークンリフレッシュ（1 回）と再試行。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）：
      - INSERT ... ON CONFLICT DO UPDATE を使用し重複を排除。
      - fetched_at に UTC タイムスタンプを記録。
    - ネットワーク/HTTP の堅牢性を考慮した実装（タイムアウト、JSON デコードエラーハンドリング等）。
    - 型変換ユーティリティ（_to_float, _to_int）。

- ニュース収集
  - RSS ニュース収集モジュール（src/kabusys/data/news_collector.py）。
    - RSS 受信・解析、テキスト前処理、URL 正規化、トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - defusedxml を利用して XML ベースの脆弱性（XML Bomb 等）に対処。
    - SSRF メタリスク対策や受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、URL トラッキングパラメータ定義、挿入バルクチャンク処理を実装。
    - raw_news テーブルへ冪等保存（ON CONFLICT DO NOTHING）およびニュースと銘柄の紐付け（news_symbols 前提）。

- Research / ファクター計算
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算（DuckDB SQL ウィンドウ関数使用）。
    - calc_volatility: ATR（20日）, atr_pct（相対ATR）, avg_turnover（20日平均売買代金）, volume_ratio の計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（価格と組み合わせ）。
    - 欠損・データ不足に対する None の扱い、スキャン範囲のバッファ設定等。

  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）IC を計算（サンプル数不足時は None）。
    - rank: 同順位は平均ランクを与える方式（浮動小数丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計要約。

  - research パッケージの __all__ に機能を公開。

- 特徴量エンジニアリング（戦略層）
  - feature_engineering モジュール（src/kabusys/strategy/feature_engineering.py）
    - build_features: research で計算した生ファクターをマージ、ユニバース（最低株価 300 円・20日平均売買代金 5 億円）をフィルタ適用、指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション）して保存。冪等性を確保。

- シグナル生成（戦略層）
  - signal_generator モジュール（src/kabusys/strategy/signal_generator.py）
    - generate_signals:
      - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
      - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）・閾値デフォルト 0.60。
      - ユーザー指定 weights の検証（不正値を無視、合計を 1.0 に再スケール）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制。サンプル不足時は偽と判断）。
      - BUY/SELL シグナル生成ロジック（BUY は threshold 超過、SELL はストップロス -8% および score 低下）、保有銘柄の優先的な SELL 扱い、signals テーブルへ日付単位で置換して保存（トランザクション）。
    - 内部ユーティリティ: _sigmoid, _avg_scores, 各コンポーネントスコア計算関数、_generate_sell_signals（positions / prices の最新行参照で判定）。

- API エクスポート
  - strategy パッケージの __init__ で build_features / generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 外部入力（RSS, XML）のパースに defusedxml を使用し、XML関連攻撃を軽減。
- ニュース収集で URL 正規化・トラッキング除去・スキーム制限などを実施し、SSRF／トラッキング漏洩リスクを軽減。
- J-Quants クライアントは 401 自動トークンリフレッシュの実装と、リトライでの過負荷回避（429のRetry-After尊重）を行う。

### Notes
- DuckDB をデータ層として利用する設計になっており、ほとんどの関数は DuckDB の接続を引数に取り SQL を直接実行します（外部 API への依存を最小化）。
- 一部の設計上の未実装・将来追加予定の機能（ドキュメント中に注記あり）:
  - signal_generator のトレーリングストップ / 時間決済（positions に peak_price / entry_date が必要）。
  - factor_research における PBR・配当利回りなどの追加ファクター。
- 外部依存:
  - duckdb（必須）
  - defusedxml（ニュース RSS の安全なパース用）
  - 標準ライブラリの urllib / datetime / math 等を多用

---

今後のリリースでは、テストカバレッジ、CI/CD の追加、さらに細かい運用向け機能（モニタリング/Slack通知/実行層との連携）を追記予定です。README やドキュメント（StrategyModel.md 等）に記載された仕様とも整合を取りながら改善します。