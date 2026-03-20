# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを使用します。

現在のリリース: [0.1.0] — 2026-03-20

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システムのコア機能群を実装しています。以下はコードベースから推測してまとめた主要な追加・仕様です。

### 追加
- 基本パッケージ
  - パッケージ初期化とエクスポートを追加 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理
  - 環境変数および .env ファイル読み込み機能を実装 (src/kabusys/config.py)
    - プロジェクトルート自動検出（.git / pyproject.toml を探索）
    - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き可能）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - シェル風の export プレフィックス、クオートやインラインコメント対応の .env パーサを実装
    - Settings クラスに主要設定をプロパティとして提供（J-Quants トークン／Kabu API／Slack／DB パス／環境判定など）
    - 入力検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）、必須環境変数未設定時は ValueError を投げる _require を提供

- データ収集・保存（J-Quants 統合）
  - J-Quants API クライアントを実装 (src/kabusys/data/jquants_client.py)
    - 固定間隔スロットリングによるレート制限（120 req/min）
    - リトライ（指数バックオフ、最大3回）と 408/429/5xx の再試行処理
    - 401 受信時にリフレッシュトークンで自動的にトークンを更新して 1 回リトライするロジック
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
    - 取得時刻 (fetched_at) を UTC で記録し、ルックアヘッドバイアス対応
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT による冪等保存を行う
    - レスポンスパース用のユーティリティ (_to_float / _to_int)
    - モジュール内で ID トークンキャッシュを保持しページネーション間で共有

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加 (src/kabusys/data/news_collector.py)
    - RSS 取得・パース・前処理（URL 正規化、トラッキングパラメータ除去、テキスト正規化）
    - 記事ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保
    - defusedxml を用いた安全な XML パース（XML Bomb 等に対処）
    - 受信サイズ制限（MAX_RESPONSE_BYTES）・HTTP スキームチェックなどのセキュリティ対策
    - DB へのバルク挿入（チャンク化）などパフォーマンス配慮
    - デフォルト RSS ソースを定義（例: Yahoo Finance のカテゴリ RSS）

- リサーチ（因子計算 / 探索）
  - ファクター計算モジュールを実装 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離）
    - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - Value（PER, ROE：raw_financials から最新の財務データを取得）
    - DuckDB の SQL ウィンドウ関数を活用した実装（データ不足時は None を返す設計）
  - 特徴量探索ユーティリティを実装 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日がデフォルト）
    - スピアマンのランク相関による IC 計算 calc_ic（最少レコード数チェック）
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）
    - ランク計算ユーティリティ rank（同順位は平均ランク）
  - 研究用 API をパッケージエクスポートに追加 (src/kabusys/research/__init__.py)

- 特徴量作成（戦略）
  - feature_engineering モジュールを実装 (src/kabusys/strategy/feature_engineering.py)
    - research の生ファクターを取得して統合
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）
    - 正規化（zscore_normalize を利用）後、±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性保障）
    - 冪等性を確保（target_date の既存行を削除してから挿入）
    - 実装と設計にルックアヘッドバイアス防止の考慮あり

- シグナル生成（戦略）
  - signal_generator モジュールを実装 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - 各コンポーネントをシグモイド変換し、重み付き合算で final_score を計算（デフォルト重みを定義）
    - 重みの入力検証と再スケーリング（合計を 1.0 に正規化）
    - Bear レジーム判定（ai_scores の regime_score が平均 < 0 の場合、十分なサンプルがある場合のみ）
    - BUY シグナルは threshold（デフォルト 0.60）超で生成。Bear レジーム時は BUY を抑制
    - SELL シグナル生成（エグジット判定）
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が threshold 未満
      - 保有銘柄の価格未取得時は SELL 判定をスキップしログ出力（誤クローズ防止）
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）
    - BUY と SELL の優先ルール（SELL 対象は BUY から除外し、再ランク付与）

- API 集約（strategy パッケージ）
  - build_features / generate_signals を __all__ で公開 (src/kabusys/strategy/__init__.py)

### 変更（設計／実装方針の明示）
- 各モジュールで「ルックアヘッドバイアス防止」を明記。target_date 時点までのデータのみを参照する方針を徹底。
- DuckDB を主要データレイヤとして想定し、SQL + Python で高効率に集計・ウィンドウ処理を行う設計。
- データ取得・保存処理は冪等性を重視（ON CONFLICT / PK チェック / ID ハッシュ化等）。

### 修正 / 既知の制約（ドキュメント化）
- signal_generator のエグジット条件に関して、コメントに未実装の要素（トレーリングストップ、時間決済）が記載されている。positions テーブルに peak_price / entry_date 等の拡張が必要。
- news_collector の URL 正規化や RSS パースでの仕様詳細（例: トラッキングパラメータリスト）は実装済みだが、外部ソースの多様性に対する追加テストが推奨される。
- execution パッケージの初期化ファイルは存在するが実装がない（将来的な発注連携は別途実装予定）。

### セキュリティ
- defusedxml を利用した安全な RSS パース（XML 攻撃防止）。
- news_collector: 受信サイズ制限、HTTP/HTTPS スキームチェック、トラッキングパラメータ除去など SSRF/DoS 対策を実装。
- J-Quants クライアント: 401 自動リフレッシュ、RateLimiter によるレート制御、Retry ロジックで過負荷を軽減。

### テスト & ロギング
- 各処理で詳細な logger.debug / logger.info / logger.warning を挿入。失敗時はトランザクションを ROLLBACK して例外を再送出する保護を実装。
- 一部の I/O（.env ファイル読み込み）で warnings.warn を利用して非致命的な読み込み失敗を通知。

---

将来的な予定（コード内コメントより推測）
- execution 層の実装（kabuステーション API を用いた発注処理、発注キャンセル、約定管理など）
- positions テーブル拡張（peak_price, entry_date 等）によるトレーリングストップや時間決済の実装
- データ収集の追加ソース（ニュースソースの拡張など）
- テストカバレッジ拡充・外部 API のモック化

もし CHANGELOG に追加したい日付や項目（例えばプレリリース / ベータ / リリースノート細分化）があれば教えてください。コードの注釈に基づきさらに詳細化して追記します。