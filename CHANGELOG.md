# CHANGELOG

すべての注記は Keep a Changelog の形式に従います。  
このファイルはコードベースの内容から推測して作成した変更履歴です（初回リリース想定）。

全般的な説明:
- プロジェクトは日本株の自動売買プラットフォーム（kabusys）用のライブラリで、データ取得・保存、リサーチ用ファクター計算、特徴量生成、シグナル生成、環境設定管理などを含みます。
- DuckDB をデータストアとして用い、J-Quants API や RSS（ニュース）を取り込みます。
- ルックアヘッドバイアス回避、冪等性（idempotency）、エラーハンドリング、セキュリティ対策を設計方針として重視しています。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回公開リリース。主要な機能群を実装。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py にてバージョン管理と公開モジュールを定義（__version__ = 0.1.0、data/strategy/execution/monitoring を公開）。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。プロジェクトルート判定は .git または pyproject.toml を探索する方式で CWD に依存しない実装。
    - 複雑な .env 行（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント）のパースに対応。
    - OS 環境変数を保護する protected 機構と、.env/.env.local の読み込み優先順位（OS > .env.local > .env）を実装。
    - 必須 env を取得する _require と Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / ログレベル / 環境判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（株価日足 / 財務データ / マーケットカレンダーの取得）。
    - 固定間隔のレート制限（120 req/min）を守る RateLimiter 実装。
    - リトライ（指数バックオフ、最大3回）と 401 の自動トークンリフレッシュ対応（リフレッシュは 1 回まで）を実装。
    - ページネーション対応で全ページを取得。
    - DuckDB への保存関数を提供（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE を用いた冪等保存。
    - 取得データのパース補助ユーティリティ（_to_float / _to_int）を実装し、不正な値や PK 欠損行はスキップしてログ出力。
    - fetched_at を UTC ISO8601 形式で記録し、データ取得時刻をトレース可能に。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを取得して raw_news に保存するモジュールを実装。
    - デフォルト RSS ソース（Yahoo finance のビジネスカテゴリ）を定義。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成する方針により冪等性を担保。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid, gclid など）を除去し、クエリをソート、フラグメント削除を行う実装を追加。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES）やバルク INSERT のチャンク処理を導入。
    - defusedxml の利用や URL/スキームの検査等、受信 XML / URL に対する安全対策を設計方針として明記。
- リサーチ（factor 計算・探索）
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value / Liquidity 系のファクター計算を実装（価格日足および raw_financials を参照）。
    - mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算する calc_momentum を実装。ウィンドウ内行数不足時は None を返す。
    - atr_20（20日 ATR）・atr_pct・avg_turnover・volume_ratio を計算する calc_volatility を実装。true_range の NULL 伝播を制御して正確なカウントを行う。
    - raw_financials から最新財務データを結合して per / roe を算出する calc_value を実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト 1/5/21 営業日）の将来リターンを一度の SQL で取得する実装。
    - calc_ic: Spearman ランク相関（IC）の計算実装（同順位は平均ランクで処理、レコード数不足時は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位の平均ランクを与えるランク関数の実装（浮動小数の丸めで ties 検出漏れを防止）。
  - src/kabusys/research/__init__.py で主要関数を公開。
- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールの生ファクターを読み込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、数値ファクターを Z スコア正規化して ±3 でクリップ、features テーブルへ日付単位で置換（トランザクション・バルク挿入）する build_features を実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用する設計。
- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news コンポーネントを計算して最終 final_score を算出する generate_signals を実装。
    - デフォルト重み・閾値（weights / threshold）をサポートし、ユーザ指定 weights は検証・正規化して合計 1.0 に再スケールするロジックを実装。
    - Sigmoid による Z スコア→[0,1] 変換、欠損コンポーネントは中立値 0.5 で補完するポリシーを採用。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）は BUY シグナルを抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8%、final_score が threshold 未満）を実装し SELL シグナル生成。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）する処理を実装。
- パッケージ公開（strategy API）
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- （初版のため設計上の明示）
  - SQL クエリはパフォーマンスを考慮してウィンドウ関数と一回クエリ取得を多用（スキャン範囲をカレンダー日数でバッファして祝日・週末を吸収する戦略を採用）。
  - データ保存時は可能な限り ON CONFLICT / DO UPDATE を利用して冪等性を確保。
  - トランザクション制御（BEGIN / COMMIT / ROLLBACK）を用いて日付単位の置換を原子化。

### Fixed
- データ取り込み周りの堅牢化
  - raw データの PK 欠損行をスキップし、スキップ数をログ出力することで不正データによる例外を防止（jquants_client.save_* 系）。
  - シグナル生成 / エグジット判定で価格欠損時は SELL 判定をスキップし、警告ログを出す処理を追加（誤クローズ防止）。
  - .env パースで複雑なクォート・エスケープ・コメントを正しく扱うことで環境変数の誤読を防止（config._parse_env_line）。

### Security
- news_collector では defusedxml を利用する方針を明記し、受信 URL の正規化・トラッキング除去、受信バイト数上限などを導入して XML Bomb / メモリ DoS / SSRF 等のリスクに配慮。
- J-Quants クライアントは Authorization ヘッダの取り扱いとトークンリフレッシュを安全に行うよう実装（無限再帰を防ぐ allow_refresh フラグ）。

### Known limitations / TODO
- signal_generator のトレーリングストップ / 時間決済条件は positions テーブルに peak_price / entry_date が必要で、現バージョンでは未実装（コメントとして明記）。
- 一部の入力検証やエッジケースはログ出力で対応しているが、将来的により詳細な監視・メトリクス収集が必要。
- news_collector の完全な SSRF/IP 検査や XML パース例外ハンドリングの微調整は今後の改善対象。

---

（注）上記はソースコードの実装内容から推測して作成した CHANGELOG です。実際のコミット履歴や issue と照らし合わせて調整してください。