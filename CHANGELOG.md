CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 初回公開リリース。
- パッケージ構成（kabusys）を追加。
  - モジュール公開: data, strategy, execution, monitoring をパッケージ公開対象に設定。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
- 環境設定・読み込み機能（kabusys.config）を追加。
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パースの堅牢化: export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ処理、インラインコメント処理（クォート有無を考慮）。
  - 環境変数取得ヘルパー _require と Settings クラスを提供（各種必須設定、デフォルト値、値のバリデーションを含む）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、is_live/is_paper/is_dev のユーティリティプロパティ。
- データ取得・保存（kabusys.data.jquants_client）を追加。
  - J-Quants API クライアント: ページネーション対応、レート制限（120 req/min）の固定間隔スロットリングを実装（_RateLimiter）。
  - リトライ機構（指数バックオフ、最大3回）と 408/429/5xx に対する再試行ロジック。
  - 401 応答時の ID トークン自動リフレッシュ（一度のみリフレッシュして再試行）とモジュールレベルのトークンキャッシュ（ページネーションで共有）。
  - 429 の場合は Retry-After ヘッダを優先して待機。
  - fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を提供。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT を使った冪等保存を実装。
  - 数値変換ユーティリティ (_to_float / _to_int) を実装し、不正値を安全に扱う。
- ニュース収集（kabusys.data.news_collector）を追加。
  - RSS フィード取得・記事抽出・前処理・冪等保存ワークフローを実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト小文字化）を実装。
  - defusedxml を利用して XML 関連攻撃（XML Bomb 等）を軽減。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、チャンク化してのバルク INSERT、INSERT RETURNING を考慮した実装方針。
  - デフォルト RSS ソースの定義（Yahoo Finance Business）。
- リサーチ用ユーティリティ（kabusys.research）を追加。
  - ファクター計算ファミリ（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（必要行数不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比率。
    - calc_value: EPS からの PER、ROE 取得（raw_financials と prices_daily を結合）。
    - DuckDB を使った SQL ベースの高性能実装。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得。horizons の入力検証（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（IC）計算。タイの扱い（平均ランク）を含む rank ユーティリティ。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - zscore_normalize 等、研究側で使うユーティリティを再エクスポート（kabusys.research.__init__）。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）を追加。
  - research 側で計算した生ファクターを統合・正規化し features テーブルへ UPSERT（日単位で置換・冪等）する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）を実装。
  - Z スコア正規化（指定カラム）と ±3 クリップ、欠損ハンドリングを実装。
  - DuckDB トランザクションにより日付単位の原子置換を実現。
- シグナル生成（kabusys.strategy.signal_generator）を追加。
  - features と ai_scores を統合し final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ日付単位の置換で保存する generate_signals を実装。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）の定義と sigmoid/平均による正規化。
  - デフォルト重みを定義し、ユーザ指定 weights を検証・補完・正規化して適用。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
  - SELL 判定ロジック（ストップロス -8% / スコア低下）を実装。価格欠損時は判定をスキップしてログ出力。
  - 保有ポジション（positions）を参照して SELL を優先し、BUY ランクを再付与。
  - トランザクション + バルク挿入で signals テーブルを日付単位で置換（冪等）。
- パッケージ内エクスポートを整備（kabusys.strategy.__init__ / kabusys.research.__init__）。

Fixed / Improved
- 環境変数パーサーの堅牢化（クォート中のエスケープ、コメント処理、export 対応）により .env の実用性を向上。
- J-Quants クライアント:
  - トークンリフレッシュ時の無限再帰を防止（allow_refresh フラグ）。
  - 429 レスポンスへの待機（Retry-After ヘッダ優先）を実装。
  - ページネーション間でトークンを共有することで余分な認証呼び出しを削減。
- DuckDB 保存処理:
  - PK 欠損レコードをスキップして警告ログを出力。
  - ON CONFLICT による冪等性を実装し、既存データ更新を安全に処理。
- news_collector:
  - defusedxml による XML パース安全化、受信サイズ制限、トラッキングパラメータ除去による記事ID一意化を実装。
- research モジュールの計算ロジック（rank, calc_ic, factor_summary など）を小数誤差や ties を考慮して安定化。

Security
- news_collector で defusedxml を利用して XML 関連攻撃を軽減。
- RSS ニュースの URL 正規化・トラッキング除去・スキームチェック等により SSRF・トラッキングのリスクを低減する設計方針を採用。
- J-Quants API 呼び出しでのタイムアウト・リトライ制御・トークン管理により想定外の失敗時の影響を抑制。

Notes / Limitations
- 一部機能は将来的な拡張予定（ソース内に TODO 記載）:
  - signal_generator のトレーリングストップ／時間決済（positions テーブルに peak_price / entry_date 等の追加が必要）。
  - news_collector の完全な SSRF 対策（IP/ホスト検証等の追加実装）。
- 本リリースは主にデータ取得・加工・シグナル生成パイプラインのコア実装に注力しており、実際の発注（execution 層）や運用監視（monitoring）は別モジュールとして分離済みだが、本コードベース内の execution/monitoring ディレクトリは初期骨格または未実装の可能性があります。

付記
- この CHANGELOG はソースコード内の docstring / コメント及び実装から推測して作成しています。実運用時は README やドキュメントと合わせて内容を確認してください。