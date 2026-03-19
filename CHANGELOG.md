CHANGELOG
=========
すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に従います。
ソース管理の履歴ではなく、コードベース（公開 API / 機能）の説明に基づき推測して作成しています。

フォーマット:
- "Added" は新規追加機能
- "Changed" は既存機能の変更
- "Fixed" は不具合修正
- "Security" はセキュリティに関する注意点

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-19
-------------------
初期リリース（推測）。以下の主要機能・モジュールを実装しています。

Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。公開 API として data, strategy, execution, monitoring を __all__ に定義。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）し、カレントディレクトリに依存しない自動 .env 読み込みを提供。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
  - 自動 .env 読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定の取得用 _require と環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - データベースパス（DUCKDB_PATH, SQLITE_PATH）、Slack、J-Quants、kabu API 関連のプロパティを提供。
- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔のレート制限（120 req/min）を守る RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 等の再試行）を実装。
  - 401 受信時のリフレッシュトークンを用いたトークン自動更新（1 回リトライ）を実装。モジュールレベルの ID トークンキャッシュを保持。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT で更新）。
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、入力データの堅牢な取り扱いを提供。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集するモジュールを追加。デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを登録。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）を実装し、記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を利用した XML パースで XML-Bomb 等を防御。受信バイト数上限（MAX_RESPONSE_BYTES）および SSRF 対策（HTTP/HTTPS スキーム等の検証）を実装。
  - バルク INSERT のチャンク処理やトランザクションでの一括保存により DB 書き込みオーバーヘッドを削減。
- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（factor_research）を追加:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0/欠損 の場合は None）。
  - 特徴量探索モジュール（feature_exploration）を追加:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算（LEAD を用いる）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算する実装。
    - factor_summary, rank: ファクターの統計サマリー・ランク計算ユーティリティを提供。
  - research パッケージの __all__ を通じて主要関数をエクスポート。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research モジュールから生ファクターを取得し（calc_momentum / calc_volatility / calc_value）、ユニバースフィルタ（最低株価・最低売買代金）を適用。
    - 数値ファクターを z-score 正規化（外部 zscore_normalize を利用）し ±3 にクリップ。
    - 日付単位で features テーブルへ置換（トランザクション + バルク挿入で原子性）。
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用する設計。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントスコアを計算。
    - コンポーネントはシグモイド変換や逆転（ボラティリティ）等の処理を行い、重み付き合算で final_score を算出（デフォルト重みを提供）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合）により BUY シグナルを抑制。
    - BUY（threshold デフォルト 0.60）および SELL（ストップロス -8% / final_score が閾値未満）を生成。
    - 保有ポジションのエグジット判定を行い、signals テーブルへ日付単位で置換保存（トランザクション）。
    - 重みのユーザ渡しを安全に受け付け、妥当性チェックと正規化を実施。
- パッケージエクスポート
  - kabusys.strategy の __all__ に build_features と generate_signals を公開。

Changed
- （初期リリースのため過去からの変更は無し。設計上の考慮点として以下を明記）
  - 多くの DB 書き込み処理でトランザクション + バルク挿入（executemany）を採用し、冪等性（ON CONFLICT）と原子性を重視した設計になっている。
  - DuckDB を主要な解析ストレージとして想定（価格・財務・features/ai_scores/positions 等のテーブル利用）。

Fixed
- （ソース解析から明示的なバグ修正履歴は推測できないため記載無し）

Security
- ニュース収集で defusedxml を使用、受信サイズ制限、URL 正規化およびスキーム検証による SSRF 対策など、外部データ取り込みの安全性を考慮した実装を行っている。
- J-Quants クライアントは認証トークンの扱い（キャッシュ／自動リフレッシュ）と HTTP エラーの扱いに注意を払っている（429 の Retry-After を尊重する処理を含む）。

Notes / Limitations（設計上の注記）
- signal_generator の一部仕様（トレーリングストップや時間決済等）はコメントで未実装として明示されている（positions テーブルに peak_price / entry_date が必要）。
- calc_forward_returns はホライズンが最大 252 営業日を超えないことを期待している（入力検証あり）。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 外部依存を最小化する方針があり（research.feature_exploration は pandas 等に依存しない実装）、純粋に標準ライブラリ＋duckdb で解析できる設計。

参考（主な公開関数 / モジュール）
- kabusys.config: settings (Settings)
- kabusys.data.jquants_client: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector: RSS 収集 / URL 正規化機能
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize (をエクスポート)
- kabusys.strategy: build_features, generate_signals

今後の改善候補（推測）
- positions テーブルの拡張（peak_price, entry_date 等）によるトレーリングストップ・時間決済ロジックの実装
- モジュール間のユニット・統合テストの整備（外部 API をモックした CI）
- ニュース記事の銘柄紐付け（NER 等）アルゴリズムの追加・精緻化
- 並列・非同期のデータ取得（RateLimiter を活かした並列化戦略）

----

この CHANGELOG はコードの構造・コメント・関数名・実装内容から推測して作成しています。実際のリリースノートとは差異があり得ます。必要であれば、実際のコミットログやリリース履歴に基づいたより正確な CHANGELOG を生成できます。