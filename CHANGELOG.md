Keep a Changelog
すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]

[0.1.0] - 2026-03-21
----------------------------------------
Added
- 基本パッケージ構成を追加（kabusys v0.1.0）。
  - パッケージ公開バージョン: src/kabusys/__init__.py にて __version__="0.1.0" を定義。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 行パーサーの強化:
    - export KEY=val 形式対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを考慮。
  - 上書き制御（override）と OS 環境変数の保護（protected set）をサポート。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティ（必須チェック・デフォルト値・妥当性検証）を実装。
    - 未設定の必須環境変数は _require() により ValueError を送出。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実施。
    - duckdb/sqlite ファイルパスは Path 型で取得し expanduser を適用。

- データ取得・保存（J-Quants クライアント）モジュール（src/kabusys/data/jquants_client.py）
  - J-Quants API との通信ユーティリティを実装（ページネーション対応）。
  - レート制限制御（固定間隔スロットリングで 120 req/min を遵守する _RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx を対象）。
  - 401 発生時は ID トークンの自動リフレッシュを 1 回試行するロジックを実装（get_id_token 連携）。
  - モジュールレベルでの ID トークンキャッシュを実装（ページネーション間で共有）。
  - fetch_* 系関数:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装（pagination_key を扱う）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT で更新を行い重複を排除。
  - 入力値変換ユーティリティ _to_float / _to_int を実装（安全な変換ルールを保持）。
  - 取得時に fetched_at を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS 取得と raw_news テーブルへの冪等保存（ON CONFLICT DO NOTHING）処理を実装。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を保証する方針を導入。
  - セキュリティ対策:
    - defusedxml を利用して XML の脆弱性（XML bomb 等）を回避。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入してメモリ DoS を防止。
    - SSRF 対策（HTTP/HTTPS のみ許可、IP 解決等のチェックを想定する設計説明）。
  - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）により DB 側のパラメータ上限を回避。

- 研究用ファクター計算・探索モジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を用いて、モメンタム（1/3/6ヶ月等）、MA200 乖離、ATR、avg_turnover、volume_ratio、PER/ROE 等を計算。
    - 過去データ不足時の None ハンドリングを設計上明示。
  - feature_exploration.py:
    - calc_forward_returns（指定ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量集計）、rank（同順位は平均ランクで処理）を実装。
    - calc_forward_returns ではパフォーマンスのためにスキャン範囲にバッファをかける実装。
  - research パッケージの __init__ で主要関数を再エクスポート。

- 戦略モジュール（src/kabusys/strategy/*）
  - feature_engineering.py:
    - 研究環境で計算した生ファクターを取り込み、ユニバースフィルタ（最小株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - 数値ファクターの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリップを実装。
    - features テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
  - signal_generator.py:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算、重み付けで final_score を算出（デフォルト重みを実装）。
    - Sigmoid 変換、欠損コンポーネントは中立値 0.5 で補完するロジックを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値により判定）および Bear 時の BUY 抑制。
    - BUY 判定（閾値デフォルト 0.60）と SELL 判定（ストップロス -8% など）を実装。
    - 保有ポジションのエグジット判定は positions テーブルと最新価格を参照。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
  - strategy パッケージの __init__ で build_features / generate_signals を公開。

Changed
- なし（初回リリースのため履歴は追加のみ）。

Fixed
- なし（初回リリース）。

Security
- ニュース XML パースに defusedxml を採用して XML ベースの攻撃を軽減。
- RSS ダウンロード時の受信サイズ制限や URL 正規化により潜在的な SSRF / トラッキング問題に配慮。

Notes / Known issues
- signal_generator のエグジット条件の一部（トレーリングストップ、60営業日超の時間決済）は未実装。positions テーブルに peak_price / entry_date 等の情報が必要。
- news_collector の SSRF/IP 検査は設計として言及済みだが、実装詳細（IP 制限の実行ロジックなど）は今後の強化対象。
- duckdb のスキーマ（raw_prices/raw_financials/features/signals/ai_scores/positions 等）は本 CHANGELOG に含めていません。実行には想定されるスキーマが必要です。
- J-Quants クライアントはネットワーク/HTTP エラーの際に最大再試行を行うが、長時間の接続不良時の振る舞いは運用での監視が必要。

開発者向けメモ
- 自動 .env ロードはパッケージ読み込み時に行われます。テストや特殊環境で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings の各プロパティは実行時に環境変数を参照するため、ユニットテストで値を差し替える際は os.environ を操作するか Settings をモックしてください。

----------------------------------------
タグ:
- [0.1.0]: 初回公開（機能追加多数、研究・データ取得・戦略生成の基盤実装）

 (この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する際は、スキーマ情報や運用手順、外部依存（API トークン等）について追記してください。)