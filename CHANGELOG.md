# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-03-20

初回リリース。本リポジトリは日本株向けの自動売買支援ライブラリ群（データ取得、研究用ファクター計算、特徴量整備、シグナル生成、設定管理など）を提供します。主な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - 外部から利用可能なサブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準とするため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途等）。
  - .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメント処理、クォート無しでのコメント検出などを考慮。
  - 環境変数取得ヘルパと型/値検証:
    - 必須キー取得時に未設定なら ValueError を送出する _require。
    - settings オブジェクトにより JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パス等をプロパティで取得可能。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の値検証を実装。

- Data 層 (src/kabusys/data)
  - J-Quants API クライアント (jquants_client.py)
    - レート制限実装: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）。
    - リトライ戦略: 指数バックオフ（最大 3 回）、408/429/5xx をリトライ対象。429 時は Retry-After を尊重。
    - 401 発生時はリフレッシュトークンから id_token を自動更新して1回だけ再試行（無限再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - ON CONFLICT DO UPDATE を用いて重複を排除。
      - fetched_at を UTC で記録（look-ahead bias のトレース用）。
    - ユーティリティ _to_float / _to_int により安全に型変換。
  - ニュース収集モジュール (news_collector.py)
    - RSS 取得 → 前処理 → raw_news へ冪等保存のフローを提供。
    - デフォルト RSS ソースに Yahoo Finance（ビジネスカテゴリ）を設定。
    - セキュリティ対策:
      - defusedxml を使用した XML パース（XML Bomb 対策）。
      - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) によるメモリ DoS 対策。
      - URL 正規化（スキーム/ホスト小文字化、tracking パラメータ除去、フラグメント削除、クエリソート）。
      - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）で SQL 長・パラメータ数制限を回避。

- 研究（research）モジュール (src/kabusys/research)
  - ファクター計算群 (factor_research.py)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日移動平均乖離 ma200_dev）。
    - ボラティリティ/流動性: calc_volatility（20日 ATR, atr_pct, avg_turnover, volume_ratio）。
    - バリュー: calc_value（最新の raw_financials を用いて per, roeを計算）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルを参照し、(date, code) キーの dict リストを返す設計。
  - 特徴量探索ユーティリティ (feature_exploration.py)
    - calc_forward_returns: 指定日に対する複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（情報係数）を計算、サンプル不足時は None を返す。
    - rank / factor_summary: 平均・分散・中央値などの統計サマリ機能。
    - pandas 等に依存しない純 Python 実装。

- 戦略（strategy）モジュール (src/kabusys/strategy)
  - 特徴量整備 (feature_engineering.py)
    - research モジュールから得た生ファクターをマージし、ユニバースフィルタと Z スコア正規化を適用して features テーブルに UPSERT（冪等）する処理を提供。
    - ユニバースフィルタ基準:
      - 最低株価: 300 円（_MIN_PRICE）
      - 20 日平均売買代金 >= 5 億円（_MIN_TURNOVER）
    - Z スコア正規化対象カラムを指定し、±3 でクリップ（外れ値抑制）。
    - 日付単位の置換（DELETE→INSERT をトランザクション内で実施）により原子性を確保。
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ書き込む。
    - デフォルト重みと閾値:
      - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - デフォルト BUY 閾値: 0.60
      - ストップロス閾値: -8%（終値/avg_price - 1 < -0.08 で即時 SELL）
    - Bear レジーム判定:
      - ai_scores の regime_score 平均が負であれば Bear（ただしサンプル数が最低 3 件以上で判定）。
      - Bear 時は BUY シグナルを抑制。
    - 欠損値ハンドリング:
      - コンポーネントスコアが None の場合は中立 0.5 で補完。
      - features に存在しない保有銘柄は final_score=0 と見なして SELL 判定の対象とする。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、残った BUY に対してランクを再付与。
    - 日付単位の置換（DELETE→INSERT をトランザクション内で実施）により原子性を確保。
  - strategy パッケージは build_features と generate_signals を公開 API としてエクスポート。

### 変更 (Changed)

- ―（初回リリースのため履歴はなし）

### 修正 (Fixed)

- ―（初回リリースのため履歴はなし）

### セキュリティ (Security)

- ニュース処理で defusedxml を使用し XML に関する脆弱性（例: XML bomb）を回避。
- ニュースダウンロードで受信バイト数上限（10MB）を設定しメモリ DoS を抑制。
- J-Quants クライアントで HTTP エラー/ネットワークエラーの安全なリトライとトークンリフレッシュ（401 ハンドリング）を実装。
- URL 正規化とトラッキングパラメータ除去、RSS ソースの URL 検証などにより SSRF/トラッキングリスクを軽減（news_collector の設計方針に基づく処理を実装）。

### 既知の制限 / TODO

- signal_generator のエグジット条件に関して、コメント中で以下が未実装であることを明示:
  - トレーリングストップ（peak_price が必要）
  - 時間決済（保有 60 営業日超過）
- news_collector 内の一部詳細（例: SSRF 関連の厳密な IP フィルタ）や記事→銘柄紐付けロジックの完全実装は今後の改善対象。
- execution（発注）パッケージは本リリースでは空のエントリ（プレースホルダ）となっているため、実際の発注処理は未提供。

### 開発者向けメモ

- settings の必須環境変数例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB に依存する多数の処理は prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルスキーマを前提としている。データ投入前にスキーマ定義が必要。
- research モジュールの関数群は pandas に依存しない純 Python + DuckDB 実装を意図しているため、軽量に運用可能。

Contributors: 初期実装チーム（コードベース内のドキュメントコメントに基づく設計者・実装者）

--- 

今後のリリースでは execution 層の実装、ニュース → 銘柄紐付けの改善、追加の安全性強化やパフォーマンスチューニング等を予定しています。必要があれば別途リリースノートを追加してください。