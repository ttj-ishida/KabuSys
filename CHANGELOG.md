CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。  

0.1.0 - 2026-03-20
------------------

Added
- 初回公開リリース (バージョン 0.1.0)
  - パッケージメタ情報
    - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
    - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。
  - 環境変数 / 設定管理（src/kabusys/config.py）
    - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - .env / .env.local の読み込み優先順位を実装（OS 環境変数を保護する protected 機構、.env.local は override=True）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途などで自動ロードを無効化可能）。
    - .env ファイルのパース機能を強化（"export KEY=val" 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / データベースパス / アプリ環境・ログレベル等のアクセスプロパティを実装。
      - 環境値検証: KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の値チェック。
      - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等にデフォルトを用意。
  - データ取得・保存（src/kabusys/data）
    - J-Quants クライアント（src/kabusys/data/jquants_client.py）
      - API レート制限 (120 req/min) を守る RateLimiter を実装（固定間隔スロットリング）。
      - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の再試行、429 の Retry-After 優先）。
      - 401 Unauthorized 受信時にリフレッシュトークンから id_token を再発行して 1 回だけリトライする自動リフレッシュ処理。
      - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
      - DuckDB へ冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE）を実装。
      - レスポンスの型安全な変換ユーティリティ _to_float / _to_int を提供。
      - 取得時刻の記録（fetched_at を UTC ISO8601 で保存）により look-ahead bias の追跡を可能に。
    - ニュース収集モジュール（src/kabusys/data/news_collector.py）
      - RSS フィードから記事を収集する基盤を実装。デフォルトソースに Yahoo Finance のビジネスカテゴリ RSS を設定。
      - セキュリティ・堅牢性対策: defusedxml による XML パース、受信バイト数上限（MAX_RESPONSE_BYTES）、HTTP スキーム検証等。
      - URL 正規化処理を実装（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
      - バルク挿入向けのチャンク処理や挿入時の冪等性（ID をハッシュ化しての重複排除など想定）を想定した設計。
  - 研究（research）モジュール（src/kabusys/research）
    - ファクター計算群（src/kabusys/research/factor_research.py）
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB の prices_daily から計算。
      - calc_volatility: 20 日 ATR（atr_20）、相対ATR（atr_pct）、20 日平均売買代金（avg_turnover）および出来高比率（volume_ratio）を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを使用）。
      - 各関数は欠損・データ不足時に None を返す設計。スキャン範囲にカレンダーバッファを持たせる実装。
    - 特徴量探索・評価（src/kabusys/research/feature_exploration.py）
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一度に取得。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
      - rank / factor_summary: ランキング（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を提供。ties に対する精度確保のため丸め処理を採用。
    - research パッケージの公開 API を __all__ で提供（calc_momentum 等の関数を容易に import 可能）。
  - 戦略（strategy）モジュール（src/kabusys/strategy）
    - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
      - build_features: research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得、ユニバースフィルタ（最低株価300円、20日平均売買代金 5 億円）を適用、Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップし features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
      - ユニバースフィルタ用に target_date 以前の最新価格を参照し、休場日や当日の欠損に対応。
    - シグナル生成（src/kabusys/strategy/signal_generator.py）
      - generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を算出する実装。
      - デフォルト重みを定義し、ユーザー指定 weights は検証後に既知キーのみでマージ、正規化（合計を 1.0 に再スケール）して適用。
      - Sigmoid 変換・欠損コンポーネントの中立補完（0.5）による堅牢化。
      - Bear レジーム判定（AI の regime_score の平均が負で、かつ十分なサンプル数がある場合）により BUY シグナルを抑制。
      - BUY シグナル閾値デフォルトは 0.60。SELL シグナルは主にストップロス（-8%）およびスコア低下を判定。positions / prices を参照してエグジット判定を行う。
      - SELL の優先度を高くし、SELL 対象銘柄を BUY から除外してランクを再付与するポリシーを実装。
      - signals テーブルへの日付単位置換（トランザクション＋バルク挿入で原子性）を行うため冪等性を確保。
  - その他
    - packages の公開 API を整理（src/kabusys/strategy/__init__.py 等で build_features / generate_signals を再公開）。
    - ロギングと警告メッセージを多用し、欠損や異常時の動作をトレースしやすく設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- ニュース XML のパースに defusedxml を利用し XML 関連の攻撃（XML Bomb 等）に対処。
- news_collector で受信サイズ制限（MAX_RESPONSE_BYTES）を導入しメモリ DoS を軽減。

Notes / 実装上の注意
- 多くの DB 書き込みはトランザクションとバルク挿入で日付単位の置換を行い、冪等性と原子性を重視しています（features / signals / raw_* / market_calendar 等）。
- J-Quants クライアントはトークン自動更新とレート制限・リトライ機構を持ちますが、実行環境側での適切なネットワーク・認証設定（環境変数 JQUANTS_REFRESH_TOKEN 等）は必須です。
- 一部の処理（例: news_collector の ID 生成・news→銘柄紐付け、execution/monitoring パッケージの具象実装）は本バージョンでは最小限の骨格もしくは未実装の可能性があります。今後のリリースで拡張予定です。

今後の予定（想定）
- execution 層（kabu ステーション / 発注ロジック）・monitoring（アラート / Slack 通知）の具体実装。
- ニュースと銘柄の自動マッチングロジック強化、自然言語処理を用いたニューススコアリング。
- テストカバレッジ拡充、長期運用を見据えた監視・メトリクスの追加。