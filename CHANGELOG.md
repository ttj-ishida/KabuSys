# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成しています。

## [0.1.0] - 2026-03-20

### 追加
- パッケージ初期リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョン `0.1.0` を定義し、主要サブパッケージ（data / strategy / execution / monitoring）を公開。

- 環境設定管理（src/kabusys/config.py）:
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env の行パーサを実装（コメント処理、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応、インラインコメント処理）。
  - 環境変数の保護機構（既存 OS 環境変数を protected として上書き防止）。
  - Settings クラスを提供し、必須設定の取得（J-Quants refresh token、Kabu API パスワード、Slack トークン／チャンネル等）や値検証（KABUSYS_ENV / LOG_LEVEL のバリデーション）、パス（DuckDB / SQLite）を Path 型で提供するユーティリティを追加。

- データ取得・保存 (J-Quants クライアント)（src/kabusys/data/jquants_client.py）:
  - J-Quants API クライアントを実装。
  - レート制限を尊重する固定間隔スロットリング（120 req/min）を実装（内部 RateLimiter）。
  - リトライ機構（指数バックオフ、最大 3 回）を導入。408/429/5xx をリトライ対象に含め、429 の場合は Retry-After ヘッダを優先。
  - 401 エラー発生時は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止フラグあり）。
  - ページネーション対応の取得関数を実装: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存関数を追加: save_daily_quotes / save_financial_statements / save_market_calendar。いずれも ON CONFLICT DO UPDATE を用いて重複更新を回避。
  - レスポンス JSON デコードや型変換のための安全なユーティリティ関数（_to_float / _to_int）を提供。

- ニュース取得（src/kabusys/data/news_collector.py）:
  - RSS フィードから記事を収集して raw_news へ保存するロジックを実装（デフォルト RSS ソースに Yahoo Finance を含む）。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュの先頭を使う設計（冪等性確保）。
  - XML 処理に defusedxml を使用して XML Bomb 等の攻撃を緩和。
  - SSRF 対策、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）等のセーフガードを設計に明記。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）により DB への一括保存の効率化を図る。

- リサーチ・ファクター計算（src/kabusys/research/）:
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M 等のモメンタム、200 日移動平均乖離率を計算（窓不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算（窓不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新報告値を銘柄ごとに選択）。
    - DuckDB のウィンドウ関数を活用した効率的 SQL 実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一回のクエリで取得。horizons のバリデーション（正の整数かつ <=252）。
    - calc_ic: スピアマン（順位）相関を実装。ties は平均ランクで扱う。有効サンプルが 3 未満なら None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクにするランク関数を実装（丸め誤差対策に round を使用）。
  - research パッケージ経由で主要関数をエクスポート。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）:
  - research の生ファクターを結合し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 指定カラムを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
  - features テーブルへ日付単位で置換（DELETE + INSERT のトランザクション処理）し冪等性を保証。
  - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）:
  - features と ai_scores を統合して final_score を計算。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出するユーティリティを実装（シグモイド変換、平均化、欠損値補完ルール）。
  - デフォルト重みとしきい値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD=0.60）を実装。ユーザー指定の weights を検証し正規化（合計 1 に再スケール）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）、Bear 時は BUY を抑制。
  - エグジット条件（ストップロス: -8% 以下 / スコア低下）を実装。SELL が BUY より優先されるポリシー。
  - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）して冪等性を保証。

- パッケージ API 整備:
  - strategy パッケージで build_features / generate_signals を公開する __all__ を定義。
  - research パッケージから主要ユーティリティを再エクスポート。

### セキュリティ
- ニュース収集で defusedxml を使用して XML 関連の攻撃を軽減。
- ニュース URL 正規化でトラッキングパラメータ削除とスキームチェックを想定し、SSRF 等のリスク低減を検討。
- API クライアントでタイムアウトとリトライ制御、トークンの自動リフレッシュを実装し、認証エラーでの不整合を最小化。

### パフォーマンス・信頼性
- DuckDB のウィンドウ関数 / 単一クエリ取得（calc_forward_returns 等）により I/O を削減。
- J-Quants クライアントに固定間隔レートリミッターを導入し API レート制限に適合。
- save_* 関数で ON CONFLICT DO UPDATE を利用し、データ取り込みの冪等性と再実行耐性を確保。
- トランザクション（BEGIN/COMMIT/ROLLBACK）により features / signals テーブルへの置換処理で原子性を担保。

### 既知の制限 / 未実装事項
- execution パッケージは空の __init__ のみ（発注実装は未提供）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済等）は positions テーブルに追加情報（peak_price / entry_date）が必要で未実装。
- news_collector の一部設計（INSERT RETURNING による実挿入数取得等）は設計に言及されているが、実装詳細はコード状況に依存。
- 一部の入力検証や外部例外処理の追加強化は今後の改善候補（より詳細なエラー分類・監視の追加など）。

### 破壊的変更
- なし（初期リリースのため該当なし）。

---

今後のリリースでは、execution 層（実際の注文送信・注文管理）、monitoring（運用監視・メトリクス送信）、および追加のエグジット戦略やニュース→銘柄マッチング精度向上などが想定されます。