# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期バージョン 0.1.0 のリリースノートを記載します（コードベースから推測して作成）。

## [0.1.0] - 2026-03-19

### Added
- パッケージの初期実装（kabusys 0.1.0）。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local ファイルおよびOS環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサの実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応）。
  - 必須設定取得ヘルパー _require と Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル検証、is_live/is_paper/is_dev プロパティ）。

- データ収集クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限 (_RateLimiter) による固定間隔スロットリング（デフォルト 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - 取得時の fetched_at は UTC で記録（Look-ahead バイアス対策）。
  - HTTP/JSON ハンドリングとエラーメッセージの整備。
  - 型変換ユーティリティ _to_float / _to_int（安全な変換）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集・正規化・DB 保存処理。
  - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を保証。
  - defusedxml による安全な XML パース。
  - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ除去（utm_*, fbclid, gclid 等）、フラグメント削除、クエリソート。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）によるメモリ保護。
  - SSRF 対策や不正スキーム拒否等を想定した実装設計。
  - バルク INSERT のチャンク処理による性能・SQL 長制御。
  - デフォルト RSS ソース定義（例: Yahoo Finance ビジネス RSS）。

- 研究・ファクター計算モジュール（src/kabusys/research/）
  - factor_research:
    - calc_momentum: 1/3/6 ヶ月リターン、200 日移動平均乖離率（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対ATR(atr_pct)、20 日平均売買代金、出来高比率。
    - calc_value: 最新の財務データ（raw_financials）と価格を組み合わせて PER / ROE を計算。
    - 時系列ウィンドウやスキャン範囲にバッファを持たせる実装（週末・祝日対応）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
    - calc_ic: Spearman のランク相関（IC）計算。サンプル不足（<3）や ties 処理を考慮。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank ユーティリティ: 同順位（ties）は平均ランク、丸めによる ties 検出漏れ防止のため小数丸めを実施。
  - research パッケージのエクスポートを整備。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research で算出した生ファクターを統合して features テーブルに保存する処理を実装。
  - ユニバースフィルタ実装（最低株価 300 円、20 日平均売買代金 >= 5 億円）。
  - 正規化: 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - 日付単位での置換（DELETE + bulk INSERT）により冪等性とトランザクション原子性を保証。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を計算し、signals テーブルへ書き込む処理を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）それぞれの計算実装。
  - シグモイド変換、欠損値は中立値 0.5 で補完。
  - 重み（デフォルト）を受け取り合計が 1.0 でなければ正規化。無効なユーザー指定重みはスキップ。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）で BUY を抑制。
  - BUY 生成閾値デフォルト 0.60。BUY/SELL の日付単位置換（冪等）を実施。
  - エグジット(Sell) 判定実装:
    - ストップロス: 損益率 <= -8%（最優先）
    - スコア低下: final_score < threshold
    - 保有ポジションの価格欠損時は判定スキップして誤クローズを防止
    - features に存在しない保有銘柄は final_score=0.0 として SELL 判定（警告ログ）
  - SELL 優先で BUY リストから除外し再ランク付け。

- トランザクションとロギング
  - 重要な DB 書き込みで BEGIN/COMMIT/ROLLBACK を利用し原子性を保証。
  - 各処理で警告・情報ログを適切に出力するよう実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- ニュース収集で defusedxml を使用し XML BOM/XXE 攻撃などを軽減。
- ニュース収集で受信バイト数制限（10MB）を設け、メモリ DoS を軽減。
- ニュース URL 正規化でトラッキングパラメータを除去し、ID を安定化（冪等性向上）。
- J-Quants クライアントのネットワークエラーや HTTP エラーに対して再試行・ログを実装。

### Notes / Known limitations
- generate_signals の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price / entry_date 等が必要（ソース内に注記あり）。
- 一部ユーティリティ（zscore_normalize）は別モジュール（kabusys.data.stats）に依存している（本リリースでは参照のみ）。
- execution 層 / monitoring パッケージは存在するが実装ファイルがほぼ空、またはエントリポイントのみ（今後の実装対象）。
- NewsCollector の具体的な RSS パース/紐付け処理や記事→銘柄マッピングの詳細は設計指針に従って実装されているが、外部環境やフィード差異に依存する。

---

この CHANGELOG はコード内容から推測して作成した初期リリースの要約です。詳細なユーザー向け変更点や API ドキュメントは、別途 README / ドキュメントにて提供してください。