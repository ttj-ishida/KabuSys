CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-20
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"、公開モジュール一覧を定義。

- 環境設定/読み込み機能 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索して特定）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - export KEY=val 形式、シングル/ダブルクォート、インラインコメント（スペース前の '# '）などに対応したパーサを実装。
  - override/protected 機能により OS 環境を上書きから保護。
  - Settings クラスを導入し、J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、データベースパス（DuckDB/SQLite）、環境（development/paper_trading/live）およびログレベルの検証を提供。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限 120 req/min を固定間隔スロットリングで遵守する RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）と特定ステータス（408/429/5xx）でのリトライ処理を実装。
  - 401 受信時はトークン自動リフレッシュ（1 回のみ）して再試行する仕組みを実装。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（日足 OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - fetched_at を UTC ISO フォーマットで記録。型安全な数値変換ユーティリティ (_to_float / _to_int) を提供。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して raw_news に保存する収集器を実装。
  - デフォルトソースに Yahoo Finance のカテゴリ RSS を含む。
  - セキュリティ対策:
    - defusedxml を利用して XML 攻撃を緩和。
    - 受信サイズ上限（10MB）を設定してメモリ DoS を軽減。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で作成し冪等性を担保。
    - SSRF 緩和のため非 http/https スキームは拒否する方針。
  - バルク INSERT をチャンク化して保存（ON CONFLICT DO NOTHING で重複回避）。

- 研究用モジュール (src/kabusys/research/*)
  - factor_research:
    - calc_momentum（1/3/6 ヶ月リターン、200 日 MA 乖離）
    - calc_volatility（20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率）
    - calc_value（PER, ROE を raw_financials と prices_daily から計算）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）
    - calc_ic（スピアマンランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median の統計要約）
    - rank（同順位は平均ランクとするランク付けユーティリティ）
  - 研究モジュールは外部ライブラリ（pandas 等）に依存しない純粋 Python + DuckDB 実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research の生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
  - 処理内容:
    - calc_momentum / calc_volatility / calc_value を呼び出して生ファクター取得
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ
    - 日付単位で置換（DELETE + BULK INSERT をトランザクション内で実行）して冪等性を保証

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を計算し signals テーブルへ書き込む generate_signals を実装。
  - 実装ポイント:
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を算出。シグモイド変換で 0..1 にマッピング。
    - 欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みを定義（momentum 0.40 など）、ユーザ提供 weights を検証・補完・正規化して利用。
    - BUY 閾値デフォルト 0.60。Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル >= 3）で BUY を抑制。
    - SELL 判定:
      - ストップロス: 終値 / avg_price - 1 <= -0.08（-8%）
      - final_score が閾値未満
      - （未実装だが設計にトレーリングストップ / 時間決済の記載あり）
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与。
    - 日付単位の置換をトランザクションで実行して冪等性を担保。
  - signals, features, ai_scores, positions, prices_daily 等の DuckDB テーブルと連携する設計。

- その他
  - strategy パッケージのエクスポート関数 (build_features, generate_signals) を __init__ で公開。
  - research パッケージの主要ユーティリティを __init__ で公開。
  - execution と monitoring の空のモジュールを追加（今後の拡張用プレースホルダ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーシングに defusedxml を使用、RSS の受信サイズ制限、URL 正規化/トラッキング除去、HTTP スキーム検査などの対策を実装。
- J-Quants クライアントでのトークン自動リフレッシュ制御とリトライポリシーにより、誤ったトークン処理や過剰リトライのリスクを低減。

Known limitations / Notes
- 一部のエグジット条件（トレーリングストップ / 時間決済）は positions テーブルに追加情報（peak_price / entry_date 等）が必要で未実装。
- 各機能は DuckDB の所定テーブル構造（raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）を前提としている。スキーマ整備が必要。
- network/HTTP のタイムアウトや例外は基本的な扱いを実装しているが、運用環境での追加監視・エラーハンドリングを推奨。
- news_collector の記事→銘柄紐付け（news_symbols への保存等）は実装方針に言及あり。実運用でのシンボル抽出ロジックの追加が必要。

Acknowledgements
- 初期設計は StrategyModel.md / DataPlatform.md 等のドキュメント設計に基づく実装方針を反映しています。