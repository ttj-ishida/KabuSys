CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。
タグ付けやリリース日はソース内の __version__ と本ファイル作成日（2026-03-20）に基づきます。

[Unreleased]
-------------

（なし）

0.1.0 - 2026-03-20
-----------------

Added
- 基本パッケージ初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ公開情報
  - src/kabusys/__init__.py に __version__="0.1.0" と __all__ のエクスポートを追加。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ: コメント行 / export プレフィックス / シングル・ダブルクォート対応、エスケープ処理、インラインコメントの扱いなどを考慮した堅牢なパース実装。
  - protected オプションを用いた .env 上書き制御。
  - 必須項目取得用の _require ユーティリティと、env/log レベル値の検証（有効値チェック）。
  - Settings が提供する主なキー: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。

- データ取得クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）とリトライ対象ステータス（408, 429, 5xx）を実装。
  - 401 受信時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライする仕組み。
  - ページネーション間で共有されるモジュールレベルの ID トークンキャッシュを実装。
  - データ保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）
    - DuckDB へ冪等（ON CONFLICT DO UPDATE / DO NOTHING）での保存。
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡）。
    - PK 欠損行のスキップとログ出力。
  - 汎用変換ユーティリティ _to_float / _to_int（変換規則を厳格に扱う）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news へ保存するモジュールを追加。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - defusedxml を使った安全な XML パース（XML Bomb 等への対策）。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント除去、クエリキーソート。
  - SSRF 防止のためスキーム制限（http/https）や受信先 IP 検査を考慮（実装方針）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策。
  - DB へのバルク挿入はチャンク処理（_INSERT_CHUNK_SIZE）と単一トランザクションで効率化。
  - Insert returning による実挿入件数の正確な取得（設計方針として明示）。

- リサーチ / ファクター計算（src/kabusys/research/factor_research.py）
  - モメンタム（calc_momentum）: 1m/3m/6m リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す設計。
  - ボラティリティ / 流動性（calc_volatility）: 20 日 ATR、相対ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御により集計精度を確保。
  - バリュー（calc_value）: raw_financials から最新財務を取得し PER / ROE を計算（EPS 欠損や 0 の扱いに注意）。
  - スキャン範囲や窓幅はカレンダー日バッファを考慮して効率化。

- 研究補助機能（src/kabusys/research/feature_exploration.py）
  - 将来リターン計算（calc_forward_returns）: 指定 horizon（営業日）に対するリターンを一度のクエリで取得。horizons の検証（1〜252）を実施。
  - IC（Information Coefficient）計算（calc_ic）: factor_records と forward_records を code で結合し、Spearman の ρ を計算。tie（同順位）は平均ランクで扱う。
  - rank 関数: 丸め（round(..., 12)）による ties 検出耐性を備えた平均ランク付け。
  - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを統合・正規化して features テーブルへ UPSERT（日付単位の置換）する build_features を追加。
  - ユニバースフィルタ実装: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
  - DuckDB トランザクションを用いた日付単位の原子的な置換処理。
  - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用する設計方針。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を算出する generate_signals を実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）計算ロジック（シグモイド変換、逆スコア等）。
  - 欠損コンポーネントは中立値 0.5 で補完する方針。
  - デフォルト重みとしきい値を定義（デフォルト閾値 = 0.60）。weights 引数でカスタム可。入力検証・スケーリングを実装。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル閾値を満たす場合）により BUY シグナルを抑制。
  - SELL（エグジット）判定: ストップロス（終値/avg_price -1 < -8%）とスコア低下（final_score < threshold）を実装。トレーリングストップや長期時間決済は未実装で注記あり。
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
  - SELL 優先ポリシー（SELL 対象は BUY から除外し rank を再付与）。

- パッケージエントリ（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）
  - 主要 API のエクスポートを整理（build_features / generate_signals / calc_* / zscore_normalize / calc_ic 等）。

Design / Notes
- ルックアヘッドバイアス防止: research/strategy 層は target_date 時点のデータのみを用いる設計を徹底。
- DB 操作は可能な限りトランザクションとバルク挿入で原子性・パフォーマンスを確保。
- 外部依存は最小化（research の集計は標準ライブラリ + DuckDB で完結）。
- セキュリティ配慮: defusedxml, SSRF/サイズ制限、.env パースの堅牢化などを実装。

Known limitations / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、60営業日超の時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector のネットワーク周り・IP フィルタの具体的実装は設計方針として明記されているが、導入環境に合わせた追加検証が必要。
- データ単位のテスト・エンドツーエンドテストは別途追加推奨。

ライセンス・貢献
- 本リリースは初期実装のため、追加のテスト、ドキュメント、安定化が必要です。貢献歓迎。