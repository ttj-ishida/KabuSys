# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加 (Added)
- 基本パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開API: data, strategy, execution, monitoring（execution は空のパッケージ、monitoring は参照のみ）

- 環境設定モジュール（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）
  - .env / .env.local の読み込み順序を実装（OS 環境変数を保護する仕組み有）
  - 行パースの詳細実装: export 形式、クォート内エスケープ、インラインコメントの扱いなどに対応
  - 必須環境変数取得のユーティリティ _require と Settings クラスを提供
  - 標準的な設定項目をプロパティとして提供（J-Quants, kabuAPI, Slack, DB パス, 環境判定, ログレベル等）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

- データ収集 / 保存（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
    - RateLimiter による固定間隔スロットリング（120 req/min）を実装
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx の再試行）
    - 401 受信時に自動でトークンリフレッシュして1回リトライ
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）
      - ON CONFLICT / DO UPDATE による重複排除
      - fetched_at を UTC で記録（look-ahead バイアス追跡）
      - 入力データの型変換ユーティリティ (_to_float, _to_int)
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードから記事を収集し raw_news に冪等保存する処理
    - URL 正規化（トラッキングパラメータ削除、クエリソート、スキーム/ホスト小文字化、フラグメント削除）
    - defusedxml を用いた XML パース（XML Bomb 等から保護）
    - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 防止観点の設計が組み込まれている
    - バルク INSERT のチャンク化等でパフォーマンスを配慮

- リサーチ用ファクター計算（src/kabusys/research/）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: 財務データ（EPS/ROE）を用いた PER/ROE の算出（raw_financials と prices_daily を参照）
    - 各関数は DuckDB 接続を受け取り、SQL + Python で完結する実装
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズンにおける将来リターン（デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）計算（同順位は平均ランクで処理）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
    - rank: タイ（同順位）を平均ランクで扱うランク変換ユーティリティ
  - research パッケージの __all__ に上記ユーティリティを公開

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research 側で算出した raw ファクターをマージし、ユニバースフィルタ（最低株価/最低平均売買代金）を適用
  - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）して ±3 でクリップ
  - features テーブルへ日付単位で置換（削除→挿入、トランザクションで原子性を確保）
  - 複数データソース（mom/vol/val）をマージして処理

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して最終スコア final_score を計算
  - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）を算出するユーティリティを実装
  - default weights と閾値（デフォルト threshold=0.60）を実装
  - Bear レジーム判定（ai_scores の regime_score の平均が負の場合を Bear と判定、サンプル数閾値あり）
  - BUY: final_score が閾値を超える銘柄をランク付け（Bear レジームでは BUY を抑制）
  - SELL: 保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）
    - 未実装のエグジット条件はコード内コメントで明示（トレーリングストップ、時間決済）
  - signals テーブルへ日付単位で置換（トランザクションで原子性）
  - weights のユーザー指定は検証・正規化され、合計が 1 になるよう再スケールされる

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### 既知の制限 / TODO
- execution パッケージは存在するが実装が含まれていない（発注ロジックは未実装）
- signals のエグジット条件の一部（トレーリングストップ、時間決済）は未実装で、positions テーブルに追加情報（peak_price / entry_date）が必要
- NewsCollector は RSS 取得周りのネットワーク/パースでの堅牢性に配慮しているが、実運用でのソース追加やマッピング（news_symbols）ロジックは拡張を想定
- research モジュールは外部ライブラリに依存しない方針だが、高度な解析用途では pandas 等に勝るとは限らない

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML 関連の攻撃（XML Bomb 等）に対処
- news の URL 正規化でトラッキングパラメータを除去、SSRF を防ぐためスキーム検証等を設計に含める
- config の .env 読み込みは OS 環境変数を保護する設計（protected set）

### 開発ノート
- DuckDB を主要なデータストアとして利用する設計（prices_daily / raw_financials / features / ai_scores / signals / positions 等のテーブル想定）
- ルックアヘッドバイアスを避ける設計方針が各モジュールに反映されている（fetched_at の記録、target_date 以前の最新データのみ参照、トランザクションで日付単位の置換など）
- ロギングは各モジュールに組み込まれている（情報・警告・デバッグの出力）

---

（注）実際のリリース日、パッケージ配布情報、追加の変更履歴は後続のコミット／リリースで更新してください。