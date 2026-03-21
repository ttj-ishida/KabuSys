# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
比較的初期のリリース（v0.1.0）として、コア機能の実装にフォーカスした内容をコードベースから推測してまとめています。

現在のバージョンは 0.1.0 です（src/kabusys/__init__.py にて定義）。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-21
初回公開リリース。日本株自動売買システムのコアモジュール群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。主要サブパッケージとして data, strategy, execution, monitoring を __all__ にエクスポート（src/kabusys/__init__.py）。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により、CWD に依存しない自動ロードを実現。
  - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env、.env.local は上書き）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パース処理: コメント、export 文対応、シングル/ダブルクォートとバックスラッシュエスケープの取り扱い、インラインコメントの扱いなどに対応。
  - Settings クラスで各種必須設定値をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値チェック（未設定で ValueError を送出）。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許可）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）を Path 型で提供。
    - ヘルパー: is_live / is_paper / is_dev。

- Data モジュール（src/kabusys/data/*）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しの共通実装（HTTP、JSON デコード）。
    - 固定間隔の簡易レートリミッタ（120 req/min）実装。
    - 再試行（リトライ）ロジック：指数バックオフ、最大試行回数、429/408/5xx のリトライ処理、Retry-After の尊重。
    - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）と再試行の仕組みを実装。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar といったデータ取得関数を実装。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar。いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
    - データ変換ユーティリティ _to_float / _to_int を提供。欠損・不正値を安全に扱う。
    - Look-ahead バイアス対策として fetched_at を UTC で記録。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードから記事を取得して raw_news へ冪等に保存する仕組みを実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - セキュリティ対策: defusedxml による XML パースで XML Bomb 等を防止、HTTP スキーム検証等で SSRF を抑止、受信サイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS を防止。
    - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）とトランザクションまとめ保存、INSERT RETURNING を用いた実挿入件数の把握。
    - デフォルト RSS ソース定義（例: Yahoo Finance ビジネスカテゴリ）。

- Research（研究）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率 (ma200_dev) の計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を算出（EPS 欠損や 0 は考慮）。
    - DuckDB のウィンドウ関数と SQL ベースの実装で、営業日欠損（週末・祝日）を考慮するスキャン範囲を確保。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル不足（<3）の場合は None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
    - rank: 平均ランクを扱う同順位処理を含むランク変換ユーティリティ。
  - research パッケージの __all__ に主要関数をエクスポート。

- Strategy（戦略）モジュール（src/kabusys/strategy/*）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで生成された生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（data.stats.zscore_normalize を利用）して ±3 でクリップ。
    - features テーブルへの日付単位での置換（DELETE + INSERT をトランザクションで実行）による冪等処理。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - Sigmoid 変換、欠損コンポーネントの中立補完（0.5）、重み付き合算による final_score 計算を実装。デフォルト重みを提供し、ユーザー重みは検証・再スケール。
    - Bear レジーム検知（AI の regime_score の平均が負）により BUY を抑制するロジック。
    - BUY シグナル閾値（デフォルト 0.60）、STOP_LOSS（-8%）等のルールを実装。
    - 保有ポジションに対する SELL 判定（stop_loss / score_drop）を実装。価格欠損時は判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位の置換（トランザクション）で冪等に保存。
    - 生成された BUY/SELL の合計数を戻り値として返す。
  - strategy パッケージの __all__ に build_features / generate_signals をエクスポート。

### Security
- 外部データ処理におけるセキュリティ対策を導入:
  - news_collector: defusedxml の採用・受信サイズ制限・URL 正規化で SSRF/DoS/トラッキング対策。
  - jquants_client: HTTP エラー処理・リトライ制御・トークン管理で安全な API 呼び出しを設計。

### Docs / Logging / Observability
- 多数の関数で logger を利用して情報/警告/デバッグを出力。処理結果のサマリや異常時の警告ログを記述。
- 設計方針や処理フローを各モジュールでドキュメント化（モジュール docstring に記載）。

### Notes / Known limitations
- execution と monitoring パッケージの中身はこのリリースでの実装記載がない（プレースホルダ）。
- 一部仕様（例: トレーリングストップ、時間決済、positions テーブルの peak_price/entry_date など）は未実装で、コード内に TODO/未実装としてコメントあり。
- 外部依存（pandas など）を極力排し、標準ライブラリ + duckdb での実装にしているため、研究向けの互換性・性能要件は今後調整の余地あり。

---

今後のリリースに向けて
- execution 層（kabu API への実際の発注/注文管理）と monitoring の実装・統合。
- バックテスト・シミュレーションモジュールの追加。
- エンドツーエンドの統合テスト、エラーハンドリング強化、メトリクス・監視の追加。

（以上）